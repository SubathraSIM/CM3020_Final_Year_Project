import math, random, re, struct, sys, tempfile, wave
from datetime import datetime
from pathlib import Path

import librosa

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtMultimedia import (
    QAudioFormat, QAudioInput, QAudioOutput, QAudioSource, QCamera,
    QMediaCaptureSession, QMediaDevices, QMediaFormat, QMediaPlayer,
    QMediaRecorder,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFileDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPlainTextEdit, QProgressBar, QPushButton, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)

from src.ai.multimodal_pipeline import AnalysisWorker, TranscriptionWorker
from src.database.database import get_recent_scores, save_check_in
from src.ui.home_page import HoverSidebar
from src.ui.translations import ENGLISH_TEXT, get_text


ROOT = Path(__file__).resolve().parents[2]
RECORDINGS = Path(tempfile.gettempdir()) / "Solace" / "recordings"
IMAGES = ROOT / "src" / "images"
RECORDINGS.mkdir(parents=True, exist_ok=True)


CHECKIN_TEXT = {
    "record_check_in": "Record your check-in",
    "record_instruction": "Record video or audio. Your transcript appears after you stop.",
    "video_check_in": "Video check-in",
    "camera_off": "Camera is off",
    "audio_check_in": "Audio-only check-in",
    "audio_note": "The bars respond to your voice and replay.",
    "automatic_transcript": "Automatic transcript",
    "transcript_note": "Whisper creates this after recording stops. You may correct it before submission.",
    "transcript_placeholder": "Your transcript will appear here.",

    "not_recorded": "Not recorded",
    "start_video": "Start video",
    "start_audio": "Start audio",
    "recording": "Recording",
    "stop_video": "Stop video",
    "stop_audio": "Stop audio",
    "record_again": "Record again",
    "record_instead": "Record instead",
    "video_recorded": "Video recorded",
    "audio_recorded": "Audio recorded",
    "uploaded": "Uploaded",
    "upload": "Upload",
    "delete": "Delete",
    "submit": "Submit",

    "upload_recording": "Upload recording",
    "upload_recording_title": "Upload a recording",
    "upload_recording_note": "Choose the recording type, then select one file.",
    "recording_type": "Recording type",
    "audio": "Audio",
    "video": "Video",
    "no_file_selected": "No file selected",
    "choose_file": "Choose file",
    "cancel": "Cancel",
    "use_file": "Use this file",
    "select_audio_file": "Select audio file",
    "select_video_file": "Select video file",

    "creating_transcript": "Creating transcript...",
    "transcription_extract_audio": "Extracting audio for transcription...",
    "transcription_whisper": "Creating transcript with Whisper...",
    "transcript_unavailable": "Transcript unavailable. Record or upload another file.",
    "transcription_failed": "Transcription failed. Please try another recording.",

    "stop_before_submit": "Stop the recording before submitting.",
    "record_first": "Record or upload video or audio first.",
    "wait_transcript": "Please wait for the transcript to finish.",
    "transcript_required": "A transcript is required before analysis.",
    "no_camera": "No camera was found.",
    "no_microphone": "No microphone was found.",
    "microphone_failed": "The microphone could not be started.",
    "video_failed": "Video recording failed.",
    "analysis_failed": "Analysis could not be completed. Please try again.",

    "processing_title": "Processing your check-in",
    "processing_note": "Please keep the application open while the selected models run.",
    "processing_loading": "Loading the selected AI models...",
    "processing_extract_audio": "Extracting audio...",
    "processing_transcription": "Transcribing speech...",
    "processing_text": "Analysing text emotion...",
    "processing_audio": "Analysing voice emotion...",
    "processing_vision": "Analysing facial expression...",
    "processing_signals": "Calculating supporting signals...",
    "processing_fusion": "Combining the available signals...",
    "processing_recommendation": "Generating supportive recommendations...",

    "wellbeing_summary": "Your wellbeing summary",
    "experimental_note": "This is an experimental wellbeing estimate, not a diagnosis.",
    "summary_note": "The summary combines the available AI and supporting signals.",
    "wellbeing_score": "Wellbeing score",
    "score_caveat": "An indicative signal, not a diagnosis.",
    "supporting_signals": "Supporting signals",
    "blink_rate": "Blink rate",
    "head_position": "Head position",
    "speech_rate": "Speech rate",
    "disfluency": "Disfluency",
    "lexical_variety": "Lexical variety",
    "not_available": "Not available",
    "head_centred": "Centred",
    "head_slightly_off": "Slightly off-centre",
    "head_off": "Off-centre",
    "supportive_recommendations": "Supportive recommendations",
    "qwen_note": "Generated from this check-in using Qwen.",
    "saved_history": "Your check-in has been saved locally.",
    "done": "Done",

    "first_high_phrase": "Today feels steady",
    "first_high_text": "Your first check-in shows a higher wellbeing range.",
    "first_mid_phrase": "Today feels mixed",
    "first_mid_text": "Your first check-in shows a moderate wellbeing range.",
    "first_low_phrase": "Today needs more care",
    "first_low_text": "Your first check-in shows a lower wellbeing range.",
    "improved_phrase": "You're moving forward",
    "improved_text": "Your wellbeing score has improved compared with your previous check-in.",
    "lower_phrase": "A little more care may help",
    "lower_text": "Your wellbeing score is lower than your previous check-in.",
    "steady_phrase": "Today feels steady",
    "steady_text": "Your wellbeing score is close to your previous check-in.",
}

ENGLISH_TEXT.update(CHECKIN_TEXT)


def label(name="", wrap=False, align=None):
    w = QLabel()
    if name:
        w.setObjectName(name)
    w.setWordWrap(wrap)
    if align is not None:
        w.setAlignment(align)
    return w


def frame(name):
    w = QFrame()
    w.setObjectName(name)
    w.setAttribute(Qt.WA_StyledBackground, True)
    return w


