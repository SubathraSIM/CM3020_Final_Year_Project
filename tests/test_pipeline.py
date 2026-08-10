import tempfile
import wave
from pathlib import Path

from src.ai.multimodal_pipeline import (
    MultimodalPipeline,
    clamp,
    label_name,
    negative_score,
    predictions,
)


# Helper function to create a temporary silent WAV file
def create_test_wav(path, duration, sample_rate=16000):
    frame_count = int(duration * sample_rate)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(
            b"\x00\x00" * frame_count
        )


# Test case 1: Check that clamp keeps values between 0 and 1
def test_clamp():
    assert clamp(-0.5) == 0.0
    assert clamp(0.0) == 0.0
    assert clamp(0.5) == 0.5
    assert clamp(1.0) == 1.0
    assert clamp(1.5) == 1.0


# Test case 2: Check that emotion labels are converted to the common labels
def test_label_name():
    assert label_name("Angry") == "anger"
    assert label_name("Fearful") == "fear"
    assert label_name("Sad") == "sadness"
    assert label_name("Disgusted") == "disgust"

    assert label_name("Happy") == "happy"
    assert label_name("Joy") == "happy"
    assert label_name("Neutral") == "neutral"

    assert label_name("label_0") == "anger"
    assert label_name("label_3") == "happy"
    assert label_name("label_6") == "neutral"


# Test case 3: Check that flat and nested model outputs are handled correctly
def test_predictions():
    flat_output = [
        {
            "label": "anger",
            "score": 0.4
        }
    ]

    nested_output = [
        [
            {
                "label": "anger",
                "score": 0.4
            }
        ]
    ]

    assert predictions(flat_output) == flat_output
    assert predictions(nested_output) == nested_output[0]


# Test case 4: Check that only negative emotions are added to the strain score
def test_negative_score():
    output = [
        {
            "label": "anger",
            "score": 0.20
        },
        {
            "label": "fear",
            "score": 0.10
        },
        {
            "label": "sadness",
            "score": 0.25
        },
        {
            "label": "disgust",
            "score": 0.05
        },
        {
            "label": "happy",
            "score": 0.30
        },
        {
            "label": "neutral",
            "score": 0.10
        }
    ]

    result = negative_score(output)

    assert round(result, 2) == 0.60


# Test case 5: Check that the negative emotion score cannot go above 1
def test_negative_score_limit():
    output = [
        {
            "label": "anger",
            "score": 0.70
        },
        {
            "label": "fear",
            "score": 0.60
        }
    ]

    result = negative_score(output)

    assert result == 1.0


# Test case 6: Check the eye ratio calculation used for blink detection
def test_eye_ratio():
    class Point:
        def __init__(self, x, y):
            self.x = x
            self.y = y

    landmarks = [
        Point(0.0, 0.0),
        Point(0.5, 0.5),
        Point(1.5, 0.5),
        Point(2.0, 0.0),
        Point(1.5, -0.5),
        Point(0.5, -0.5),
    ]

    pipeline = MultimodalPipeline()

    result = pipeline.eye_ratio(
        landmarks,
        [0, 1, 2, 3, 4, 5]
    )

    assert round(result, 2) == 0.50


# Test case 7: Check English speech rate, disfluency and lexical variety
def test_english_speech_signals():
    pipeline = MultimodalPipeline()

    with tempfile.TemporaryDirectory() as folder:
        audio_path = Path(folder) / "english.wav"

        create_test_wav(
            audio_path,
            duration=6
        )

        transcript = (
            "I feel tired um after a long shift "
            "but I feel okay"
        )

        result = pipeline.speech_signals(
            transcript,
            str(audio_path),
            "English"
        )

    assert result["speech_rate"] == 120.0
    assert result["disfluency_rate"] == 0.083
    assert result["lexical_variety"] == 0.833

    assert result["speech_signal"] == 0
    assert round(
        result["disfluency_signal"],
        3
    ) == 0.833

    assert result["lexical_signal"] == 0


