from __future__ import annotations

import gc
import re
import subprocess
import tempfile
from pathlib import Path
from statistics import mean

import cv2
import imageio_ffmpeg
import librosa
import torch
from PIL import Image
from PySide6.QtCore import QThread, Signal
from transformers import AutoModelForCausalLM, AutoTokenizer
from transformers import pipeline as hf_pipeline

TEXT_MODEL_ID = "j-hartmann/emotion-english-roberta-large"
AUDIO_MODEL_ID = "forwarder1121/ast-finetuned-model"
VISION_MODEL_ID = "trpakov/vit-face-expression"
WHISPER_MODEL_ID = "openai/whisper-small"
RECOMMENDATION_MODEL_ID = "Qwen/Qwen2.5-1.5B-Instruct"

NEGATIVE_LABELS = {
    "anger",
    "fear",
    "sad",
    "sadness",
    "disgust",
}

VIDEO_FRAME_COUNT = 8


def canonical_label(value: object) -> str:
    label = re.sub(r"[^a-z]+", "", str(value).strip().lower())

    aliases = {
        "ang": "anger",
        "angry": "anger",
        "anger": "anger",
        "fea": "fear",
        "fearful": "fear",
        "fear": "fear",
        "sad": "sad",
        "sadness": "sadness",
        "hap": "happy",
        "happy": "happy",
        "joy": "happy",
        "neu": "neutral",
        "neutral": "neutral",
        "sur": "surprise",
        "surprised": "surprise",
        "surprise": "surprise",
        "dis": "disgust",
        "disgusted": "disgust",
        "disgust": "disgust",
        "calm": "calm",
        "contempt": "contempt",
    }

    return aliases.get(label, label)


def normalise_predictions(raw_output: object) -> list[dict]:
    output = raw_output

    if isinstance(output, dict):
        output = [output]

    if (
        isinstance(output, list)
        and output
        and isinstance(output[0], list)
    ):
        output = output[0]

    predictions = []

    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue

            if "label" not in item or "score" not in item:
                continue

            predictions.append(
                {
                    "label": str(item["label"]),
                    "score": float(item["score"]),
                }
            )

    return predictions


def negative_probability(predictions: list[dict]) -> float:
    probability = sum(
        item["score"]
        for item in predictions
        if canonical_label(item["label"]) in NEGATIVE_LABELS
    )

    return max(0.0, min(1.0, probability))


