from __future__ import annotations

import gc, math, re, subprocess, tempfile
from pathlib import Path
from statistics import mean, median

import cv2
import imageio_ffmpeg
import librosa
import mediapipe as mp
import torch

from nltk.tokenize import wordpunct_tokenize
from PIL import Image
from PySide6.QtCore import QThread, Signal
from transformers import (
    AutoModelForAudioClassification,
    AutoProcessor,
    pipeline as hf_pipeline,
)

from src.ui.translations import translate_text


TEXT_MODEL_ID = "j-hartmann/emotion-english-roberta-large"
AUDIO_MODEL_ID = "MERaLiON/MERaLiON-SER-v1"
VISION_MODEL_ID = "mo-thecreator/vit-Facial-Expression-Recognition"
WHISPER_MODEL_ID = "openai/whisper-small"
RECOMMENDATION_MODEL_ID = "Qwen/Qwen3-1.7B"

WHISPER_LANGUAGES = {
    "English": "en",
    "Malay": "ms",
    "Chinese": "zh",
    "Tamil": "ta",
}

NEGATIVE_LABELS = {"anger", "fear", "sadness", "disgust"}

MERALION_LABELS = [
    "Neutral", "Happy", "Sad", "Angry",
    "Fearful", "Disgusted", "Surprised",
]

LABEL_ALIASES = {
    "angry": "anger", "anger": "anger",
    "fearful": "fear", "fear": "fear",
    "sad": "sadness", "sadness": "sadness",
    "disgusted": "disgust", "disgust": "disgust",
    "happy": "happy", "happiness": "happy", "joy": "happy",
    "neutral": "neutral",
    "surprised": "surprise", "surprise": "surprise",

    "label_0": "anger",
    "label_1": "disgust",
    "label_2": "fear",
    "label_3": "happy",
    "label_4": "sadness",
    "label_5": "surprise",
    "label_6": "neutral",
}

SPEECH_RANGES = {
    "English": (100, 190),
    "Malay": (100, 190),
    "Chinese": (180, 320),
    "Tamil": (90, 180),
}

FILLERS = {
    "English": {"um", "uh", "erm", "hmm"},
    "Malay": {"erm", "hmm", "anu", "macam"},
    "Chinese": {"嗯", "呃", "那个"},
    "Tamil": {"அம்", "ஊம்", "அதாவது"},
}

VIDEO_FRAME_COUNT = 8
AUXILIARY_WEIGHT = 0.02


def clamp(value):
    return max(0.0, min(1.0, float(value)))


def label_name(name):
    name = str(name).lower().strip()
    return LABEL_ALIASES.get(name, name)


def predictions(output):
    return output[0] if output and isinstance(output[0], list) else output


def negative_score(output):
    return clamp(sum(
        float(item["score"])
        for item in predictions(output)
        if label_name(item["label"]) in NEGATIVE_LABELS
    ))