def button(name, height=44, width=None):
    w = QPushButton()
    w.setObjectName(name)
    w.setFixedHeight(height)
    w.setCursor(Qt.PointingHandCursor)
    if width:
        w.setFixedWidth(width)
    return w


class WaveformWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("waveformWidget")
        self.levels = [0.0] * 40
        self.setMinimumHeight(92)

    def clear(self):
        self.levels = [0.0] * 40
        self.update()

    def add_level(self, level):
        level = max(0, min(1, float(level)))
        for i in range(40):
            shape = 0.55 + 0.45 * math.sin(math.pi * i / 39)
            target = level * shape * random.uniform(0.75, 1.05)
            self.levels[i] = self.levels[i] * 0.5 + target * 0.5
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#F8FAFC"))

        gap, padding = 3, 14
        width = max(2.5, (self.width() - padding * 2 - gap * 39) / 40)
        middle, x = self.height() / 2, float(padding)
        p.setPen(Qt.NoPen)

        for value in self.levels:
            height = max(3, value * self.height() * 0.78)
            p.setBrush(QColor("#2563EB" if value > 0.06 else "#C7D2FE"))
            p.drawRoundedRect(QRectF(x, middle - height / 2, width, height), 3, 3)
            x += width + gap


class LoadingSpinner(QWidget):
    def __init__(self):
        super().__init__()
        self.angle = 0
        self.setFixedSize(90, 90)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)

    def start(self):
        self.timer.start(40)

    def stop(self):
        self.timer.stop()

    def rotate(self):
        self.angle = (self.angle - 12) % 360
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#2563EB"), 7)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawArc(QRectF(10, 10, 70, 70), self.angle * 16, 275 * 16)


class MiniTrendGraph(QWidget):
    def __init__(self):
        super().__init__()
        self.points = []
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_points(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        if len(self.points) < 2:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        left, right, top, bottom = 35, 15, 15, 25
        width = self.width() - left - right
        height = self.height() - top - bottom
        step = width / (len(self.points) - 1)

        p.setPen(QPen(QColor("#E2E8F0"), 1))
        for row in range(3):
            y = top + row * height / 2
            p.drawLine(left, int(y), self.width() - right, int(y))

        points = []
        for i, item in enumerate(self.points):
            score = float(item["score"])
            points.append(QPointF(left + i * step, top + (100 - score) / 100 * height))

        p.setPen(QPen(QColor("#2563EB"), 3))
        for i in range(len(points) - 1):
            p.drawLine(points[i], points[i + 1])

        p.setBrush(QColor("#FFFFFF"))
        p.setPen(QPen(QColor("#2563EB"), 2))
        for point in points:
            p.drawEllipse(point, 4, 4)

        p.setPen(QColor("#94A3B8"))
        p.drawText(QRectF(left, self.height() - 20, width / 2, 16),
                   Qt.AlignLeft, str(self.points[0].get("day", "")))
        p.drawText(QRectF(left + width / 2, self.height() - 20, width / 2, 16),
                   Qt.AlignRight, str(self.points[-1].get("day", "")))


class UploadDialog(QDialog):
    def __init__(self, language, parent=None):
        super().__init__(parent)

        self.language = language
        self.selected_path = ""
        self.selected_type = "audio"
        self.setFixedSize(520, 370)

        card = frame("uploadCard")
        self.title = label("uploadTitle")
        self.note = label("uploadNote", True)
        self.type_label = label("fieldLabel")

        self.type_combo = QComboBox()
        self.type_combo.setObjectName("uploadTypeCombo")
        self.type_combo.setFixedHeight(46)
        self.type_combo.addItem("", "audio")
        self.type_combo.addItem("", "video")
        self.type_combo.currentIndexChanged.connect(self.change_type)

        self.file_label = label("uploadFileLabel", True)
        self.file_label.setMinimumHeight(48)

        self.choose_button = button("uploadChooseButton", 46)
        self.cancel_button = button("secondaryButton", 44, 110)
        self.use_button = button("primaryButton", 44, 150)
        self.use_button.setEnabled(False)

        self.choose_button.clicked.connect(self.choose_file)
        self.cancel_button.clicked.connect(self.reject)
        self.use_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.use_button)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 26, 30, 26)
        layout.setSpacing(12)

        for w in (self.title, self.note, self.type_label,
                  self.type_combo, self.file_label, self.choose_button):
            layout.addWidget(w)

        layout.addStretch()
        layout.addLayout(buttons)

        outer = QVBoxLayout(self)
        outer.addWidget(card)

        self.translate()

    def t(self, key):
        return get_text(self.language, key)

    def translate(self):
        self.setWindowTitle(self.t("upload_recording"))

        texts = {
            self.title: "upload_recording_title",
            self.note: "upload_recording_note",
            self.type_label: "recording_type",
            self.file_label: "no_file_selected",
            self.choose_button: "choose_file",
            self.cancel_button: "cancel",
            self.use_button: "use_file",
        }

        for w, key in texts.items():
            w.setText(self.t(key))

        self.type_combo.setItemText(0, self.t("audio"))
        self.type_combo.setItemText(1, self.t("video"))

        if self.language == "Tamil":
            for w in texts:
                w.setStyleSheet("font-size:10px;")

    def change_type(self):
        self.selected_type = self.type_combo.currentData()
        self.selected_path = ""
        self.file_label.setText(self.t("no_file_selected"))
        self.use_button.setEnabled(False)

    def choose_file(self):
        audio = self.selected_type == "audio"
        caption = self.t("select_audio_file" if audio else "select_video_file")
        file_filter = (
            "Audio files (*.wav *.mp3 *.m4a *.flac *.ogg)"
            if audio else
            "Video files (*.mp4 *.mov *.avi *.mkv *.webm)"
        )

        path, _ = QFileDialog.getOpenFileName(self, caption, "", file_filter)

        if path:
            self.selected_path = path
            self.file_label.setText(Path(path).name)
            self.use_button.setEnabled(True)