class MultimodalPipeline:
    def __init__(self):
        self.device = 0 if torch.cuda.is_available() else -1

        self._whisper = None
        self._text_classifier = None
        self._audio_classifier = None
        self._vision_classifier = None
        self._recommendation_tokenizer = None
        self._recommendation_model = None

    def _load_whisper(self):
        if self._whisper is None:
            self._whisper = hf_pipeline(
                "automatic-speech-recognition",
                model=WHISPER_MODEL_ID,
                device=self.device,
                chunk_length_s=30,
            )

        return self._whisper

    def _load_text_classifier(self):
        if self._text_classifier is None:
            self._text_classifier = hf_pipeline(
                "text-classification",
                model=TEXT_MODEL_ID,
                device=self.device,
                top_k=None,
            )

        return self._text_classifier

    def _load_audio_classifier(self):
        if self._audio_classifier is None:
            self._audio_classifier = hf_pipeline(
                "audio-classification",
                model=AUDIO_MODEL_ID,
                device=self.device,
                top_k=None,
                trust_remote_code=True,
            )

        return self._audio_classifier

    def _load_vision_classifier(self):
        if self._vision_classifier is None:
            self._vision_classifier = hf_pipeline(
                "image-classification",
                model=VISION_MODEL_ID,
                device=self.device,
                top_k=None,
            )

        return self._vision_classifier

    def _load_recommendation_model(self):
        if self._recommendation_model is None:
            self._recommendation_tokenizer = AutoTokenizer.from_pretrained(
                RECOMMENDATION_MODEL_ID
            )

            self._recommendation_model = (
                AutoModelForCausalLM.from_pretrained(
                    RECOMMENDATION_MODEL_ID,
                    torch_dtype="auto",
                    low_cpu_mem_usage=True,
                )
            )

            if torch.cuda.is_available():
                self._recommendation_model.to("cuda")

        return (
            self._recommendation_tokenizer,
            self._recommendation_model,
        )

    def transcribe(self, audio_path: str) -> str:
        recogniser = self._load_whisper()

        waveform, _ = librosa.load(
            audio_path,
            sr=16000,
            mono=True,
        )

        output = recogniser(
            {
                "array": waveform,
                "sampling_rate": 16000,
            }
        )

        if isinstance(output, dict):
            return str(output.get("text", "")).strip()

        return str(output).strip()

    def text_score(self, transcript: str) -> float:
        classifier = self._load_text_classifier()

        raw_output = classifier(
            transcript,
            truncation=True,
            max_length=512,
            top_k=None,
        )

        return negative_probability(
            normalise_predictions(raw_output)
        )

    def audio_score(self, audio_path: str) -> float:
        classifier = self._load_audio_classifier()

        extractor = getattr(
            classifier,
            "feature_extractor",
            None,
        )

        sampling_rate = int(
            getattr(extractor, "sampling_rate", 16000)
        )

        waveform, _ = librosa.load(
            audio_path,
            sr=sampling_rate,
            mono=True,
        )

        raw_output = classifier(
            {
                "array": waveform,
                "sampling_rate": sampling_rate,
            },
            top_k=None,
        )

        return negative_probability(
            normalise_predictions(raw_output)
        )

    def vision_score(self, video_path: str) -> float:
        classifier = self._load_vision_classifier()

        frames = self._sample_face_frames(
            video_path,
            VIDEO_FRAME_COUNT,
        )

        if not frames:
            raise RuntimeError(
                "No usable video frames were found for facial-expression analysis."
            )

        scores = []

        for frame in frames:
            raw_output = classifier(
                frame,
                top_k=None,
            )

            scores.append(
                negative_probability(
                    normalise_predictions(raw_output)
                )
            )

        return float(mean(scores))

    def _sample_face_frames(
        self,
        video_path: str,
        frame_count: int,
    ) -> list[Image.Image]:
        capture = cv2.VideoCapture(video_path)

        if not capture.isOpened():
            raise RuntimeError(
                "The selected video could not be opened."
            )

        total_frames = int(
            capture.get(cv2.CAP_PROP_FRAME_COUNT)
        )

        if total_frames <= 0:
            capture.release()
            return []

        face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades
            + "haarcascade_frontalface_default.xml"
        )

        positions = [
            int(
                index
                * (total_frames - 1)
                / max(1, frame_count - 1)
            )
            for index in range(frame_count)
        ]

        images = []

        for position in positions:
            capture.set(
                cv2.CAP_PROP_POS_FRAMES,
                position,
            )

            success, frame = capture.read()

            if not success:
                continue

            rgb_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2RGB,
            )

            grey_frame = cv2.cvtColor(
                frame,
                cv2.COLOR_BGR2GRAY,
            )

            faces = face_detector.detectMultiScale(
                grey_frame,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(60, 60),
            )

            if len(faces):
                x, y, width, height = max(
                    faces,
                    key=lambda item: item[2] * item[3],
                )

                margin = int(
                    max(width, height) * 0.18
                )

                x1 = max(0, x - margin)
                y1 = max(0, y - margin)
                x2 = min(
                    rgb_frame.shape[1],
                    x + width + margin,
                )
                y2 = min(
                    rgb_frame.shape[0],
                    y + height + margin,
                )

                rgb_frame = rgb_frame[
                    y1:y2,
                    x1:x2,
                ]

            images.append(
                Image.fromarray(rgb_frame)
            )

        capture.release()

        return images

    def extract_audio(self, video_path: str) -> str:
        temporary_file = tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False,
        )

        temporary_file.close()

        ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

        command = [
            ffmpeg_path,
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
            temporary_file.name,
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            Path(temporary_file.name).unlink(
                missing_ok=True
            )

            raise RuntimeError(
                "The audio track could not be extracted from the video."
            )

        return temporary_file.name

    def generate_recommendation(
        self,
        transcript: str,
        wellbeing_score: float,
        phrase: str,
    ) -> str:
        tokenizer, model = (
            self._load_recommendation_model()
        )

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a cautious workplace wellbeing support assistant. "
                    "You do not diagnose medical conditions. Give practical, "
                    "supportive and low-risk suggestions."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Create exactly three short numbered recommendations for "
                    "a healthcare worker based on this experimental check-in. "
                    "Do not mention AI model scores. Do not diagnose. Each item "
                    "must be one short sentence.\n\n"
                    f"Summary: {phrase}\n"
                    f"Wellbeing score: {wellbeing_score:.0f}/100\n"
                    f"Transcript: {transcript[:1200]}"
                ),
            },
        ]

        prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        model_inputs = tokenizer(
            [prompt],
            return_tensors="pt",
        )

        model_inputs = {
            key: value.to(model.device)
            for key, value in model_inputs.items()
        }

        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=150,
            do_sample=False,
            repetition_penalty=1.05,
        )

        prompt_length = model_inputs[
            "input_ids"
        ].shape[1]

        response_ids = generated_ids[
            :,
            prompt_length:
        ]

        recommendation = tokenizer.batch_decode(
            response_ids,
            skip_special_tokens=True,
        )[0].strip()

        if not recommendation:
            raise RuntimeError(
                "The recommendation model returned an empty response."
            )

        return recommendation

    def fallback_recommendation(
        self,
        wellbeing_score: float,
    ) -> str:
        if wellbeing_score >= 70:
            return (
                "1. Keep one routine today that supports your current balance.\n"
                "2. Take a short pause between demanding tasks when possible.\n"
                "3. Check in again later to notice any meaningful change."
            )

        if wellbeing_score >= 40:
            return (
                "1. Take a brief pause and reduce one non-urgent demand today.\n"
                "2. Speak with someone you trust about what feels most difficult.\n"
                "3. Protect time for rest before your next demanding shift."
            )

        return (
            "1. Pause and contact someone you trust for support today.\n"
            "2. Reduce non-essential demands and prioritise rest where possible.\n"
            "3. Consider speaking with a qualified professional if the strain continues."
        )

    def analyse(
        self,
        recording_path: str,
        recording_type: str,
        progress_callback,
        transcript: str | None = None,
    ) -> dict:
        temporary_audio = None

        try:
            if recording_type == "video":
                progress_callback(
                    "Extracting the audio track..."
                )

                temporary_audio = self.extract_audio(
                    recording_path
                )

                audio_path = temporary_audio
            else:
                audio_path = recording_path

            if not transcript:
                progress_callback(
                    "Transcribing speech with Whisper..."
                )

                transcript = self.transcribe(
                    audio_path
                )

            transcript = transcript.strip()

            if not transcript:
                raise RuntimeError(
                    "Whisper could not produce a transcript from this recording."
                )

            progress_callback(
                "Analysing the transcript with RoBERTa..."
            )

            text_negative = self.text_score(
                transcript
            )

            progress_callback(
                "Analysing voice emotion with AST..."
            )

            audio_negative = self.audio_score(
                audio_path
            )

            vision_negative = None

            if recording_type == "video":
                progress_callback(
                    "Analysing facial expressions with ViT..."
                )

                vision_negative = self.vision_score(
                    recording_path
                )

            progress_callback(
                "Fusing the available model scores..."
            )

            modality_scores = [
                text_negative,
                audio_negative,
            ]

            if vision_negative is not None:
                modality_scores.append(
                    vision_negative
                )

            strain_score = float(
                mean(modality_scores) * 100.0
            )

            wellbeing_score = float(
                100.0 - strain_score
            )

            phrase, explanation = (
                self._summary_for_score(
                    wellbeing_score
                )
            )

            # The three emotion models are no longer needed once fusion is complete.
            # Releasing them leaves more memory available for Qwen.
            self.release_analysis_models()

            progress_callback(
                "Generating supportive recommendations with Qwen..."
            )

            recommendation_source = (
                RECOMMENDATION_MODEL_ID
            )

            try:
                recommendation = (
                    self.generate_recommendation(
                        transcript,
                        wellbeing_score,
                        phrase,
                    )
                )
            except Exception:
                recommendation = (
                    self.fallback_recommendation(
                        wellbeing_score
                    )
                )

                recommendation_source = "fallback"

            return {
                "recording_type": recording_type,
                "transcript": transcript,
                "text_score": round(
                    text_negative * 100.0,
                    2,
                ),
                "audio_score": round(
                    audio_negative * 100.0,
                    2,
                ),
                "vision_score": (
                    round(
                        vision_negative * 100.0,
                        2,
                    )
                    if vision_negative is not None
                    else None
                ),
                "strain_score": round(
                    strain_score,
                    2,
                ),
                "wellbeing_score": round(
                    wellbeing_score,
                    2,
                ),
                "phrase": phrase,
                "explanation": explanation,
                "recommendation": recommendation,
                "recommendation_source": (
                    recommendation_source
                ),
            }

        finally:
            if temporary_audio:
                Path(temporary_audio).unlink(
                    missing_ok=True
                )

    def _summary_for_score(
        self,
        wellbeing_score: float,
    ) -> tuple[str, str]:
        if wellbeing_score >= 75:
            return (
                "Today feels steady",
                "Your available signals suggest relatively stable emotional energy today.",
            )

        if wellbeing_score >= 55:
            return (
                "Today feels balanced",
                "Your available signals suggest some strain, but the overall pattern remains fairly balanced.",
            )

        if wellbeing_score >= 35:
            return (
                "Today feels heavier",
                "Your available signals suggest lower energy and increased emotional strain today.",
            )

        return (
            "Today feels difficult",
            "Your available signals suggest a high level of emotional strain today. Consider pausing and seeking support.",
        )

    def release_whisper(self):
        self._whisper = None
        self._clean_memory()

    def release_analysis_models(self):
        self._text_classifier = None
        self._audio_classifier = None
        self._vision_classifier = None
        self._clean_memory()

    def release_recommendation_model(self):
        self._recommendation_tokenizer = None
        self._recommendation_model = None
        self._clean_memory()

    def _clean_memory(self):
        gc.collect()

        if torch.cuda.is_available():
            torch.cuda.empty_cache()