class MultimodalPipeline:
    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1

        self.whisper = None
        self.text_model = None
        self.audio_processor = None
        self.audio_model = None
        self.vision_model = None
        self.qwen = None

    # --------------------------------------------------
    # Model loading
    # --------------------------------------------------

    def load_whisper(self):
        if self.whisper is None:
            self.whisper = hf_pipeline(
                "automatic-speech-recognition",
                model=WHISPER_MODEL_ID,
                device=self.device,
                chunk_length_s=30,
            )
        return self.whisper

    def load_text_model(self):
        if self.text_model is None:
            self.text_model = hf_pipeline(
                "text-classification",
                model=TEXT_MODEL_ID,
                device=self.device,
                top_k=None,
            )
        return self.text_model

    def load_audio_model(self):
        if self.audio_model is None:
            self.audio_processor = AutoProcessor.from_pretrained(
                AUDIO_MODEL_ID
            )

            self.audio_model = (
                AutoModelForAudioClassification.from_pretrained(
                    AUDIO_MODEL_ID,
                    trust_remote_code=True,
                )
            )

            if torch.cuda.is_available():
                self.audio_model.to("cuda")

            self.audio_model.eval()

        return self.audio_processor, self.audio_model

    def load_vision_model(self):
        if self.vision_model is None:
            self.vision_model = hf_pipeline(
                "image-classification",
                model=VISION_MODEL_ID,
                device=self.device,
                top_k=None,
            )
        return self.vision_model

    def load_qwen(self):
        if self.qwen is None:
            self.qwen = hf_pipeline(
                "text-generation",
                model=RECOMMENDATION_MODEL_ID,
                device_map="auto",
                dtype="auto",
            )
        return self.qwen

    # --------------------------------------------------
    # Whisper
    # --------------------------------------------------

    def whisper_text(self, audio_path, language_name, task):
        audio, _ = librosa.load(
            audio_path,
            sr=16000,
            mono=True,
        )

        result = self.load_whisper()(
            {
                "array": audio,
                "sampling_rate": 16000,
            },
            return_timestamps=True,
            generate_kwargs={
                "language":
                    WHISPER_LANGUAGES[language_name],
                "task": task,
            },
        )

        return result["text"].strip()

    def transcribe(self, audio_path, language_name):
        return self.whisper_text(
            audio_path,
            language_name,
            "transcribe",
        )

    def translate_to_english(self, audio_path, language_name):
        if language_name == "English":
            return self.transcribe(
                audio_path,
                language_name,
            )

        return self.whisper_text(
            audio_path,
            language_name,
            "translate",
        )

    # --------------------------------------------------
    # Primary model 1 - RoBERTa text emotion
    # --------------------------------------------------

    def text_score(self, text):
        output = self.load_text_model()(
            text,
            truncation=True,
            max_length=512,
            top_k=None,
        )

        return negative_score(output)

    # --------------------------------------------------
    # Primary model 2 - MERaLiON speech emotion
    # --------------------------------------------------

    def audio_score(self, audio_path):
        processor, model = self.load_audio_model()

        audio, _ = librosa.load(
            audio_path,
            sr=16000,
            mono=True,
        )

        inputs = processor(
            audio,
            sampling_rate=16000,
            return_tensors="pt",
            return_attention_mask=True,
        )

        device = next(model.parameters()).device

        inputs = {
            key: value.to(device)
            for key, value in inputs.items()
            if key in {
                "input_features",
                "attention_mask",
            }
        }

        with torch.inference_mode():
            logits = model(**inputs)["logits"]

        probabilities = (
            torch.softmax(logits, dim=-1)[0]
            .detach()
            .cpu()
            .tolist()
        )

        output = [
            {
                "label": label,
                "score": score,
            }
            for label, score
            in zip(
                MERALION_LABELS,
                probabilities,
            )
        ]

        return negative_score(output)

    # --------------------------------------------------
    # Primary model 3 - ViT facial emotion
    # --------------------------------------------------

    def vision_score(self, video_path):
        frames = self.sample_faces(video_path)

        if not frames:
            raise RuntimeError(
                "No face detected in the video."
            )

        model = self.load_vision_model()

        return mean(
            negative_score(
                model(image, top_k=None)
            )
            for image in frames
        )

    def sample_faces(self, video_path):
        capture = cv2.VideoCapture(video_path)

        frame_count = int(
            capture.get(
                cv2.CAP_PROP_FRAME_COUNT
            )
        )

        detector = cv2.CascadeClassifier(
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        images = []

        for index in range(
            VIDEO_FRAME_COUNT
        ):
            position = int(
                index
                * max(frame_count - 1, 0)
                / max(
                    VIDEO_FRAME_COUNT - 1,
                    1,
                )
            )

            capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                position,
            )

            ok, frame = capture.read()

            if not ok:
                continue

            grey = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY,
            )

            faces = detector.detectMultiScale(
                grey,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),
            )

            if len(faces) == 0:
                continue

            x, y, width, height = max(
                faces,
                key=lambda box:
                    box[2] * box[3],
            )

            margin = int(
                max(width, height) * 0.18
            )

            x1 = max(0, x - margin)
            y1 = max(0, y - margin)

            x2 = min(
                frame.shape[1],
                x + width + margin,
            )

            y2 = min(
                frame.shape[0],
                y + height + margin,
            )

            face = cv2.cvtColor(
                frame[y1:y2, x1:x2],
                cv2.COLOR_BGR2RGB,
            )

            images.append(
                Image.fromarray(face)
            )

        capture.release()
        return images

    # --------------------------------------------------
    # Supporting signals 1 + 2
    # Blink rate and head position
    # --------------------------------------------------

    @staticmethod
    def distance(a, b):
        return math.hypot(
            a.x - b.x,
            a.y - b.y,
        )

    def eye_ratio(self, landmarks, indexes):
        p1, p2, p3, p4, p5, p6 = [
            landmarks[index]
            for index in indexes
        ]

        horizontal = self.distance(
            p1,
            p4,
        )

        vertical = (
            self.distance(p2, p6)
            + self.distance(p3, p5)
        )

        return (
            vertical / (2 * horizontal)
            if horizontal
            else 0
        )

    def visual_signals(self, video_path):
        capture = cv2.VideoCapture(
            video_path
        )

        fps = (
            capture.get(
                cv2.CAP_PROP_FPS
            )
            or 30
        )

        duration = (
            int(
                capture.get(
                    cv2.CAP_PROP_FRAME_COUNT
                )
            )
            / fps
        )

        left_eye = [
            33, 160, 158,
            133, 153, 144,
        ]

        right_eye = [
            362, 385, 387,
            263, 373, 380,
        ]

        blink_count = 0
        eye_closed = False
        head_offsets = []
        frame_number = 0

        with mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
        ) as face_mesh:

            while True:
                ok, frame = capture.read()

                if not ok:
                    break

                frame_number += 1

                if frame_number % 3:
                    continue

                result = face_mesh.process(
                    cv2.cvtColor(
                        frame,
                        cv2.COLOR_BGR2RGB,
                    )
                )

                if (
                    not result
                    .multi_face_landmarks
                ):
                    continue

                landmarks = (
                    result
                    .multi_face_landmarks[0]
                    .landmark
                )

                eye = (
                    self.eye_ratio(
                        landmarks,
                        left_eye,
                    )
                    + self.eye_ratio(
                        landmarks,
                        right_eye,
                    )
                ) / 2

                if (
                    eye < 0.20
                    and not eye_closed
                ):
                    eye_closed = True

                elif (
                    eye >= 0.20
                    and eye_closed
                ):
                    blink_count += 1
                    eye_closed = False

                head_offsets.append(
                    abs(
                        landmarks[1].x
                        - 0.5
                    )
                )

        capture.release()

        if not head_offsets:
            raise RuntimeError(
                "Face landmarks could not be measured."
            )

        blink_rate = (
            blink_count
            / duration
            * 60
            if duration
            else 0
        )

        head_offset = mean(
            head_offsets
        )

        if head_offset <= 0.08:
            head_position = "Centred"

        elif head_offset <= 0.18:
            head_position = (
                "Slightly off-centre"
            )

        else:
            head_position = "Off-centre"

        if blink_rate < 8:
            blink_signal = clamp(
                (8 - blink_rate) / 8
            )

        elif blink_rate > 25:
            blink_signal = clamp(
                (blink_rate - 25) / 25
            )

        else:
            blink_signal = 0

        return {
            "blink_rate":
                round(blink_rate, 2),

            "head_position":
                head_position,

            "blink_signal":
                blink_signal,

            "head_signal":
                clamp(
                    (
                        head_offset
                        - 0.08
                    )
                    / 0.25
                ),
        }

    # --------------------------------------------------
    # Supporting signals 3 + 4 + 5
    # Speech rate, disfluency and lexical variety
    # --------------------------------------------------

    def speech_signals(
        self,
        transcript,
        audio_path,
        language_name,
    ):
        duration = librosa.get_duration(
            path=audio_path
        )

        if language_name == "Chinese":
            words = re.findall(
                r"[\u4e00-\u9fff]",
                transcript,
            )

        else:
            words = [
                token.lower()
                for token
                in wordpunct_tokenize(
                    transcript
                )
                if any(
                    letter.isalpha()
                    for letter in token
                )
            ]

        speech_rate = (
            len(words)
            / duration
            * 60
            if duration
            else 0
        )

        lexical_variety = (
            len(set(words))
            / len(words)
            if words
            else 0
        )

        fillers = FILLERS[
            language_name
        ]

        if language_name in {
            "Chinese",
            "Tamil",
        }:
            disfluencies = sum(
                transcript.count(word)
                for word in fillers
            )

        else:
            disfluencies = sum(
                word in fillers
                for word in words
            )

        disfluency_rate = (
            disfluencies
            / len(words)
            if words
            else 0
        )

        low, high = SPEECH_RANGES[
            language_name
        ]

        if speech_rate < low:
            speech_signal = clamp(
                (
                    low
                    - speech_rate
                )
                / low
            )

        elif speech_rate > high:
            speech_signal = clamp(
                (
                    speech_rate
                    - high
                )
                / high
            )

        else:
            speech_signal = 0

        return {
            "speech_rate":
                round(
                    speech_rate,
                    2,
                ),

            "disfluency_rate":
                round(
                    disfluency_rate,
                    3,
                ),

            "lexical_variety":
                round(
                    lexical_variety,
                    3,
                ),

            "speech_signal":
                speech_signal,

            "disfluency_signal":
                clamp(
                    disfluency_rate
                    / 0.10
                ),

            "lexical_signal":
                clamp(
                    (
                        0.45
                        - lexical_variety
                    )
                    / 0.45
                ),
        }

    # --------------------------------------------------
    # Fusion
    # --------------------------------------------------

    def fuse(
        self,
        primary_scores,
        supporting_scores,
    ):
        # Median fusion for the primary AI models.
        # For video: median of text, audio and vision.
        # For audio-only: median of text and audio,
        # which is equivalent to their average.
        primary = median(
            primary_scores
        )

        # Mean retained for reporting the overall
        # supporting-signal level.
        supporting = (
            mean(supporting_scores)
            if supporting_scores
            else 0
        )

        # Each supporting signal receives 2% of the final score.
        supporting_contribution = sum(
            score * AUXILIARY_WEIGHT
            for score in supporting_scores
        )

        # Remaining weight belongs to the primary AI-model fusion.
        # Video: 5 supporting signals -> 90% primary.
        # Audio: 3 supporting signals -> 94% primary.
        primary_weight = (
            1.0
            - len(supporting_scores) * AUXILIARY_WEIGHT
        )

        strain = clamp(
            primary * primary_weight
            + supporting_contribution
        )

        return (
            primary,
            supporting,
            strain,
            primary_weight,
        )
    # --------------------------------------------------
    # Video audio extraction
    # --------------------------------------------------

    def extract_audio(
        self,
        video_path,
    ):
        output = (
            tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False,
            )
        )

        output.close()

        subprocess.run(
            [
                imageio_ffmpeg
                .get_ffmpeg_exe(),

                "-y",
                "-i",
                video_path,

                "-vn",
                "-ac",
                "1",

                "-ar",
                "16000",

                "-c:a",
                "pcm_s16le",

                output.name,
            ],
            capture_output=True,
        )

        return output.name

    # --------------------------------------------------
    # Qwen recommendation
    # --------------------------------------------------

    def recommendation(
        self,
        english_text,
        wellbeing_score,
        summary,
        language_name,
        trend,
    ):
        generator = self.load_qwen()

        support_note = ""

        if wellbeing_score < 35:
            support_note = (
                " Include one recommendation "
                "to contact a trusted person "
                "or qualified healthcare professional."
            )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a workplace wellbeing "
                    "support assistant. "
                    "Do not diagnose medical conditions."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Write exactly 3 short wellbeing "
                    "recommendations in English.\n"
                    "Write each recommendation on a "
                    "separate numbered line.\n"
                    "Make each recommendation different "
                    "and practical.\n"
                    "Do not repeat ideas."
                    f"{support_note}\n\n"
                    f"Wellbeing score: "
                    f"{wellbeing_score:.0f}/100\n"
                    f"Summary: {summary}\n"
                    f"Trend: {trend}\n"
                    f"Transcript: "
                    f"{english_text[:1200]}"
                ),
            },
        ]

        result = generator(
            messages,
            max_new_tokens=180,
            do_sample=False,
            pad_token_id=
                generator.tokenizer
                .eos_token_id,
        )[0]["generated_text"]

        english = (
            result[-1]["content"]
            .strip()
        )

        # Qwen is released before NLLB is loaded.
        self.release_qwen()

        return translate_text(
            english,
            language_name,
        )

    # --------------------------------------------------
    # Full analysis
    # --------------------------------------------------

    def analyse(
        self,
        recording_path,
        recording_type,
        progress,
        transcript=None,
        *,
        language_name="English",
        trend=(
            "No previous check-in "
            "trend is available."
        ),
    ):
        temporary_audio = None

        try:
            if recording_type == "video":
                progress(
                    "processing_extract_audio"
                )

                temporary_audio = (
                    self.extract_audio(
                        recording_path
                    )
                )

                audio_path = (
                    temporary_audio
                )

            else:
                audio_path = (
                    recording_path
                )

            if not transcript:
                progress(
                    "processing_transcription"
                )

                transcript = self.transcribe(
                    audio_path,
                    language_name,
                )

            # RoBERTa and Qwen always receive English.
            progress("processing_text")

            if language_name == "English":
                english_text = transcript

            else:
                english_text = (
                    self.translate_to_english(
                        audio_path,
                        language_name,
                    )
                )

            text = self.text_score(
                english_text
            )

            self.release_whisper()

            progress("processing_audio")

            audio = self.audio_score(
                audio_path
            )

            primary_scores = [
                text,
                audio,
            ]

            vision = None
            visual = {}

            if recording_type == "video":
                progress(
                    "processing_vision"
                )

                vision = self.vision_score(
                    recording_path
                )

                primary_scores.append(
                    vision
                )

                progress(
                    "processing_signals"
                )

                visual = (
                    self.visual_signals(
                        recording_path
                    )
                )

            else:
                progress(
                    "processing_signals"
                )

            speech = self.speech_signals(
                transcript,
                audio_path,
                language_name,
            )

            supporting = [
                speech["speech_signal"],
                speech["disfluency_signal"],
                speech["lexical_signal"],
            ]

            if recording_type == "video":
                supporting += [
                    visual["blink_signal"],
                    visual["head_signal"],
                ]

            progress(
                "processing_fusion"
            )

            (
                primary_strain,
                supporting_strain,
                strain,
                primary_weight,
            ) = self.fuse(
                primary_scores,
                supporting,
            )

            strain_score = (
                strain * 100
            )

            wellbeing_score = (
                100 - strain_score
            )

            phrase, explanation = (
                self.summary(
                    wellbeing_score
                )
            )

            self.release_analysis_models()

            progress(
                "processing_recommendation"
            )

            recommendation = (
                self.recommendation(
                    english_text,
                    wellbeing_score,
                    phrase,
                    language_name,
                    trend,
                )
            )

            return {
                "recording_type":
                    recording_type,

                "language":
                    language_name,

                "transcript":
                    transcript,

                "text_score":
                    round(
                        text * 100,
                        2,
                    ),

                "audio_score":
                    round(
                        audio * 100,
                        2,
                    ),

                "vision_score":
                    (
                        round(
                            vision * 100,
                            2,
                        )
                        if vision
                        is not None
                        else None
                    ),

                # Five supporting signals
                "blink_rate":
                    visual.get(
                        "blink_rate"
                    ),

                "head_position":
                    visual.get(
                        "head_position"
                    ),

                "speech_rate":
                    speech[
                        "speech_rate"
                    ],

                "disfluency_rate":
                    speech[
                        "disfluency_rate"
                    ],

                "lexical_variety":
                    speech[
                        "lexical_variety"
                    ],

                "primary_strain_score":
                    round(
                        primary_strain
                        * 100,
                        2,
                    ),

                "auxiliary_strain_score":
                    round(
                        supporting_strain
                        * 100,
                        2,
                    ),

                "strain_score":
                    round(
                        strain_score,
                        2,
                    ),

                "wellbeing_score":
                    round(
                        wellbeing_score,
                        2,
                    ),

                "primary_weight":
                    round(
                        primary_weight
                        * 100,
                        2,
                    ),

                "phrase":
                    phrase,

                "explanation":
                    explanation,

                "recommendation":
                    recommendation,

            }

        finally:
            if temporary_audio:
                Path(
                    temporary_audio
                ).unlink(
                    missing_ok=True
                )

    @staticmethod
    def summary(score):
        if score >= 67:
            return (
                "Today feels steady",
                "Your signals suggest "
                "a higher wellbeing range.",
            )

        if score >= 34:
            return (
                "Today feels mixed",
                "Your signals suggest "
                "a moderate wellbeing range.",
            )

        return (
            "Today needs more care",
            "Your signals suggest "
            "a lower wellbeing range.",
        )

    # --------------------------------------------------
    # Memory
    # --------------------------------------------------

    def release_whisper(self):
        self.whisper = None
        self.clean_memory()

    def release_analysis_models(self):
        self.text_model = None
        self.audio_processor = None
        self.audio_model = None
        self.vision_model = None
        self.clean_memory()

    def release_qwen(self):
        self.qwen = None
        self.clean_memory()

    @staticmethod
    def clean_memory():
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()