# Test case 8: Check Chinese speech signals use Chinese characters correctly
def test_chinese_speech_signals():
    pipeline = MultimodalPipeline()

    with tempfile.TemporaryDirectory() as folder:
        audio_path = Path(folder) / "chinese.wav"

        create_test_wav(
            audio_path,
            duration=2
        )

        transcript = "我今天很累嗯但是还好"

        result = pipeline.speech_signals(
            transcript,
            str(audio_path),
            "Chinese"
        )

    assert result["speech_rate"] == 300.0
    assert result["disfluency_rate"] == 0.1
    assert result["lexical_variety"] == 1.0

    assert result["speech_signal"] == 0
    assert result["disfluency_signal"] == 1.0
    assert result["lexical_signal"] == 0


# Test case 9: Check that slow speech produces a supporting strain signal
def test_slow_speech_signal():
    pipeline = MultimodalPipeline()

    with tempfile.TemporaryDirectory() as folder:
        audio_path = Path(folder) / "slow.wav"

        create_test_wav(
            audio_path,
            duration=6
        )

        transcript = (
            "I feel very tired"
        )

        result = pipeline.speech_signals(
            transcript,
            str(audio_path),
            "English"
        )

    assert result["speech_rate"] == 40.0

    assert round(
        result["speech_signal"],
        2
    ) == 0.60


# Test case 10: Check audio fusion uses 94 percent primary model weight
def test_audio_fusion():
    pipeline = MultimodalPipeline()

    primary_scores = [
        0.40,
        0.60
    ]

    supporting_scores = [
        0.20,
        0.40,
        0.60
    ]

    (
        primary,
        supporting,
        strain,
        primary_weight
    ) = pipeline.fuse(
        primary_scores,
        supporting_scores
    )

    assert round(primary, 2) == 0.50
    assert round(supporting, 2) == 0.40

    assert round(
        primary_weight,
        2
    ) == 0.94

    assert round(
        strain,
        3
    ) == 0.494


# Test case 11: Check video fusion uses 90 percent primary model weight
def test_video_fusion():
    pipeline = MultimodalPipeline()

    primary_scores = [
        0.30,
        0.50,
        0.70
    ]

    supporting_scores = [
        0.10,
        0.20,
        0.30,
        0.40,
        0.50
    ]

    (
        primary,
        supporting,
        strain,
        primary_weight
    ) = pipeline.fuse(
        primary_scores,
        supporting_scores
    )

    assert round(primary, 2) == 0.50
    assert round(supporting, 2) == 0.30

    assert round(
        primary_weight,
        2
    ) == 0.90

    assert round(
        strain,
        2
    ) == 0.48


# Test case 12: Check fusion works when no supporting signals are supplied
def test_fusion_without_supporting_signals():
    pipeline = MultimodalPipeline()

    primary_scores = [
        0.40,
        0.60
    ]

    (
        primary,
        supporting,
        strain,
        primary_weight
    ) = pipeline.fuse(
        primary_scores,
        []
    )

    assert round(primary, 2) == 0.50
    assert supporting == 0

    assert primary_weight == 1.0
    assert round(strain, 2) == 0.50


# Test case 13: Check the higher wellbeing score boundary
def test_high_wellbeing_summary():
    pipeline = MultimodalPipeline()

    phrase, explanation = pipeline.summary(
        67
    )

    assert phrase == "Today feels steady"

    assert (
        "higher wellbeing range"
        in explanation
    )


# Test case 14: Check the moderate wellbeing score boundary
def test_moderate_wellbeing_summary():
    pipeline = MultimodalPipeline()

    phrase, explanation = pipeline.summary(
        34
    )

    assert phrase == "Today feels mixed"

    assert (
        "moderate wellbeing range"
        in explanation
    )


# Test case 15: Check the lower wellbeing score boundary
def test_low_wellbeing_summary():
    pipeline = MultimodalPipeline()

    phrase, explanation = pipeline.summary(
        33
    )

    assert phrase == "Today needs more care"

    assert (
        "lower wellbeing range"
        in explanation
    )