_PIPELINE = MultimodalPipeline()


class TranscriptionWorker(QThread):
    progress = Signal(str)
    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        recording_path: str,
        recording_type: str,
        parent=None,
    ):
        super().__init__(parent)

        self.recording_path = recording_path
        self.recording_type = recording_type

    def run(self):
        temporary_audio = None

        try:
            if self.recording_type == "video":
                self.progress.emit(
                    "Extracting audio for transcription..."
                )

                temporary_audio = (
                    _PIPELINE.extract_audio(
                        self.recording_path
                    )
                )

                audio_path = temporary_audio
            else:
                audio_path = self.recording_path

            self.progress.emit(
                "Creating transcript with Whisper..."
            )

            transcript = _PIPELINE.transcribe(
                audio_path
            )

            if not transcript:
                raise RuntimeError(
                    "Whisper could not produce a transcript."
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
                Path(temporary_audio).unlink(
                    missing_ok=True
                )

            _PIPELINE.release_whisper()


class AnalysisWorker(QThread):
    progress = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        recording_path: str,
        recording_type: str,
        transcript: str,
        parent=None,
    ):
        super().__init__(parent)

        self.recording_path = recording_path
        self.recording_type = recording_type
        self.transcript = transcript

    def run(self):
        try:
            result = _PIPELINE.analyse(
                self.recording_path,
                self.recording_type,
                self.progress.emit,
                self.transcript,
            )

            self.completed.emit(result)

        except Exception as error:
            self.failed.emit(str(error))

        finally:
            _PIPELINE.release_analysis_models()
            _PIPELINE.release_recommendation_model()