_PIPELINE = MultimodalPipeline()


# --------------------------------------------------
# Whisper worker
# --------------------------------------------------

class TranscriptionWorker(QThread):
    progress = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        recording_path,
        recording_type,
        parent=None,
        *,
        language_name="English",
    ):
        super().__init__(parent)

        self.recording_path = (
            recording_path
        )

        self.recording_type = (
            recording_type
        )

        self.language_name = (
            language_name
        )

    def run(self):
        temporary_audio = None

        try:
            if self.recording_type == "video":
                self.progress.emit(
                    "transcription_extract_audio"
                )

                temporary_audio = (
                    _PIPELINE.extract_audio(
                        self.recording_path
                    )
                )

                audio_path = (
                    temporary_audio
                )

            else:
                audio_path = (
                    self.recording_path
                )

            self.progress.emit(
                "transcription_whisper"
            )

            transcript = (
                _PIPELINE.transcribe(
                    audio_path,
                    self.language_name,
                )
            )

            self.completed.emit(
                transcript
            )

        except Exception as error:
            self.failed.emit(
                str(error)
            )

        finally:
            if temporary_audio:
                Path(
                    temporary_audio
                ).unlink(
                    missing_ok=True
                )

            _PIPELINE.release_whisper()


# --------------------------------------------------
# Complete analysis worker
# --------------------------------------------------

class AnalysisWorker(QThread):
    progress = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        recording_path,
        recording_type,
        transcript,
        parent=None,
        *,
        language_name="English",
        trend=(
            "No previous check-in "
            "trend is available."
        ),
    ):
        super().__init__(parent)

        self.recording_path = (
            recording_path
        )

        self.recording_type = (
            recording_type
        )

        self.transcript = transcript
        self.language_name = language_name
        self.trend = trend

    def run(self):
        try:
            result = _PIPELINE.analyse(
                self.recording_path,
                self.recording_type,
                self.progress.emit,
                self.transcript,
                language_name=
                    self.language_name,
                trend=self.trend,
            )

            self.completed.emit(result)

        except Exception as error:
            self.failed.emit(
                str(error)
            )

        finally:
            _PIPELINE.release_whisper()
            _PIPELINE.release_analysis_models()
            _PIPELINE.release_qwen()