class CheckInPage(QWidget):
    home_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()

        self.user_id = None
        self.current_language = "English"
        self.user_labels = []

        self.video_file = ""
        self.audio_file = ""
        self.video_local = False
        self.audio_local = False
        self.video_recording = False
        self.audio_recording = False
        self.recording_mode = ""
        self.elapsed = 0

        self.audio_pcm = bytearray()
        self.audio_levels = []

        self.transcription_worker = None
        self.analysis_worker = None
        self.processing_key = "processing_loading"

        self.capture_session = None
        self.camera = None
        self.camera_audio = None
        self.recorder = None

        self.audio_source = None
        self.audio_device = None
        self.audio_format = None

        self.play_icon = QIcon(str(IMAGES / "play.png"))
        self.pause_icon = QIcon(str(IMAGES / "pause.png"))

        self.video_player = QMediaPlayer(self)
        self.video_output = QAudioOutput(self)
        self.video_player.setAudioOutput(self.video_output)

        self.audio_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_player.setAudioOutput(self.audio_output)

        self.video_player.playbackStateChanged.connect(self.video_state)
        self.video_player.durationChanged.connect(
            lambda ms: self.set_duration(self.video_time, ms)
        )

        self.audio_player.playbackStateChanged.connect(self.audio_state)
        self.audio_player.durationChanged.connect(
            lambda ms: self.set_duration(self.audio_time, ms)
        )
        self.audio_player.positionChanged.connect(self.sync_waveform)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time)

        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)

        self.sidebar.home_button.setProperty("active", False)
        self.sidebar.check_in_button.setProperty("active", True)

        for w in (self.sidebar.home_button, self.sidebar.check_in_button):
            w.style().unpolish(w)
            w.style().polish(w)

        self.stack = QStackedWidget()
        self.capture_page = self.build_capture()
        self.processing_page = self.build_processing()
        self.result_page = self.build_result()

        for page in (self.capture_page, self.processing_page, self.result_page):
            self.stack.addWidget(page)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.stack, 1)

        self.set_language("English")

    # ---------------- UI ----------------

    def header(self):
        heart = QLabel()
        heart.setFixedSize(30, 30)
        heart.setAlignment(Qt.AlignCenter)
        heart.setPixmap(
            QPixmap(str(IMAGES / "heart.png")).scaled(
                28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )

        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        user = label("welcomeLabel", align=Qt.AlignRight | Qt.AlignVCenter)
        self.user_labels.append(user)

        row = QHBoxLayout()
        row.setSpacing(7)
        row.addWidget(heart)
        row.addWidget(brand)
        row.addStretch()
        row.addWidget(user)
        return row

    def build_capture(self):
        page = QWidget()
        page.setObjectName("checkInPageContent")

        self.capture_title = label("checkInIntroTitle", True)
        self.capture_subtitle = label("checkInIntroText", True)
        self.capture_status = label("captureStatus")
        self.capture_status.hide()

        title = QHBoxLayout()
        title.addWidget(self.capture_title)
        title.addStretch()
        title.addWidget(self.capture_status)

        cards = QHBoxLayout()
        cards.setSpacing(16)
        cards.addWidget(self.build_video(), 1)
        cards.addWidget(self.build_audio(), 1)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 22)
        layout.setSpacing(10)
        layout.addLayout(self.header())
        layout.addLayout(title)
        layout.addWidget(self.capture_subtitle)
        layout.addLayout(cards, 3)
        layout.addWidget(self.build_transcript(), 2)
        layout.addWidget(self.build_actions())
        return page

    def build_video(self):
        card = frame("videoCaptureCard")
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        card.setFixedHeight(232)

        self.video_title = label("captureCardTitle", True)
        self.video_title.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Preferred,
        )

        self.video_stack = QStackedWidget()
        self.video_stack.setObjectName("videoPreviewStack")
        self.video_stack.setFixedSize(300, 135)

        placeholder = QWidget()
        placeholder.setObjectName("videoPlaceholder")
        self.camera_off = label("videoPreviewText", align=Qt.AlignCenter)

        holder = QVBoxLayout(placeholder)
        holder.setContentsMargins(0, 0, 0, 0)
        holder.addWidget(self.camera_off)

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName("videoWidget")
        self.video_widget.setFixedSize(300, 135)
        self.video_widget.setAspectRatioMode(Qt.KeepAspectRatioByExpanding)

        self.video_stack.addWidget(placeholder)
        self.video_stack.addWidget(self.video_widget)

        self.video_status = label("recordingStatus")
        self.video_status.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Preferred,
        )

        self.video_time = QLabel("00:00")
        self.video_time.setObjectName("recordingTimeSmall")
        self.video_time.setFixedWidth(42)

        self.video_play = button("playMediaButton", 42, 56)
        self.video_play.setIconSize(QSize(18, 18))
        self.video_play.setEnabled(False)
        self.video_play.clicked.connect(self.toggle_video_play)
        self.set_play_icon(self.video_play, False)

        self.video_button = button("recordButton", 42, 190)
        self.video_button.clicked.connect(self.toggle_video)

        controls = QHBoxLayout()
        controls.addWidget(self.video_status)
        controls.addWidget(self.video_time)
        controls.addStretch()
        controls.addWidget(self.video_play)
        controls.addWidget(self.video_button)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 10, 20, 12)
        layout.setSpacing(5)
        layout.addWidget(self.video_title)
        layout.addWidget(
            self.video_stack,
            0,
            Qt.AlignHCenter | Qt.AlignTop,
        )
        layout.addSpacing(2)
        layout.addLayout(controls)
        return card

    def build_audio(self):
        card = frame("checkInLowerCard")

        self.audio_title = label("captureCardTitle", True)
        self.audio_note = label("captureCardText", True)
        self.waveform = WaveformWidget()

        self.audio_play = button("audioPlayButton", 46, 46)
        self.audio_play.setIconSize(QSize(18, 18))
        self.audio_play.setEnabled(False)
        self.audio_play.clicked.connect(self.toggle_audio_play)
        self.set_play_icon(self.audio_play, False)

        wave = QHBoxLayout()
        wave.addWidget(self.waveform, 1)
        wave.addWidget(self.audio_play)

        self.audio_status = label("recordingStatus")
        self.audio_time = QLabel("00:00")
        self.audio_time.setObjectName("recordingTimeSmall")

        self.audio_button = button("recordButton", 42)
        self.audio_button.clicked.connect(self.toggle_audio)

        status = QHBoxLayout()
        status.addWidget(self.audio_status)
        status.addStretch()
        status.addWidget(self.audio_time)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(7)
        layout.addWidget(self.audio_title)
        layout.addWidget(self.audio_note)
        layout.addLayout(wave, 1)
        layout.addLayout(status)
        layout.addWidget(self.audio_button)
        return card

    def build_transcript(self):
        card = frame("transcriptCard")
        self.transcript_title = label("captureCardTitle", True)
        self.transcript_note = label("captureCardText", True)

        self.transcript = QPlainTextEdit()
        self.transcript.setObjectName("transcriptEditor")
        self.transcript.setReadOnly(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(7)
        layout.addWidget(self.transcript_title)
        layout.addWidget(self.transcript_note)
        layout.addWidget(self.transcript, 1)
        return card

    def build_actions(self):
        card = frame("checkInActionCard")

        self.upload_button = button("uploadCheckInButton")
        self.delete_button = button("deleteCheckInButton")
        self.submit_button = button("submitCheckInButton")
        self.submit_button.setEnabled(False)

        self.upload_button.clicked.connect(self.open_upload)
        self.delete_button.clicked.connect(self.reset_recordings)
        self.submit_button.clicked.connect(self.submit_check_in)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 11, 18, 11)
        layout.setSpacing(16)

        for w in (self.upload_button, self.delete_button, self.submit_button):
            w.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            layout.addWidget(w, 1)

        return card

    def build_processing(self):
        page = QWidget()
        page.setObjectName("processingPage")

        card = frame("processingCard")
        self.spinner = LoadingSpinner()
        self.processing_title = label("processingTitle", align=Qt.AlignCenter)
        self.processing_message = label("processingMessage", True, Qt.AlignCenter)
        self.processing_note = label("processingNote", True, Qt.AlignCenter)

        inside = QVBoxLayout(card)
        inside.setContentsMargins(50, 44, 50, 44)
        inside.setSpacing(14)
        inside.addWidget(self.spinner, 0, Qt.AlignCenter)
        inside.addWidget(self.processing_title)
        inside.addWidget(self.processing_message)
        inside.addWidget(self.processing_note)

        layout = QVBoxLayout(page)
        layout.addStretch()
        layout.addWidget(card, 0, Qt.AlignCenter)
        layout.addStretch()
        return page

    def build_result(self):
        page = QWidget()
        page.setObjectName("resultPage")

        self.result_title = label("resultPageTitle", True)
        self.result_subtitle = label("checkInIntroText", True)

        summary = frame("resultSummaryCard")
        self.result_image = label("resultEmoji", align=Qt.AlignCenter)
        self.result_image.setFixedHeight(90)
        self.result_phrase = label("resultPhrase", True)
        self.result_explanation = label("resultExplanation", True)
        self.summary_note = label("resultReminder", True)

        summary_layout = QVBoxLayout(summary)
        summary_layout.setContentsMargins(28, 20, 28, 20)
        summary_layout.addWidget(self.result_image)
        summary_layout.addWidget(self.result_phrase)
        summary_layout.addWidget(self.result_explanation)
        summary_layout.addStretch()
        summary_layout.addWidget(self.summary_note)

        score_card = frame("resultScoreCard")
        self.score_label = label("scoreLabel")

        self.score = QProgressBar()
        self.score.setObjectName("wellbeingProgress")
        self.score.setRange(0, 100)
        self.score.setFormat("-- / 100")

        self.score_note = label("scoreCaveat", True)
        self.signals_title = label("captureCardTitle")
        self.signal_names, self.signal_values = {}, {}

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(6)

        keys = ("blink_rate", "head_position", "speech_rate",
                "disfluency", "lexical_variety")

        for row, key in enumerate(keys):
            name = label("scoreCaveat")
            value = label("scoreLabel", align=Qt.AlignRight | Qt.AlignVCenter)
            self.signal_names[key] = name
            self.signal_values[key] = value
            grid.addWidget(name, row, 0)
            grid.addWidget(value, row, 1)

        score_layout = QVBoxLayout(score_card)
        score_layout.setContentsMargins(24, 18, 24, 18)
        score_layout.addWidget(self.score_label)
        score_layout.addWidget(self.score)
        score_layout.addWidget(self.score_note)
        score_layout.addSpacing(5)
        score_layout.addWidget(self.signals_title)
        score_layout.addLayout(grid)
        score_layout.addStretch()

        top = QHBoxLayout()
        top.setSpacing(16)
        top.addWidget(summary, 1)
        top.addWidget(score_card, 1)

        rec = frame("recommendationCard")
        self.rec_title = label("captureCardTitle")
        self.rec_note = label("captureCardText", True)

        self.rec_area = QWidget()
        self.rec_layout = QVBoxLayout(self.rec_area)
        self.rec_layout.setContentsMargins(0, 0, 0, 0)
        self.rec_layout.setSpacing(7)

        rec_layout = QVBoxLayout(rec)
        rec_layout.setContentsMargins(20, 14, 20, 14)
        rec_layout.addWidget(self.rec_title)
        rec_layout.addWidget(self.rec_note)
        rec_layout.addWidget(self.rec_area, 1)

        actions = frame("checkInActionCard")
        self.done_note = label("checkInInformation", True)
        self.done_button = button("submitCheckInButton", 44, 160)
        self.done_button.clicked.connect(self.finish)

        action_layout = QHBoxLayout(actions)
        action_layout.addWidget(self.done_note)
        action_layout.addStretch()
        action_layout.addWidget(self.done_button)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 20, 40, 22)
        layout.setSpacing(10)
        layout.addLayout(self.header())
        layout.addWidget(self.result_title)
        layout.addWidget(self.result_subtitle)
        layout.addLayout(top, 2)
        layout.addWidget(rec, 3)
        layout.addWidget(actions)
        return page

    def set_busy(self, busy):
        self.sidebar.setEnabled(not busy)

    # ---------------- Video ----------------

    def toggle_video(self):
        self.stop_video() if self.video_recording else self.start_video()

    def start_video(self):
        if not self.reset_recordings():
            return

        camera = QMediaDevices.defaultVideoInput()
        mic = QMediaDevices.defaultAudioInput()

        if camera.isNull():
            return self.status(self.t("no_camera"))

        if mic.isNull():
            return self.status(self.t("no_microphone"))

        self.set_busy(True)

        self.capture_session = QMediaCaptureSession(self)
        self.camera = QCamera(camera)
        self.camera_audio = QAudioInput(mic)
        self.recorder = QMediaRecorder()

        self.capture_session.setCamera(self.camera)
        self.capture_session.setAudioInput(self.camera_audio)
        self.capture_session.setRecorder(self.recorder)
        self.capture_session.setVideoOutput(self.video_widget)

        self.recorder.setMediaFormat(QMediaFormat(QMediaFormat.FileFormat.MPEG4))
        self.recorder.setQuality(QMediaRecorder.Quality.NormalQuality)
        self.recorder.errorOccurred.connect(self.video_error)

        path = RECORDINGS / f"video_{datetime.now():%Y%m%d_%H%M%S}.mp4"
        self.video_file = str(path)
        self.video_local = True

        self.recorder.setOutputLocation(QUrl.fromLocalFile(str(path)))
        self.video_stack.setCurrentWidget(self.video_widget)

        self.camera.start()
        self.recorder.record()

        self.video_recording = True
        self.recording_mode = "video"
        self.elapsed = 0

        self.video_time.setText("00:00")
        self.video_status.setText(self.t("recording"))
        self.video_button.setText(self.t("stop_video"))

        self.video_play.setEnabled(False)
        self.audio_button.setEnabled(False)
        self.timer.start(1000)
        self.capture_status.hide()

    def stop_video(self, discard=False):
        self.timer.stop()
        self.video_recording = False
        self.recording_mode = ""
        self.video_discard = discard

        if self.camera:
            self.camera.stop()

        if self.capture_session:
            self.capture_session.setVideoOutput(None)

        if self.recorder:
            self.recorder.recorderStateChanged.connect(self.video_stopped)
            self.recorder.stop()

    def video_stopped(self, state):
        if state != QMediaRecorder.RecorderState.StoppedState:
            return

        path = self.video_file
        discard = self.video_discard

        self.recorder = None
        self.camera = None
        self.camera_audio = None
        self.capture_session = None
        self.audio_button.setEnabled(True)

        if discard:
            self.release_players()

            if self.video_local and path:
                Path(path).unlink(missing_ok=True)

            self.clear_video()
            self.set_busy(False)
            return

        self.video_status.setText(self.t("video_recorded"))
        self.video_button.setText(self.t("record_again"))
        self.video_play.setEnabled(True)

        QTimer.singleShot(250, lambda: self.show_video(path))
        QTimer.singleShot(500, lambda: self.start_transcription(path, "video"))

    def video_error(self, *args):
        self.status(self.t("video_failed"))
        self.stop_video(True)

    # ---------------- Audio ----------------

    def toggle_audio(self):
        self.stop_audio() if self.audio_recording else self.start_audio()

    def start_audio(self):
        if not self.reset_recordings():
            return
        mic = QMediaDevices.defaultAudioInput()

        if mic.isNull():
            return self.status(self.t("no_microphone"))

        self.audio_format = mic.preferredFormat()
        self.audio_source = QAudioSource(mic, self.audio_format, self)
        self.audio_device = self.audio_source.start()

        if self.audio_device is None:
            return self.status(self.t("microphone_failed"))

        self.set_busy(True)

        self.audio_pcm = bytearray()
        self.audio_device.readyRead.connect(self.read_audio)

        self.audio_recording = True
        self.recording_mode = "audio"
        self.elapsed = 0

        self.audio_time.setText("00:00")
        self.audio_status.setText(self.t("recording"))
        self.audio_button.setText(self.t("stop_audio"))

        self.audio_play.setEnabled(False)
        self.video_button.setEnabled(False)
        self.timer.start(1000)
        self.capture_status.hide()

    def read_audio(self):
        raw = bytes(self.audio_device.readAll())
        samples = self.decode_audio(raw)

        if not samples:
            return

        rms = math.sqrt(sum(x * x for x in samples) / len(samples))
        self.waveform.add_level(min(1, rms * 4.5))

        for sample in samples:
            value = int(max(-1, min(1, sample)) * 32767)
            self.audio_pcm.extend(struct.pack("<h", value))

    def decode_audio(self, raw):
        fmt = self.audio_format.sampleFormat()
        channels = max(1, self.audio_format.channelCount())
        endian = "<" if sys.byteorder == "little" else ">"

        formats = {
            QAudioFormat.SampleFormat.Int16: (2, "h", 32768.0),
            QAudioFormat.SampleFormat.Int32: (4, "i", 2147483648.0),
            QAudioFormat.SampleFormat.Float: (4, "f", 1.0),
        }

        if fmt == QAudioFormat.SampleFormat.UInt8:
            values = [(x - 128) / 128 for x in raw]
        else:
            size, code, scale = formats[fmt]
            usable = len(raw) - len(raw) % size
            values = [x[0] / scale for x in struct.iter_unpack(endian + code, raw[:usable])]

        if channels == 1:
            return values

        usable = len(values) - len(values) % channels
        return [
            sum(values[i:i + channels]) / channels
            for i in range(0, usable, channels)
        ]

    def stop_audio(self, discard=False):
        self.timer.stop()

        if self.audio_source:
            self.audio_source.stop()

        self.audio_recording = False
        self.recording_mode = ""
        self.video_button.setEnabled(True)

        if discard or not self.audio_pcm:
            self.clear_audio()
            self.set_busy(False)

        else:
            path = RECORDINGS / f"audio_{datetime.now():%Y%m%d_%H%M%S}.wav"

            with wave.open(str(path), "wb") as f:
                f.setnchannels(1)
                f.setsampwidth(2)
                f.setframerate(self.audio_format.sampleRate())
                f.writeframes(bytes(self.audio_pcm))

            self.audio_file = str(path)
            self.audio_local = True

            self.audio_status.setText(self.t("audio_recorded"))
            self.audio_button.setText(self.t("record_again"))
            self.audio_play.setEnabled(True)

            self.prepare_waveform(str(path))
            self.start_transcription(str(path), "audio")

        self.audio_source = self.audio_device = self.audio_format = None
        self.audio_pcm = bytearray()

    def update_time(self):
        self.elapsed += 1
        text = f"{self.elapsed // 60:02d}:{self.elapsed % 60:02d}"

        if self.recording_mode == "video":
            self.video_time.setText(text)
        else:
            self.audio_time.setText(text)

        if self.elapsed >= 60:
            self.stop_video() if self.recording_mode == "video" else self.stop_audio()

    # ---------------- Playback ----------------

    def release_players(self):
        self.video_player.stop()
        self.video_player.setSource(QUrl())
        self.video_player.setVideoOutput(None)

        self.audio_player.stop()
        self.audio_player.setSource(QUrl())

    def set_play_icon(self, btn, playing):
        btn.setText("")
        btn.setIcon(self.pause_icon if playing else self.play_icon)

    def toggle_video_play(self):
        if self.video_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return self.video_player.pause()

        self.audio_player.stop()
        self.video_player.setVideoOutput(self.video_widget)
        self.video_player.setSource(QUrl.fromLocalFile(self.video_file))
        self.video_stack.setCurrentWidget(self.video_widget)
        self.video_player.play()

    def show_video(self, path):
        self.video_player.setVideoOutput(self.video_widget)
        self.video_player.setSource(QUrl.fromLocalFile(path))
        self.video_stack.setCurrentWidget(self.video_widget)
        self.video_player.play()
        QTimer.singleShot(450, self.video_player.pause)

    def video_state(self, state):
        self.set_play_icon(
            self.video_play,
            state == QMediaPlayer.PlaybackState.PlayingState,
        )

    def toggle_audio_play(self):
        if self.audio_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            return self.audio_player.pause()

        self.video_player.stop()
        self.audio_player.setSource(QUrl.fromLocalFile(self.audio_file))
        self.audio_player.play()

    def audio_state(self, state):
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self.set_play_icon(self.audio_play, playing)

        if not playing:
            self.waveform.clear()

    @staticmethod
    def set_duration(widget, ms):
        if ms > 0:
            seconds = ms // 1000
            widget.setText(f"{seconds // 60:02d}:{seconds % 60:02d}")

    def prepare_waveform(self, path):
        audio, _ = librosa.load(path, sr=16000, mono=True)
        levels = librosa.feature.rms(y=audio)[0].tolist()
        maximum = max(levels) if levels else 1
        self.audio_levels = [x / maximum for x in levels]

    def sync_waveform(self, position):
        if not self.audio_levels:
            return

        duration = max(1, self.audio_player.duration())
        index = min(
            len(self.audio_levels) - 1,
            int(position / duration * len(self.audio_levels)),
        )

        self.waveform.add_level(self.audio_levels[index])

    # ---------------- Upload ----------------

    def open_upload(self):
        if self.transcription_worker and self.transcription_worker.isRunning():
            return self.status(self.t("wait_transcript"))

        dialog = UploadDialog(self.current_language, self)

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        self.reset_recordings()
        path = dialog.selected_path

        if dialog.selected_type == "audio":
            self.audio_file = path
            self.audio_local = False
            self.audio_status.setText(f"{self.t('uploaded')}: {Path(path).name}")
            self.audio_button.setText(self.t("record_instead"))
            self.audio_play.setEnabled(True)
            self.video_button.setEnabled(False)
            self.prepare_waveform(path)
            self.start_transcription(path, "audio")

        else:
            self.video_file = path
            self.video_local = False
            self.video_status.setText(f"{self.t('uploaded')}: {Path(path).name}")
            self.video_button.setText(self.t("record_instead"))
            self.video_play.setEnabled(True)
            self.audio_button.setEnabled(False)
            self.show_video(path)
            self.start_transcription(path, "video")

    # ---------------- Whisper ----------------

    def start_transcription(self, path, recording_type):
        self.set_busy(True)
        self.submit_button.setEnabled(False)
        self.transcript.clear()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(self.t("creating_transcript"))

        self.transcription_worker = TranscriptionWorker(
            path,
            recording_type,
            self,
            language_name=self.current_language,
        )

        self.transcription_worker.progress.connect(
            lambda key: self.transcript.setPlaceholderText(self.t(key))
        )
        self.transcription_worker.completed.connect(self.transcription_done)
        self.transcription_worker.failed.connect(self.transcription_failed)
        self.transcription_worker.start()

    def transcription_done(self, text):
        self.transcript.setPlainText(text)
        self.transcript.setReadOnly(False)
        self.submit_button.setEnabled(True)
        self.transcription_worker = None
        self.set_busy(False)

    def transcription_failed(self, message):
        self.transcript.clear()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(self.t("transcript_unavailable"))
        self.submit_button.setEnabled(False)
        self.status(self.t("transcription_failed"))
        self.transcription_worker = None
        self.set_busy(False)

    # ---------------- Analysis ----------------

    def submit_check_in(self):
        if self.video_recording or self.audio_recording:
            return self.status(self.t("stop_before_submit"))

        if not self.video_file and not self.audio_file:
            return self.status(self.t("record_first"))

        if self.transcription_worker and self.transcription_worker.isRunning():
            return self.status(self.t("wait_transcript"))

        text = self.transcript.toPlainText().strip()

        if not text:
            return self.status(self.t("transcript_required"))

        path = self.video_file or self.audio_file
        recording_type = "video" if self.video_file else "audio"

        previous = get_recent_scores(self.user_id, 1)
        previous_score = previous[-1] if previous else None

        trend = (
            f"Previous wellbeing score: {previous_score:.0f}/100."
            if previous_score is not None
            else "No previous check-in trend is available."
        )

        self.release_players()

        self.processing_key = "processing_loading"
        self.processing_message.setText(self.t(self.processing_key))
        self.stack.setCurrentWidget(self.processing_page)
        self.spinner.start()

        self.analysis_worker = AnalysisWorker(
            path,
            recording_type,
            text,
            self,
            language_name=self.current_language,
            trend=trend,
        )

        self.analysis_worker.progress.connect(self.analysis_progress)
        self.analysis_worker.completed.connect(self.analysis_done)
        self.analysis_worker.failed.connect(self.analysis_failed)
        self.set_busy(True)
        self.analysis_worker.start()

    def analysis_progress(self, key):
        self.processing_key = key
        self.processing_message.setText(self.t(key))

    def analysis_done(self, result):
        self.spinner.stop()

        previous = get_recent_scores(self.user_id, 1)
        previous_score = previous[-1] if previous else None
        score = round(result["wellbeing_score"])

        phrase, explanation, image = self.result_text(score, previous_score)

        result["phrase"] = phrase
        result["explanation"] = explanation
        result["image_name"] = image

        save_check_in(self.user_id, result)

        self.populate_result(result)
        self.stack.setCurrentWidget(self.result_page)
        self.analysis_worker = None
        self.set_busy(False)

    def analysis_failed(self, message):
        print("ANALYSIS ERROR:", message)

        self.spinner.stop()
        self.stack.setCurrentWidget(self.capture_page)
        self.status(self.t("analysis_failed"))

        if self.video_file:
            self.show_video(self.video_file)

        self.analysis_worker = None
        self.set_busy(False)

    # ---------------- Results ----------------

    def result_text(self, score, previous):
        if previous is None:
            if score >= 67:
                keys = "first_high_phrase", "first_high_text", "wellbeing_high.png"
            elif score >= 34:
                keys = "first_mid_phrase", "first_mid_text", "wellbeing_mid.png"
            else:
                keys = "first_low_phrase", "first_low_text", "wellbeing_low.png"

        elif score - previous >= 5:
            keys = "improved_phrase", "improved_text", "wellbeing_high.png"

        elif score - previous <= -5:
            keys = "lower_phrase", "lower_text", "wellbeing_low.png"

        else:
            keys = "steady_phrase", "steady_text", "wellbeing_mid.png"

        return self.t(keys[0]), self.t(keys[1]), keys[2]

    def populate_result(self, result):
        score = round(result["wellbeing_score"])

        pixmap = QPixmap(str(IMAGES / result["image_name"]))
        self.result_image.setPixmap(
            pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        self.result_phrase.setText(result["phrase"])
        self.result_explanation.setText(result["explanation"])

        self.score.setValue(score)
        self.score.setFormat(f"{score} / 100")
        self.score.setProperty("zone", "high" if score >= 67 else "mid" if score >= 34 else "low")
        self.score.style().unpolish(self.score)
        self.score.style().polish(self.score)

        self.set_signals(result)
        self.set_recommendations(result["recommendation"])

    def set_signals(self, result):
        na = self.t("not_available")

        heads = {
            "Centred": self.t("head_centred"),
            "Slightly off-centre": self.t("head_slightly_off"),
            "Off-centre": self.t("head_off"),
        }

        blink = result.get("blink_rate")
        head = result.get("head_position")

        values = {
            "blink_rate": f"{blink:.1f}/min" if blink is not None else na,
            "head_position": heads.get(head, na),
            "speech_rate": f"{result['speech_rate']:.0f}/min",
            "disfluency": f"{result['disfluency_rate'] * 100:.1f}%",
            "lexical_variety": f"{result['lexical_variety']:.2f}",
        }

        for key, value in values.items():
            self.signal_values[key].setText(value)

    def set_recommendations(self, text):
        while self.rec_layout.count():
            item = self.rec_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for item in re.split(r"(?=\b[1-3][.)]\s*)", text):
            item = item.strip().replace("**", "")

            if not item:
                continue

            w = label("recommendationItem", True)
            w.setText(item)

            if self.current_language == "Tamil":
                w.setStyleSheet("font-size:9px;")

            self.rec_layout.addWidget(w)

        self.rec_layout.addStretch()

    # ---------------- Translation ----------------

    def t(self, key):
        return get_text(self.current_language, key)

    def set_language(self, language):
        self.current_language = language
        self.sidebar.set_language(language)

        texts = {
            self.capture_title: "record_check_in",
            self.capture_subtitle: "record_instruction",
            self.video_title: "video_check_in",
            self.camera_off: "camera_off",
            self.audio_title: "audio_check_in",
            self.audio_note: "audio_note",
            self.transcript_title: "automatic_transcript",
            self.transcript_note: "transcript_note",
            self.upload_button: "upload",
            self.delete_button: "delete",
            self.submit_button: "submit",
            self.processing_title: "processing_title",
            self.processing_note: "processing_note",
            self.result_title: "wellbeing_summary",
            self.result_subtitle: "experimental_note",
            self.summary_note: "summary_note",
            self.score_label: "wellbeing_score",
            self.score_note: "score_caveat",
            self.signals_title: "supporting_signals",
            self.rec_title: "supportive_recommendations",
            self.rec_note: "qwen_note",
            self.done_note: "saved_history",
            self.done_button: "done",
        }

        for w, key in texts.items():
            w.setText(self.t(key))

        for key, w in self.signal_names.items():
            w.setText(self.t(key))

        self.processing_message.setText(self.t(self.processing_key))

        if not self.transcript.toPlainText():
            self.transcript.setPlaceholderText(self.t("transcript_placeholder"))

        self.refresh_recording_text()
        self.tamil_fonts()

    def refresh_recording_text(self):
        if self.video_recording:
            self.video_status.setText(self.t("recording"))
            self.video_button.setText(self.t("stop_video"))

        elif self.video_file:
            self.video_status.setText(
                self.t("video_recorded")
                if self.video_local
                else f"{self.t('uploaded')}: {Path(self.video_file).name}"
            )
            self.video_button.setText(
                self.t("record_again") if self.video_local else self.t("record_instead")
            )

        else:
            self.video_status.setText(self.t("not_recorded"))
            self.video_button.setText(self.t("start_video"))

        if self.audio_recording:
            self.audio_status.setText(self.t("recording"))
            self.audio_button.setText(self.t("stop_audio"))

        elif self.audio_file:
            self.audio_status.setText(
                self.t("audio_recorded")
                if self.audio_local
                else f"{self.t('uploaded')}: {Path(self.audio_file).name}"
            )
            self.audio_button.setText(
                self.t("record_again") if self.audio_local else self.t("record_instead")
            )

        else:
            self.audio_status.setText(self.t("not_recorded"))
            self.audio_button.setText(self.t("start_audio"))

    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        widgets = [
            (self.capture_title, 18), (self.capture_subtitle, 10),
            (self.video_title, 12),
            (self.audio_title, 12), (self.audio_note, 9),
            (self.transcript_title, 12), (self.transcript_note, 9),
            (self.transcript, 10), (self.video_button, 10),
            (self.audio_button, 10), (self.upload_button, 10),
            (self.delete_button, 10), (self.submit_button, 10),
            (self.processing_title, 18), (self.processing_message, 11),
            (self.processing_note, 10), (self.result_title, 18),
            (self.result_subtitle, 10), (self.result_phrase, 21),
            (self.result_explanation, 11), (self.signals_title, 12),
            (self.rec_title, 12), (self.rec_note, 9),
            (self.done_note, 9), (self.done_button, 10),
        ]

        for w, size in widgets:
            w.setStyleSheet(f"font-size:{size}px;" if tamil else "")

        for w in self.user_labels:
            w.setStyleSheet("font-size:11px;" if tamil else "")

        for w in list(self.signal_names.values()) + list(self.signal_values.values()):
            w.setStyleSheet("font-size:9px;" if tamil else "")

    # ---------------- Reset ----------------

    def status(self, text):
        self.capture_status.setText(text)
        self.capture_status.show()

    def clear_video(self):
        self.video_file = ""
        self.video_local = False
        self.video_status.setText(self.t("not_recorded"))
        self.video_time.setText("00:00")
        self.video_button.setText(self.t("start_video"))
        self.video_play.setEnabled(False)
        self.set_play_icon(self.video_play, False)
        self.video_stack.setCurrentIndex(0)

    def clear_audio(self):
        self.audio_file = ""
        self.audio_local = False
        self.audio_status.setText(self.t("not_recorded"))
        self.audio_time.setText("00:00")
        self.audio_button.setText(self.t("start_audio"))
        self.audio_play.setEnabled(False)
        self.audio_levels = []
        self.waveform.clear()
        self.set_play_icon(self.audio_play, False)

    def reset_recordings(self):
        if self.transcription_worker and self.transcription_worker.isRunning():
            self.status(self.t("wait_transcript"))
            return False

        self.release_players()

        old_video = self.video_file if self.video_local and not self.video_recording else ""
        old_audio = self.audio_file if self.audio_local and not self.audio_recording else ""

        if self.video_recording:
            self.stop_video(True)

        if self.audio_recording:
            self.stop_audio(True)

        if old_video:
            Path(old_video).unlink(missing_ok=True)

        if old_audio:
            Path(old_audio).unlink(missing_ok=True)

        self.clear_video()
        self.clear_audio()

        self.video_button.setEnabled(True)
        self.audio_button.setEnabled(True)

        self.transcript.clear()
        self.transcript.setReadOnly(True)
        self.transcript.setPlaceholderText(self.t("transcript_placeholder"))

        self.submit_button.setEnabled(False)
        self.capture_status.hide()

        return True

    def set_user(self, full_name, user_id=None):
        first = full_name.split()[0] if full_name else ""

        for w in self.user_labels:
            w.setText(first)

        self.user_id = user_id

    def reset_page(self):
        if self.analysis_worker and self.analysis_worker.isRunning():
            return False

        if not self.reset_recordings():
            return False

        self.stack.setCurrentWidget(self.capture_page)
        return True

    def finish(self):
        self.home_requested.emit()