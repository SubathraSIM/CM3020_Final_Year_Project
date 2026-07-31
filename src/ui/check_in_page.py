import math
import random
import struct
import sys
import wave
from datetime import date, datetime
from pathlib import Path
import calendar

import librosa
import numpy as np
from PySide6.QtCore import (
    QEvent,
    QPointF,
    QRect,
    QRectF,
    QSize,
    Qt,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtMultimedia import (
    QAudioFormat,
    QAudioInput,
    QAudioOutput,
    QAudioSource,
    QCamera,
    QMediaCaptureSession,
    QMediaDevices,
    QMediaFormat,
    QMediaPlayer,
    QMediaRecorder,
)
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QToolTip,
    QVBoxLayout,
    QWidget,
)

from src.ai.multimodal_pipeline import (
    AnalysisWorker,
    TranscriptionWorker,
)
from src.database.database import (
    get_check_in_count,
    get_month_check_ins,
    get_recent_scores,
    save_check_in,
)
from src.ui.home_page import HoverSidebar


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RECORDINGS_FOLDER = PROJECT_ROOT / "data" / "recordings"
RECORDINGS_FOLDER.mkdir(parents=True, exist_ok=True)

ICONS_FOLDER = PROJECT_ROOT / "src" / "images"


class WaveformWidget(QWidget):
    BARS = 44

    def __init__(self):
        super().__init__()

        self.display_levels = [0.0] * self.BARS
        self.static_levels = [0.0] * self.BARS

        self.weights = [
            0.55
            + 0.45
            * math.sin(
                math.pi * index / (self.BARS - 1)
            )
            for index in range(self.BARS)
        ]

        self.setMinimumHeight(92)

    def clear(self):
        self.display_levels = [0.0] * self.BARS
        self.static_levels = [0.0] * self.BARS
        self.update()

    def add_level(self, level):
        level = max(
            0.0,
            min(float(level), 1.0),
        )

        for index in range(self.BARS):
            target = (
                level
                * self.weights[index]
                * random.uniform(0.72, 1.08)
            )

            target = max(
                0.0,
                min(target, 1.0),
            )

            self.display_levels[index] = (
                self.display_levels[index] * 0.52
                + target * 0.48
            )

        self.update()

    def set_static_levels(self, levels):
        if not levels:
            self.clear()
            return

        values = np.asarray(
            levels,
            dtype=float,
        )

        if values.size != self.BARS:
            source_positions = np.linspace(
                0.0,
                1.0,
                values.size,
            )

            target_positions = np.linspace(
                0.0,
                1.0,
                self.BARS,
            )

            values = np.interp(
                target_positions,
                source_positions,
                values,
            )

        maximum = float(
            np.max(values)
        )

        if maximum > 0:
            values = values / maximum

        self.static_levels = [
            max(0.04, min(float(value), 1.0))
            for value in values
        ]

        self.restore_static()

    def restore_static(self):
        self.display_levels = list(
            self.static_levels
        )

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.Antialiasing
        )

        painter.fillRect(
            self.rect(),
            QColor("#F8FAFC"),
        )

        width = self.width()
        height = self.height()
        middle = height / 2
        padding = 14
        gap = 3.0

        usable_width = (
            width - padding * 2
        )

        bar_width = max(
            2.5,
            (
                usable_width
                - gap * (self.BARS - 1)
            )
            / self.BARS,
        )

        maximum_bar_height = (
            height * 0.78
        )

        painter.setPen(Qt.NoPen)

        x_position = float(padding)

        for value in self.display_levels:
            bar_height = max(
                3.0,
                value * maximum_bar_height,
            )

            rectangle = QRectF(
                x_position,
                middle - bar_height / 2,
                bar_width,
                bar_height,
            )

            colour = (
                QColor("#2563EB")
                if value > 0.06
                else QColor("#C7D2FE")
            )

            painter.setBrush(colour)

            radius = min(
                bar_width / 2.0,
                3.0,
            )

            painter.drawRoundedRect(
                rectangle,
                radius,
                radius,
            )

            x_position += (
                bar_width + gap
            )


class LoadingSpinner(QWidget):
    def __init__(self):
        super().__init__()

        self.angle = 0
        self.setFixedSize(90, 90)

        self.timer = QTimer(self)
        self.timer.timeout.connect(
            self._rotate
        )

    def start(self):
        self.timer.start(40)

    def stop(self):
        self.timer.stop()

    def _rotate(self):
        self.angle = (
            self.angle - 12
        ) % 360

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.Antialiasing
        )

        pen = QPen(
            QColor("#2563EB"),
            7,
        )

        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)

        painter.drawArc(
            QRectF(10, 10, 70, 70),
            self.angle * 16,
            275 * 16,
        )


class MiniTrendGraph(QWidget):
    def __init__(self):
        super().__init__()

        self.points = []
        self._hitboxes = []
        self._half_step = 12.0
        self.setMinimumHeight(100)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        self.setMouseTracking(True)

    def set_points(self, points):
        self.points = list(points)
        self.update()

    def paintEvent(self, event):
        self._hitboxes = []

        if len(self.points) < 2:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        left = 44
        right = 16
        top = 16
        bottom = 26
        plot_w = width - left - right
        plot_h = height - top - bottom

        painter.setFont(QFont("Segoe UI", 8))

        for row in range(3):
            y = top + row * plot_h / 2
            painter.setPen(QPen(QColor("#EEF2F7"), 1))
            painter.drawLine(left, int(y), width - right, int(y))

        painter.setPen(QColor("#94A3B8"))
        painter.drawText(
            QRectF(0, top - 8, left - 8, 16),
            Qt.AlignRight | Qt.AlignVCenter,
            "Higher",
        )
        painter.drawText(
            QRectF(0, top + plot_h - 8, left - 8, 16),
            Qt.AlignRight | Qt.AlignVCenter,
            "Lower",
        )

        count = len(self.points)
        step = plot_w / (count - 1)
        self._half_step = max(step / 2, 10.0)

        pixels = []
        for index, item in enumerate(self.points):
            score = float(item["score"])
            x = left + index * step
            y = top + (100 - score) / 100 * plot_h
            point = QPointF(x, y)
            pixels.append(point)
            self._hitboxes.append((point, item))

        area = QPainterPath()
        area.moveTo(pixels[0].x(), top + plot_h)
        for point in pixels:
            area.lineTo(point.x(), point.y())
        area.lineTo(pixels[-1].x(), top + plot_h)
        area.closeSubpath()

        gradient = QLinearGradient(0, top, 0, top + plot_h)
        gradient.setColorAt(0.0, QColor(37, 99, 235, 60))
        gradient.setColorAt(1.0, QColor(37, 99, 235, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(gradient))
        painter.drawPath(area)

        line_pen = QPen(QColor("#2563EB"), 3)
        line_pen.setCapStyle(Qt.RoundCap)
        line_pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(line_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPolyline(QPolygonF(pixels))

        for point in pixels:
            painter.setPen(QPen(QColor("#2563EB"), 2))
            painter.setBrush(QColor("#FFFFFF"))
            painter.drawEllipse(point, 4.5, 4.5)

        painter.setPen(QColor("#94A3B8"))
        first_date = str(
            self.points[0].get(
                "day",
                1,
            )
        )

        last_date = str(
            self.points[-1].get(
                "day",
                len(self.points),
            )
        )
        painter.drawText(
            QRectF(left, height - bottom + 4, plot_w / 2, 16),
            Qt.AlignLeft | Qt.AlignVCenter,
            first_date,
        )
        painter.drawText(
            QRectF(left + plot_w / 2, height - bottom + 4, plot_w / 2, 16),
            Qt.AlignRight | Qt.AlignVCenter,
            last_date,
        )

    def mouseMoveEvent(self, event):
        if not self._hitboxes:
            return

        position = event.position()
        nearest = min(
            self._hitboxes,
            key=lambda hit: abs(hit[0].x() - position.x()),
        )

        if abs(nearest[0].x() - position.x()) <= self._half_step:
            point, item = nearest

            date_text = str(
                item.get("date", "")
            )[:10]

            if not item.get(
                "has_check_in",
                True,
            ):
                tooltip_text = (
                    f"<b>No check-in</b>"
                    f"<br>{date_text}"
                )
            else:
                phrase = item.get(
                    "phrase",
                    "",
                )

                score = int(
                    round(
                        float(
                            item.get(
                                "score",
                                0,
                            )
                        )
                    )
                )

                tooltip_text = (
                    f"<b>{phrase}</b>"
                    f"<br>{date_text}"
                    f"<br>Score {score} / 100"
                )

            QToolTip.showText(
                event.globalPosition().toPoint(),
                tooltip_text,
                self,
            )
        else:
            QToolTip.hideText()


class UploadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.selected_path = ""
        self.selected_type = "Audio"

        self.setWindowTitle(
            "Upload recording"
        )

        self.setModal(True)
        self.setFixedSize(520, 370)

        card = QFrame()
        card.setObjectName("uploadCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        title = QLabel(
            "Upload a recording"
        )
        title.setObjectName("uploadTitle")

        note = QLabel(
            "Choose the recording type, then select one file."
        )
        note.setObjectName("uploadNote")

        type_label = QLabel(
            "Recording type"
        )
        type_label.setObjectName("fieldLabel")

        self.type_combo = QComboBox()
        self.type_combo.setObjectName(
            "uploadTypeCombo"
        )
        self.type_combo.setFixedHeight(46)
        self.type_combo.addItems(
            ["Audio", "Video"]
        )
        self.type_combo.currentTextChanged.connect(
            self._change_type
        )

        self.file_label = QLabel(
            "No file selected"
        )
        self.file_label.setObjectName(
            "uploadFileLabel"
        )
        self.file_label.setWordWrap(True)
        self.file_label.setMinimumHeight(48)

        choose_button = QPushButton(
            "Choose file"
        )
        choose_button.setObjectName(
            "uploadChooseButton"
        )
        choose_button.setFixedHeight(46)
        choose_button.clicked.connect(
            self._choose_file
        )

        cancel_button = QPushButton(
            "Cancel"
        )
        cancel_button.setObjectName(
            "secondaryButton"
        )
        cancel_button.setFixedSize(
            110,
            44,
        )
        cancel_button.clicked.connect(
            self.reject
        )

        self.use_button = QPushButton(
            "Use this file"
        )
        self.use_button.setObjectName(
            "primaryButton"
        )
        self.use_button.setFixedSize(
            130,
            44,
        )
        self.use_button.setEnabled(False)
        self.use_button.clicked.connect(
            self.accept
        )

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(self.use_button)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            30,
            26,
            30,
            26,
        )
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addSpacing(4)
        layout.addWidget(type_label)
        layout.addWidget(self.type_combo)
        layout.addWidget(self.file_label)
        layout.addWidget(choose_button)
        layout.addStretch()
        layout.addLayout(buttons)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )
        outer_layout.addWidget(card)

    def _change_type(self, recording_type):
        self.selected_type = recording_type
        self.selected_path = ""
        self.file_label.setText(
            "No file selected"
        )
        self.use_button.setEnabled(False)

    def _choose_file(self):
        if self.selected_type == "Audio":
            file_filter = (
                "Audio files "
                "(*.wav *.mp3 *.m4a *.flac *.ogg)"
            )
        else:
            file_filter = (
                "Video files "
                "(*.mp4 *.mov *.avi *.mkv *.webm)"
            )

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select "
            + self.selected_type.lower()
            + " file",
            "",
            file_filter,
        )

        if not path:
            return

        self.selected_path = path
        self.file_label.setText(
            Path(path).name
        )
        self.use_button.setEnabled(True)


class CheckInPage(QWidget):
    home_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()

        QApplication.instance().installEventFilter(self)

        self._play_icon = QIcon(str(ICONS_FOLDER / "play.png"))
        self._pause_icon = QIcon(str(ICONS_FOLDER / "pause.png"))

        self.user_id = None

        self.video_file_path = ""
        self.audio_file_path = ""

        self.video_file_is_local = False
        self.audio_file_is_local = False

        self.video_recording = False
        self.audio_recording = False

        self.elapsed_seconds = 0
        self.active_recording_mode = ""

        self.current_transcript = ""
        self.audio_playback_levels = []

        self.transcription_worker = None
        self.analysis_worker = None

        self.video_capture_session = None
        self.video_camera = None
        self.video_audio_input = None
        self.video_recorder = None

        self.audio_source = None
        self.audio_device = None
        self.audio_format = None
        self.audio_pcm = bytearray()

        self.video_player = QMediaPlayer(self)
        self.video_audio_output = QAudioOutput(self)
        self.video_audio_output.setVolume(1.0)
        self.video_player.setAudioOutput(
            self.video_audio_output
        )

        self.audio_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.audio_output.setVolume(1.0)
        self.audio_player.setAudioOutput(
            self.audio_output
        )

        self.audio_player.durationChanged.connect(
            self._update_audio_duration
        )

        self.video_player.playbackStateChanged.connect(
            self._update_video_play_button
        )

        self.video_player.durationChanged.connect(
            self._update_video_duration
        )

        self.audio_player.playbackStateChanged.connect(
            self._update_audio_play_button
        )

        self.audio_player.positionChanged.connect(
            self._sync_audio_waveform
        )

        self.recording_timer = QTimer(self)
        self.recording_timer.timeout.connect(
            self._update_recording_time
        )

        self.sidebar = HoverSidebar()

        self.sidebar.home_requested.connect(
            self.home_requested.emit
        )

        self.sidebar.logout_requested.connect(
            self.logout_requested.emit
        )

        self.sidebar.home_button.setProperty(
            "active",
            False,
        )

        self.sidebar.check_in_button.setProperty(
            "active",
            True,
        )

        self._refresh_style(
            self.sidebar.home_button
        )

        self._refresh_style(
            self.sidebar.check_in_button
        )

        self.flow_stack = QStackedWidget()

        self.capture_page = (
            self._build_capture_page()
        )

        self.processing_page = (
            self._build_processing_page()
        )

        self.result_page = (
            self._build_result_page()
        )

        self.flow_stack.addWidget(
            self.capture_page
        )

        self.flow_stack.addWidget(
            self.processing_page
        )

        self.flow_stack.addWidget(
            self.result_page
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(
            self.flow_stack,
            1,
        )

    def _build_capture_page(self):
        page = QWidget()
        page.setObjectName(
            "checkInPageContent"
        )

        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            40,
            20,
            40,
            22,
        )
        layout.setSpacing(10)

        layout.addLayout(
            self._build_header("")
        )

        title = QLabel(
            "Record your check-in"
        )
        title.setObjectName(
            "checkInIntroTitle"
        )

        self.capture_status = QLabel()
        self.capture_status.setObjectName(
            "captureStatus"
        )
        self.capture_status.hide()

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(
            self.capture_status,
            0,
            Qt.AlignVCenter,
        )

        subtitle = QLabel(
            "Record video or audio. Your transcript appears after you stop."
        )
        subtitle.setObjectName(
            "checkInIntroText"
        )

        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)
        top_layout.addWidget(
            self._build_video_card(),
            1,
        )
        top_layout.addWidget(
            self._build_audio_card(),
            1,
        )

        transcript_card = (
            self._build_transcript_card()
        )

        action_card = self._build_actions()

        layout.addLayout(title_row)
        layout.addWidget(subtitle)
        layout.addLayout(top_layout, 3)
        layout.addWidget(transcript_card, 2)
        layout.addWidget(action_card)

        return page

    def _build_header(self, page_title):
        heart = QLabel("♥")
        heart.setObjectName("homeHeart")

        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        title = QLabel(page_title)
        title.setObjectName(
            "checkInPageTitle"
        )

        self.user_label = QLabel()
        self.user_label.setObjectName(
            "welcomeLabel"
        )
        self.user_label.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        layout.setSpacing(8)
        layout.addWidget(heart)
        layout.addWidget(brand)
        if page_title:
            layout.addSpacing(18)
            layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.user_label)

        return layout

    def _build_video_card(self):
        card = QFrame()
        card.setObjectName(
            "videoCaptureCard"
        )
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        title = QLabel(
            "Video check-in"
        )
        title.setObjectName(
            "captureCardTitle"
        )

        note = QLabel(
            "Records camera and microphone together."
        )
        note.setObjectName(
            "captureCardText"
        )

        self.video_stack = QStackedWidget()
        self.video_stack.setObjectName(
            "videoPreviewStack"
        )
        self.video_stack.setMinimumHeight(170)

        placeholder = QWidget()
        placeholder.setObjectName(
            "videoPlaceholder"
        )

        placeholder_text = QLabel(
            "Camera is off"
        )
        placeholder_text.setObjectName(
            "videoPreviewText"
        )
        placeholder_text.setAlignment(
            Qt.AlignCenter
        )

        placeholder_layout = QVBoxLayout(
            placeholder
        )
        placeholder_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        placeholder_layout.addWidget(
            placeholder_text
        )

        self.video_widget = QVideoWidget()
        self.video_widget.setObjectName(
            "videoWidget"
        )
        self.video_widget.setSizePolicy(
            QSizePolicy.Ignored,
            QSizePolicy.Ignored,
        )
        self.video_widget.setAspectRatioMode(
            Qt.KeepAspectRatio
        )

        self.video_stack.addWidget(
            placeholder
        )
        self.video_stack.addWidget(
            self.video_widget
        )

        self.video_status = QLabel(
            "Not recorded"
        )
        self.video_status.setObjectName(
            "recordingStatus"
        )

        self.video_time = QLabel("00:00")
        self.video_time.setObjectName(
            "recordingTimeSmall"
        )

        self.video_play_button = QPushButton()
        self.video_play_button.setObjectName(
            "playMediaButton"
        )
        self.video_play_button.setFixedSize(
            56,
            42,
        )
        self.video_play_button.setIconSize(
            QSize(18, 18)
        )
        self.video_play_button.setCursor(
            Qt.PointingHandCursor
        )
        self.video_play_button.setEnabled(False)
        self.video_play_button.clicked.connect(
            self.toggle_video_playback
        )
        self._set_play_icon(
            self.video_play_button,
            False,
        )

        self.video_button = QPushButton(
            "Start video"
        )
        self.video_button.setObjectName(
            "recordButton"
        )
        self.video_button.setFixedSize(
            150,
            42,
        )
        self.video_button.setCursor(
            Qt.PointingHandCursor
        )
        self.video_button.clicked.connect(
            self.toggle_video_recording
        )

        controls = QHBoxLayout()
        controls.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        controls.addWidget(self.video_status)
        controls.addWidget(self.video_time)
        controls.addStretch()
        controls.addWidget(
            self.video_play_button
        )
        controls.addWidget(self.video_button)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            20,
            14,
            20,
            14,
        )
        layout.setSpacing(6)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(
            self.video_stack,
            1,
        )
        layout.addLayout(controls)

        return card

    def _build_audio_card(self):
        card = QFrame()
        card.setObjectName(
            "checkInLowerCard"
        )
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        title = QLabel(
            "Audio-only check-in"
        )
        title.setObjectName(
            "captureCardTitle"
        )

        note = QLabel(
            "The bars respond to your voice and replay."
        )
        note.setObjectName(
            "captureCardText"
        )

        self.waveform = WaveformWidget()

        self.audio_play_button = QPushButton()
        self.audio_play_button.setObjectName(
            "audioPlayButton"
        )
        self.audio_play_button.setFixedSize(
            46,
            46,
        )
        self.audio_play_button.setIconSize(
            QSize(18, 18)
        )
        self.audio_play_button.setCursor(
            Qt.PointingHandCursor
        )
        self.audio_play_button.setEnabled(False)
        self.audio_play_button.clicked.connect(
            self.toggle_audio_playback
        )
        self._set_play_icon(
            self.audio_play_button,
            False,
        )

        waveform_row = QHBoxLayout()
        waveform_row.setSpacing(10)
        waveform_row.addWidget(
            self.waveform,
            1,
        )
        waveform_row.addWidget(
            self.audio_play_button,
            0,
            Qt.AlignVCenter,
        )

        self.audio_status = QLabel(
            "Not recorded"
        )
        self.audio_status.setObjectName(
            "recordingStatus"
        )

        self.audio_time = QLabel("00:00")
        self.audio_time.setObjectName(
            "recordingTimeSmall"
        )

        self.audio_button = QPushButton(
            "Start audio"
        )
        self.audio_button.setObjectName(
            "recordButton"
        )
        self.audio_button.setFixedHeight(42)
        self.audio_button.setCursor(
            Qt.PointingHandCursor
        )
        self.audio_button.clicked.connect(
            self.toggle_audio_recording
        )

        status_row = QHBoxLayout()
        status_row.addWidget(self.audio_status)
        status_row.addStretch()
        status_row.addWidget(self.audio_time)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            18,
            14,
            18,
            14,
        )
        layout.setSpacing(7)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addLayout(
            waveform_row,
            1,
        )
        layout.addLayout(status_row)
        layout.addWidget(self.audio_button)

        return card

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            widget = QApplication.focusWidget()
            if isinstance(widget, QPlainTextEdit):
                point = event.globalPosition().toPoint()
                corner = widget.mapToGlobal(widget.rect().topLeft())
                if not QRect(corner, widget.size()).contains(point):
                    widget.clearFocus()
        return super().eventFilter(obj, event)

    def _build_transcript_card(self):
        card = QFrame()
        card.setObjectName(
            "transcriptCard"
        )
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        title = QLabel(
            "Automatic transcript"
        )
        title.setObjectName(
            "captureCardTitle"
        )

        note = QLabel(
            "Whisper creates this after recording stops. You may correct it before submission."
        )
        note.setObjectName(
            "captureCardText"
        )

        self.transcript_input = QPlainTextEdit()
        self.transcript_input.setObjectName(
            "transcriptEditor"
        )
        self.transcript_input.setPlaceholderText(
            "Your transcript will appear here."
        )
        self.transcript_input.setReadOnly(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            18,
            14,
            18,
            14,
        )
        layout.setSpacing(7)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(
            self.transcript_input,
            1,
        )

        return card

    def _build_actions(self):
        card = QFrame()
        card.setObjectName(
            "checkInActionCard"
        )
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        self.upload_button = QPushButton(
            "Upload"
        )
        self.upload_button.setObjectName(
            "uploadCheckInButton"
        )
        self.upload_button.setFixedHeight(44)
        self.upload_button.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.upload_button.setCursor(
            Qt.PointingHandCursor
        )
        self.upload_button.clicked.connect(
            self.open_upload_dialog
        )

        self.delete_button = QPushButton(
            "Delete"
        )
        self.delete_button.setObjectName(
            "deleteCheckInButton"
        )
        self.delete_button.setFixedHeight(44)
        self.delete_button.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.delete_button.setCursor(
            Qt.PointingHandCursor
        )
        self.delete_button.clicked.connect(
            self.reset_recordings
        )

        self.submit_button = QPushButton(
            "Submit"
        )
        self.submit_button.setObjectName(
            "submitCheckInButton"
        )
        self.submit_button.setFixedHeight(44)
        self.submit_button.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.submit_button.setCursor(
            Qt.PointingHandCursor
        )
        self.submit_button.setEnabled(False)
        self.submit_button.clicked.connect(
            self.submit_check_in
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(
            18,
            11,
            18,
            11,
        )
        layout.setSpacing(16)
        layout.addWidget(self.upload_button, 1)
        layout.addWidget(self.delete_button, 1)
        layout.addWidget(self.submit_button, 1)

        return card

    def _build_processing_page(self):
        page = QWidget()
        page.setObjectName("processingPage")

        card = QFrame()
        card.setObjectName("processingCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        self.spinner = LoadingSpinner()

        title = QLabel(
            "Processing your check-in"
        )
        title.setObjectName("processingTitle")
        title.setAlignment(Qt.AlignCenter)

        self.processing_message = QLabel(
            "Preparing your recording..."
        )
        self.processing_message.setObjectName(
            "processingMessage"
        )
        self.processing_message.setAlignment(
            Qt.AlignCenter
        )
        self.processing_message.setWordWrap(True)

        note = QLabel(
            "Please keep the application open while the selected models run."
        )
        note.setObjectName("processingNote")
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(
            50,
            44,
            50,
            44,
        )
        card_layout.setSpacing(14)
        card_layout.addWidget(
            self.spinner,
            0,
            Qt.AlignCenter,
        )
        card_layout.addWidget(title)
        card_layout.addWidget(
            self.processing_message
        )
        card_layout.addWidget(note)

        layout = QVBoxLayout(page)
        layout.addStretch()
        layout.addWidget(
            card,
            0,
            Qt.AlignCenter,
        )
        layout.addStretch()

        return page

    def _build_result_page(self):
        page = QWidget()
        page.setObjectName("resultPage")

        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            40,
            20,
            40,
            22,
        )
        layout.setSpacing(10)

        layout.addLayout(
            self._build_header(
                ""
            )
        )

        title = QLabel(
            "Your wellbeing summary"
        )
        title.setObjectName(
            "resultPageTitle"
        )

        subtitle = QLabel(
            "This is an experimental wellbeing estimate, not a diagnosis."
        )
        subtitle.setObjectName(
            "checkInIntroText"
        )

        top_layout = QHBoxLayout()
        top_layout.setSpacing(16)

        self.result_summary_card = QFrame()
        self.result_summary_card.setObjectName(
            "resultSummaryCard"
        )
        self.result_summary_card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        self.result_emoji = QLabel()
        self.result_emoji.setObjectName(
            "resultEmoji"
        )
        self.result_emoji.setAlignment(
            Qt.AlignCenter
        )
        self.result_emoji.setFixedHeight(105)

        emoji_font = self.result_emoji.font()
        emoji_font.setPointSize(54)
        self.result_emoji.setFont(emoji_font)
        self.result_emoji.setFixedHeight(90)

        self.result_phrase = QLabel(
            "Waiting for analysis"
        )
        self.result_phrase.setObjectName(
            "resultPhrase"
        )

        self.result_explanation = QLabel()
        self.result_explanation.setObjectName(
            "resultExplanation"
        )
        self.result_explanation.setWordWrap(True)

        summary_note = QLabel(
            "The summary combines the available text, voice and facial signals."
        )
        summary_note.setObjectName(
            "resultReminder"
        )
        summary_note.setWordWrap(True)

        summary_layout = QVBoxLayout(
            self.result_summary_card
        )
        summary_layout.setContentsMargins(
            28,
            24,
            28,
            24,
        )
        summary_layout.setSpacing(12)
        summary_layout.addWidget(
            self.result_emoji
        )
        summary_layout.addWidget(
            self.result_phrase
        )
        summary_layout.addWidget(
            self.result_explanation
        )
        summary_layout.addStretch()
        summary_layout.addWidget(summary_note)

        self.result_score_card = QFrame()
        self.result_score_card.setObjectName(
            "resultScoreCard"
        )
        self.result_score_card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        score_label = QLabel(
            "Wellbeing score"
        )
        score_label.setObjectName(
            "scoreLabel"
        )

        self.score_progress = QProgressBar()
        self.score_progress.setObjectName(
            "wellbeingProgress"
        )
        self.score_progress.setRange(0, 100)
        self.score_progress.setValue(0)
        self.score_progress.setFormat(
            "-- / 100"
        )

        self.score_caveat = QLabel(
            "An indicative signal, not a diagnosis."
        )
        self.score_caveat.setObjectName(
            "scoreCaveat"
        )
        self.score_caveat.setWordWrap(True)

        trend_label = QLabel(
            "This month's trend"
        )
        trend_label.setObjectName(
            "trendLabel"
        )

        self.trend_requirement = QLabel(
            "Check in again to see the monthly trend."
        )
        self.trend_requirement.setObjectName(
            "trendRequirement"
        )
        self.trend_requirement.setWordWrap(True)
        self.trend_requirement.setAlignment(
            Qt.AlignCenter
        )

        self.trend_graph = MiniTrendGraph()
        self.trend_graph.hide()

        score_layout = QVBoxLayout(
            self.result_score_card
        )
        score_layout.setContentsMargins(
            24,
            16,
            24,
            16,
        )
        score_layout.setSpacing(6)
        score_layout.addWidget(score_label)
        score_layout.addWidget(
            self.score_progress
        )
        score_layout.addWidget(
            self.score_caveat
        )
        score_layout.addSpacing(4)
        score_layout.addWidget(trend_label)
        score_layout.addWidget(
            self.trend_requirement,
            1,
        )
        score_layout.addWidget(
            self.trend_graph,
            1,
        )

        top_layout.addWidget(
            self.result_summary_card,
            1,
        )
        top_layout.addWidget(
            self.result_score_card,
            1,
        )

        self.recommendation_card = QFrame()
        self.recommendation_card.setObjectName(
            "recommendationCard"
        )
        self.recommendation_card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        recommendation_title = QLabel(
            "💡  Supportive recommendations"
        )
        recommendation_title.setObjectName(
            "captureCardTitle"
        )

        recommendation_note = QLabel(
            "Generated by Qwen from this check-in."
        )
        recommendation_note.setObjectName(
            "captureCardText"
        )

        self.recommendation_items = QWidget()

        self.recommendation_items.setObjectName(
            "recommendationItems"
        )

        self.recommendation_items_layout = QVBoxLayout(
            self.recommendation_items
        )

        self.recommendation_items_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.recommendation_items_layout.setSpacing(8)

        recommendation_layout = QVBoxLayout(
            self.recommendation_card
        )
        recommendation_layout.setContentsMargins(
            20,
            16,
            20,
            16,
        )
        recommendation_layout.setSpacing(7)
        recommendation_layout.addWidget(
            recommendation_title
        )
        recommendation_layout.addWidget(
            recommendation_note
        )
        recommendation_layout.addWidget(
            self.recommendation_items,
            1,
        )

        action_card = QFrame()
        action_card.setObjectName(
            "checkInActionCard"
        )
        action_card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        done_note = QLabel(
            "Your score and model outputs were saved to local history."
        )
        done_note.setObjectName(
            "checkInInformation"
        )

        done_button = QPushButton("Done")
        done_button.setObjectName(
            "submitCheckInButton"
        )
        done_button.setFixedSize(
            150,
            44,
        )
        done_button.clicked.connect(
            self._finish_result
        )

        action_layout = QHBoxLayout(
            action_card
        )
        action_layout.setContentsMargins(
            18,
            11,
            18,
            11,
        )
        action_layout.addWidget(done_note)
        action_layout.addStretch()
        action_layout.addWidget(done_button)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(top_layout, 3)
        layout.addWidget(
            self.recommendation_card,
            2,
        )
        layout.addWidget(action_card)

        return page

    def toggle_video_recording(self):
        if self.video_button.property("locked"):
            return

        if self.video_recording:
            self._stop_video_recording()
        else:
            self._start_video_recording()

    def _start_video_recording(self):
        if not self.reset_recordings():
            return

        self.capture_status.hide()

        camera_device = (
            QMediaDevices.defaultVideoInput()
        )

        if camera_device.isNull():
            self.show_capture_status(
                "No camera was found."
            )
            return

        audio_device = (
            QMediaDevices.defaultAudioInput()
        )

        if audio_device.isNull():
            self.show_capture_status(
                "No microphone was found for video recording."
            )
            return

        self.video_capture_session = (
            QMediaCaptureSession(self)
        )
        self.video_camera = QCamera(
            camera_device
        )
        self.video_audio_input = QAudioInput(
            audio_device
        )
        self.video_recorder = QMediaRecorder()

        self.video_capture_session.setCamera(
            self.video_camera
        )
        self.video_capture_session.setAudioInput(
            self.video_audio_input
        )
        self.video_capture_session.setRecorder(
            self.video_recorder
        )
        self.video_capture_session.setVideoOutput(
            self.video_widget
        )

        media_format = QMediaFormat(
            QMediaFormat.FileFormat.MPEG4
        )
        self.video_recorder.setMediaFormat(
            media_format
        )
        self.video_recorder.setQuality(
            QMediaRecorder.Quality.NormalQuality
        )
        self.video_recorder.errorOccurred.connect(
            self._video_error
        )

        path = RECORDINGS_FOLDER / (
            "video_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".mp4"
        )

        self.video_file_path = str(path)
        self.video_file_is_local = True

        self.video_recorder.setOutputLocation(
            QUrl.fromLocalFile(str(path))
        )

        self.video_player.stop()
        self.video_stack.setCurrentWidget(
            self.video_widget
        )
        self.video_camera.start()
        self.video_recorder.record()

        self.video_recording = True
        self.active_recording_mode = "video"
        self.elapsed_seconds = 0
        self.video_time.setText("00:00")
        self.video_status.setText("Recording")
        self.video_button.setText("Stop video")
        self.video_play_button.setEnabled(False)
        self.recording_timer.start(1000)
        self._lock_other_input("video")

    def _stop_video_recording(
        self,
        discard=False,
    ):
        if (
            not self.video_recording
            and self.video_recorder is None
        ):
            return

        self.recording_timer.stop()

        if self.video_recorder is not None:
            self.video_recorder.stop()

        if self.video_camera is not None:
            self.video_camera.stop()

        if self.video_capture_session is not None:
            self.video_capture_session.setVideoOutput(
                None
            )

        self.video_recording = False
        self.active_recording_mode = ""
        self.video_button.setText(
            "Record again"
        )

        if discard:
            path = self.video_file_path
            self.video_file_path = ""
            self.video_file_is_local = False
            self.video_status.setText(
                "Not recorded"
            )
            self.video_time.setText("00:00")
            self.video_stack.setCurrentIndex(0)
            self.video_play_button.setEnabled(False)

            if path:
                QTimer.singleShot(
                    300,
                    lambda: Path(path).unlink(
                        missing_ok=True
                    ),
                )
        else:
            self.video_status.setText(
                "Video recorded"
            )
            self.video_play_button.setEnabled(True)

            QTimer.singleShot(
                500,
                lambda: self._show_video_first_frame(
                    self.video_file_path
                ),
            )

            QTimer.singleShot(
                700,
                lambda: self._start_transcription(
                    self.video_file_path,
                    "video",
                ),
            )

        self.video_recorder = None
        self.video_camera = None
        self.video_audio_input = None
        self.video_capture_session = None

        self._lock_other_input(
            "video"
            if self.video_file_path
            else None
        )

    def toggle_audio_recording(self):
        if self.audio_button.property("locked"):
            return

        if self.audio_recording:
            self._stop_audio_recording()
        else:
            self._start_audio_recording()

    def _start_audio_recording(self):
        if not self.reset_recordings():
            return

        self.capture_status.hide()

        audio_device = (
            QMediaDevices.defaultAudioInput()
        )

        if audio_device.isNull():
            self.show_capture_status(
                "No microphone was found."
            )
            return

        requested_format = QAudioFormat()
        requested_format.setSampleRate(16000)
        requested_format.setChannelCount(1)
        requested_format.setSampleFormat(
            QAudioFormat.SampleFormat.Int16
        )

        if audio_device.isFormatSupported(
            requested_format
        ):
            self.audio_format = requested_format
        else:
            self.audio_format = (
                audio_device.preferredFormat()
            )

        self.audio_source = QAudioSource(
            audio_device,
            self.audio_format,
            self,
        )

        self.audio_device = (
            self.audio_source.start()
        )

        if self.audio_device is None:
            self.audio_source = None
            self.show_capture_status(
                "The microphone could not be started."
            )
            return

        self.audio_pcm = bytearray()

        self.audio_device.readyRead.connect(
            self._read_audio_data
        )

        self.audio_recording = True
        self.active_recording_mode = "audio"
        self.elapsed_seconds = 0
        self.audio_time.setText("00:00")
        self.audio_status.setText("Recording")
        self.audio_button.setText("Stop audio")
        self.audio_play_button.setEnabled(False)
        self.recording_timer.start(1000)
        self._lock_other_input("audio")

    def _read_audio_data(self):
        if (
            self.audio_device is None
            or self.audio_format is None
        ):
            return

        raw_data = bytes(
            self.audio_device.readAll()
        )

        if not raw_data:
            return

        samples = self._decode_audio(
            raw_data,
            self.audio_format,
        )

        if not samples:
            return

        rms = math.sqrt(
            sum(
                sample * sample
                for sample in samples
            )
            / len(samples)
        )

        self.waveform.add_level(
            min(1.0, rms * 4.5)
        )

        for sample in samples:
            value = int(
                max(
                    -1.0,
                    min(1.0, sample),
                )
                * 32767
            )

            self.audio_pcm.extend(
                struct.pack("<h", value)
            )

    def _decode_audio(
        self,
        raw_data,
        audio_format,
    ):
        sample_format = (
            audio_format.sampleFormat()
        )
        channels = max(
            1,
            audio_format.channelCount(),
        )
        endian = (
            "<"
            if sys.byteorder == "little"
            else ">"
        )

        if sample_format == (
            QAudioFormat.SampleFormat.Int16
        ):
            size, code, scale = (
                2,
                "h",
                32768.0,
            )
        elif sample_format == (
            QAudioFormat.SampleFormat.Int32
        ):
            size, code, scale = (
                4,
                "i",
                2147483648.0,
            )
        elif sample_format == (
            QAudioFormat.SampleFormat.Float
        ):
            size, code, scale = (
                4,
                "f",
                1.0,
            )
        elif sample_format == (
            QAudioFormat.SampleFormat.UInt8
        ):
            values = [
                (value - 128) / 128.0
                for value in raw_data
            ]

            return self._mix_to_mono(
                values,
                channels,
            )
        else:
            return []

        usable_length = (
            len(raw_data)
            - len(raw_data) % size
        )

        if usable_length <= 0:
            return []

        values = [
            item[0] / scale
            for item in struct.iter_unpack(
                endian + code,
                raw_data[:usable_length],
            )
        ]

        return self._mix_to_mono(
            values,
            channels,
        )

    def _mix_to_mono(
        self,
        values,
        channels,
    ):
        if channels == 1:
            return values

        mono_values = []

        usable_length = (
            len(values)
            - len(values) % channels
        )

        for index in range(
            0,
            usable_length,
            channels,
        ):
            mono_values.append(
                sum(
                    values[index:index + channels]
                )
                / channels
            )

        return mono_values

    def _stop_audio_recording(
        self,
        discard=False,
    ):
        if (
            not self.audio_recording
            and self.audio_source is None
        ):
            return

        self.recording_timer.stop()

        if self.audio_source is not None:
            self.audio_source.stop()

        self.audio_recording = False
        self.active_recording_mode = ""
        self.audio_button.setText(
            "Record again"
        )

        if discard or not self.audio_pcm:
            self.audio_file_path = ""
            self.audio_file_is_local = False
            self.audio_status.setText(
                "Not recorded"
            )
            self.audio_time.setText("00:00")
            self.waveform.clear()
            self.audio_play_button.setEnabled(False)
        else:
            path = RECORDINGS_FOLDER / (
                "audio_"
                + datetime.now().strftime(
                    "%Y%m%d_%H%M%S"
                )
                + ".wav"
            )

            sample_rate = (
                self.audio_format.sampleRate()
                if self.audio_format is not None
                else 16000
            )

            with wave.open(
                str(path),
                "wb",
            ) as audio_file:
                audio_file.setnchannels(1)
                audio_file.setsampwidth(2)
                audio_file.setframerate(
                    sample_rate
                )
                audio_file.writeframes(
                    bytes(self.audio_pcm)
                )

            self.audio_file_path = str(path)
            self.audio_file_is_local = True
            self.audio_status.setText(
                "Audio recorded"
            )
            self.audio_play_button.setEnabled(True)

            self._prepare_audio_waveform(
                self.audio_file_path
            )

            self._start_transcription(
                self.audio_file_path,
                "audio",
            )

        self.audio_device = None
        self.audio_source = None
        self.audio_format = None
        self.audio_pcm = bytearray()

        self._lock_other_input(
            "audio"
            if self.audio_file_path
            else None
        )

    def _update_recording_time(self):
        self.elapsed_seconds += 1

        time_text = (
            f"{self.elapsed_seconds // 60:02d}:"
            f"{self.elapsed_seconds % 60:02d}"
        )

        if self.active_recording_mode == "video":
            self.video_time.setText(time_text)
        elif self.active_recording_mode == "audio":
            self.audio_time.setText(time_text)

        if self.elapsed_seconds >= 60:
            if self.active_recording_mode == "video":
                self._stop_video_recording()
            elif self.active_recording_mode == "audio":
                self._stop_audio_recording()

    def _video_error(self, error, message):
        self.show_capture_status(
            message
            or "Video recording failed."
        )
        self._stop_video_recording(
            discard=True
        )
        self._lock_other_input(None)

    def toggle_video_playback(self):
        if not self.video_file_path:
            return

        if self.video_player.playbackState() == (
            QMediaPlayer.PlaybackState.PlayingState
        ):
            self.video_player.pause()
            return

        self.audio_player.stop()
        self.video_player.setVideoOutput(
            self.video_widget
        )
        self.video_player.setSource(
            QUrl.fromLocalFile(
                self.video_file_path
            )
        )
        self.video_stack.setCurrentWidget(
            self.video_widget
        )
        self.video_player.play()

    def _show_video_first_frame(self, path):
        if not path or not Path(path).exists():
            return

        self.video_player.stop()
        self.video_player.setVideoOutput(
            self.video_widget
        )
        self.video_player.setSource(
            QUrl.fromLocalFile(path)
        )
        self.video_stack.setCurrentWidget(
            self.video_widget
        )
        self.video_player.play()

        QTimer.singleShot(
            450,
            self.video_player.pause,
        )

    def _set_play_icon(self, button, playing):
        icon = self._pause_icon if playing else self._play_icon
        if icon.isNull():
            button.setText("\u275A\u275A" if playing else "\u25B6")
        else:
            button.setText("")
            button.setIcon(icon)

    def _update_video_play_button(
        self,
        state,
    ):
        playing = (
            state
            == QMediaPlayer.PlaybackState.PlayingState
        )
        self._set_play_icon(
            self.video_play_button,
            playing,
        )

    def _update_video_duration(self, duration_ms):
        if duration_ms <= 0:
            return

        total_seconds = duration_ms // 1000
        minutes, seconds = divmod(
            total_seconds,
            60,
        )

        self.video_time.setText(
            f"{minutes:02d}:{seconds:02d}"
        )

    def _update_audio_duration(self, duration_ms):
        if duration_ms <= 0:
            return

        total_seconds = duration_ms // 1000

        minutes, seconds = divmod(
            total_seconds,
            60,
        )

        self.audio_time.setText(
            f"{minutes:02d}:{seconds:02d}"
        )

    def toggle_audio_playback(self):
        if not self.audio_file_path:
            return

        if self.audio_player.playbackState() == (
            QMediaPlayer.PlaybackState.PlayingState
        ):
            self.audio_player.pause()
            return

        self.video_player.stop()
        self.audio_player.setSource(
            QUrl.fromLocalFile(
                self.audio_file_path
            )
        )
        self.audio_player.play()

    def _update_audio_play_button(
        self,
        state,
    ):
        playing = state == (
            QMediaPlayer.PlaybackState.PlayingState
        )

        self._set_play_icon(
            self.audio_play_button,
            playing,
        )

        if not playing:
            self.waveform.clear()

    def _prepare_audio_waveform(self, path):
        self.audio_playback_levels = []
        self.waveform.clear()

        try:
            waveform, sampling_rate = librosa.load(
                path,
                sr=16000,
                mono=True,
            )

            if waveform.size == 0:
                return

            duration_seconds = max(
                1.0,
                waveform.size / sampling_rate,
            )

            playback_count = max(
                40,
                int(duration_seconds * 20),
            )

            self.audio_playback_levels = (
                self._rms_levels(
                    waveform,
                    playback_count,
                )
            )

        except Exception:
            self.audio_playback_levels = []
            self.waveform.clear()

    def _rms_levels(
        self,
        waveform,
        count,
    ):
        count = max(1, int(count))

        segments = np.array_split(
            waveform,
            count,
        )

        levels = []

        for segment in segments:
            if segment.size == 0:
                levels.append(0.0)
                continue

            level = float(
                np.sqrt(
                    np.mean(
                        np.square(segment)
                    )
                )
            )

            levels.append(level)

        maximum = max(
            levels,
            default=0.0,
        )

        if maximum > 0:
            levels = [
                level / maximum
                for level in levels
            ]

        return levels

    def _sync_audio_waveform(self, position):
        if self.audio_player.playbackState() != (
            QMediaPlayer.PlaybackState.PlayingState
        ):
            return

        if not self.audio_playback_levels:
            return

        duration = max(
            1,
            self.audio_player.duration(),
        )

        progress = max(
            0.0,
            min(position / duration, 1.0),
        )

        index = min(
            len(self.audio_playback_levels) - 1,
            int(
                progress
                * len(self.audio_playback_levels)
            ),
        )

        self.waveform.add_level(
            self.audio_playback_levels[index]
        )

    def open_upload_dialog(self):
        if self._worker_running(
            self.transcription_worker
        ):
            self.show_capture_status(
                "Please wait for transcription to finish."
            )
            return

        dialog = UploadDialog(self)

        if dialog.exec() != (
            QDialog.DialogCode.Accepted
        ):
            return

        if not self.reset_recordings():
            return

        selected_path = dialog.selected_path

        if dialog.selected_type == "Audio":
            self.audio_file_path = selected_path
            self.audio_file_is_local = False
            self.audio_status.setText(
                "Uploaded: "
                + Path(selected_path).name
            )
            self.audio_button.setText(
                "Record instead"
            )
            self.audio_play_button.setEnabled(True)
            self._prepare_audio_waveform(
                selected_path
            )
            self._lock_other_input("audio")
            self._start_transcription(
                selected_path,
                "audio",
            )
        else:
            self.video_file_path = selected_path
            self.video_file_is_local = False
            self.video_status.setText(
                "Uploaded: "
                + Path(selected_path).name
            )
            self.video_button.setText(
                "Record instead"
            )
            self.video_play_button.setEnabled(True)
            self._show_video_first_frame(
                selected_path
            )
            self._lock_other_input("video")
            self._start_transcription(
                selected_path,
                "video",
            )

        self.capture_status.hide()

    def _start_transcription(
        self,
        recording_path,
        recording_type,
    ):
        if (
            not recording_path
            or not Path(recording_path).exists()
        ):
            return

        self.current_transcript = ""
        self.submit_button.setEnabled(False)
        self.transcript_input.clear()
        self.transcript_input.setReadOnly(True)
        self.transcript_input.setPlaceholderText(
            "Creating transcript..."
        )

        self.transcription_worker = (
            TranscriptionWorker(
                recording_path,
                recording_type,
                self,
            )
        )

        self.transcription_worker.progress.connect(
            self.transcript_input.setPlaceholderText
        )

        self.transcription_worker.completed.connect(
            self._transcription_completed
        )

        self.transcription_worker.failed.connect(
            self._transcription_failed
        )

        self.transcription_worker.start()

    def _transcription_completed(
        self,
        transcript,
    ):
        self.current_transcript = transcript
        self.transcript_input.setPlainText(
            transcript
        )
        self.transcript_input.setReadOnly(False)
        self.submit_button.setEnabled(True)
        self.transcription_worker = None

    def _transcription_failed(self, message):
        self.current_transcript = ""
        self.transcript_input.clear()
        self.transcript_input.setReadOnly(True)
        self.transcript_input.setPlaceholderText(
            "Transcript unavailable. Record or upload another file."
        )
        self.submit_button.setEnabled(False)
        self.show_capture_status(
            "Transcription failed: " + message
        )
        self.transcription_worker = None

    def submit_check_in(self):
        if (
            self.video_recording
            or self.audio_recording
        ):
            self.show_capture_status(
                "Stop the recording before submitting."
            )
            return

        if (
            not self.video_file_path
            and not self.audio_file_path
        ):
            self.show_capture_status(
                "Record or upload video or audio first."
            )
            return

        if self._worker_running(
            self.transcription_worker
        ):
            self.show_capture_status(
                "Please wait for the transcript to finish."
            )
            return

        transcript = (
            self.transcript_input
            .toPlainText()
            .strip()
        )

        if not transcript:
            self.show_capture_status(
                "A transcript is required before analysis."
            )
            return

        if self.user_id is None:
            self.show_capture_status(
                "No signed-in user was found."
            )
            return

        if self.video_file_path:
            recording_path = self.video_file_path
            recording_type = "video"
        else:
            recording_path = self.audio_file_path
            recording_type = "audio"

        self.video_player.stop()
        self.audio_player.stop()

        self.processing_message.setText(
            "Loading the selected AI models..."
        )

        self.flow_stack.setCurrentWidget(
            self.processing_page
        )

        self.spinner.start()

        self.analysis_worker = AnalysisWorker(
            recording_path,
            recording_type,
            transcript,
            self,
        )

        self.analysis_worker.progress.connect(
            self.processing_message.setText
        )

        self.analysis_worker.completed.connect(
            self._analysis_completed
        )

        self.analysis_worker.failed.connect(
            self._analysis_failed
        )

        self.analysis_worker.start()

    def _analysis_completed(self, result):
        self.spinner.stop()

        previous_scores = get_recent_scores(
            self.user_id,
            1,
        )

        previous_score = (
            previous_scores[-1]
            if previous_scores
            else None
        )

        score = int(
            round(result["wellbeing_score"])
        )

        phrase, explanation, image_name = (
            self._result_presentation(
                score,
                previous_score,
            )
        )

        result["phrase"] = phrase
        result["explanation"] = explanation
        result["image_name"] = image_name

        save_check_in(
            self.user_id,
            result,
        )

        self._populate_result(result)

        self.flow_stack.setCurrentWidget(
            self.result_page
        )

        self.analysis_worker = None

    def _analysis_failed(self, message):
        self.spinner.stop()
        self.flow_stack.setCurrentWidget(
            self.capture_page
        )
        self.show_capture_status(
            "Analysis failed: " + message
        )
        self.analysis_worker = None

    def _set_result_image(self, image_name):
        image_path = ICONS_FOLDER / image_name
        pixmap = QPixmap(str(image_path))

        self.result_emoji.setPixmap(
            pixmap.scaled(
                100,
                100,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )


    def _result_presentation(
        self,
        score,
        previous_score,
    ):
        if previous_score is None:
            if score >= 67:
                return (
                    "Today feels steady",
                    "Your first check-in shows a higher wellbeing range.",
                    "wellbeing_high.png",
                )

            if score >= 34:
                return (
                    "Today feels mixed",
                    "Your first check-in shows a moderate wellbeing range.",
                    "wellbeing_mid.png",
                )

            return (
                "Today needs more care",
                "Your first check-in shows a lower wellbeing range.",
                "wellbeing_low.png",
            )

        difference = score - previous_score

        if difference >= 5:
            return (
                "You're moving forward",
                "Your wellbeing score has improved compared with your previous check-in.",
                "wellbeing_high.png",
            )

        if difference <= -5:
            return (
                "Let's take a closer look",
                "Your wellbeing score is lower than your previous check-in.",
                "wellbeing_low.png",
            )

        return (
            "Today feels steady",
            "Your wellbeing score is close to your previous check-in.",
            "wellbeing_mid.png",
        )

    def _format_recommendation(self, text):
        lines = [
            line.strip()
            for line in (text or "").splitlines()
            if line.strip()
        ]
        return "".join(
            f"<div style='margin-bottom:9px;'>{line}</div>"
            for line in lines
        )

    def _complete_month_points(
        self,
        existing_points,
    ):
        today = date.today()

        days_in_month = calendar.monthrange(
            today.year,
            today.month,
        )[1]

        points_by_day = {}

        for item in existing_points:
            date_text = str(
                item.get("date", "")
            )[:10]

            try:
                item_date = datetime.strptime(
                    date_text,
                    "%Y-%m-%d",
                ).date()
            except ValueError:
                continue

            if (
                item_date.year == today.year
                and item_date.month == today.month
            ):
                points_by_day[item_date.day] = item

        complete_points = []

        for day_number in range(
            1,
            days_in_month + 1,
        ):
            item = points_by_day.get(
                day_number
            )

            if item is None:
                complete_points.append(
                    {
                        "day": day_number,
                        "date": (
                            f"{today.year:04d}-"
                            f"{today.month:02d}-"
                            f"{day_number:02d}"
                        ),
                        "score": 0.0,
                        "phrase": "No check-in",
                        "has_check_in": False,
                    }
                )
            else:
                complete_points.append(
                    {
                        "day": day_number,
                        "date": item["date"],
                        "score": float(
                            item["score"]
                        ),
                        "phrase": item.get(
                            "phrase",
                            "",
                        ),
                        "has_check_in": True,
                    }
                )

        return complete_points

    def _set_recommendations(self, recommendation_text):
        while self.recommendation_items_layout.count():
            item = self.recommendation_items_layout.takeAt(0)

            if item.widget() is not None:
                item.widget().deleteLater()

        lines = [
            line.strip()
            for line in recommendation_text.splitlines()
            if line.strip()
        ]

        for line in lines:
            cleaned_line = line

            if (
                len(cleaned_line) > 2
                and cleaned_line[0].isdigit()
                and cleaned_line[1] in ".)"
            ):
                cleaned_line = cleaned_line[2:].strip()

            recommendation = QLabel(
                cleaned_line
            )

            recommendation.setObjectName(
                "recommendationItem"
            )

            recommendation.setWordWrap(True)

            recommendation.setAlignment(
                Qt.AlignLeft | Qt.AlignVCenter
            )

            self.recommendation_items_layout.addWidget(
                recommendation
            )

        self.recommendation_items_layout.addStretch()

    def _populate_result(self, result):
        score = int(
            round(result["wellbeing_score"])
        )

        self._set_result_image(
            result["image_name"]
        )

        self.result_phrase.setText(
            result["phrase"]
        )

        self.result_explanation.setText(
            result["explanation"]
        )

        self.score_progress.setValue(score)
        self.score_progress.setFormat(
            f"{score} / 100"
        )

        if score >= 67:
            zone = "high"
        elif score >= 34:
            zone = "mid"
        else:
            zone = "low"

        self.score_progress.setProperty(
            "zone",
            zone,
        )

        self._refresh_style(
            self.score_progress
        )

        self._set_recommendations(
            result["recommendation"]
        )

        month_points = get_month_check_ins(
            self.user_id,
            31,
        )

        complete_month_points = (
            self._complete_month_points(
                month_points
            )
        )

        self.trend_requirement.hide()

        self.trend_graph.set_points(
            complete_month_points
        )

        self.trend_graph.show()

    def show_capture_status(self, message):
        self.capture_status.setText(message)
        self.capture_status.setProperty(
            "statusType",
            "error",
        )
        self._refresh_style(
            self.capture_status
        )
        self.capture_status.show()

    def reset_recordings(self):
        if self._worker_running(
            self.transcription_worker
        ):
            self.show_capture_status(
                "Please wait for transcription to finish."
            )
            return False

        video_path = self.video_file_path
        audio_path = self.audio_file_path
        video_local = self.video_file_is_local
        audio_local = self.audio_file_is_local

        self._stop_video_recording(
            discard=True
        )
        self._stop_audio_recording(
            discard=True
        )

        self.video_player.stop()
        self.audio_player.stop()

        if video_local:
            self._delete_local_recording(
                video_path
            )

        if audio_local:
            self._delete_local_recording(
                audio_path
            )

        self._clear_video_state()
        self._clear_audio_state()

        self.current_transcript = ""
        self.transcript_input.clear()
        self.transcript_input.setReadOnly(True)
        self.transcript_input.setPlaceholderText(
            "Your transcript will appear here."
        )

        self.submit_button.setEnabled(False)
        self.capture_status.hide()
        self._lock_other_input(None)

        return True

    def _delete_local_recording(self, path):
        if not path:
            return

        try:
            file_path = Path(path)

            if (
                file_path.resolve().parent
                == RECORDINGS_FOLDER.resolve()
            ):
                file_path.unlink(
                    missing_ok=True
                )
        except OSError:
            pass

    def _clear_video_state(self):
        self.video_file_path = ""
        self.video_file_is_local = False
        self.video_status.setText(
            "Not recorded"
        )
        self.video_time.setText("00:00")
        self.video_button.setText(
            "Start video"
        )
        self._set_play_icon(
            self.video_play_button,
            False,
        )
        self.video_play_button.setEnabled(False)
        self.video_stack.setCurrentIndex(0)

    def _clear_audio_state(self):
        self.audio_file_path = ""
        self.audio_file_is_local = False
        self.audio_status.setText(
            "Not recorded"
        )
        self.audio_time.setText("00:00")
        self.audio_button.setText(
            "Start audio"
        )
        self._set_play_icon(
            self.audio_play_button,
            False,
        )
        self.audio_play_button.setEnabled(False)
        self.audio_playback_levels = []
        self.waveform.clear()

    def set_user(
        self,
        full_name,
        user_id=None,
    ):
        first_name = (
            full_name.split()[0]
            if full_name
            else ""
        )

        self.user_label.setText(
            first_name
        )
        self.user_id = user_id

    def reset_page(self):
        if self._worker_running(
            self.analysis_worker
        ):
            return

        if self._worker_running(
            self.transcription_worker
        ):
            return

        self.spinner.stop()
        self.reset_recordings()
        self.flow_stack.setCurrentWidget(
            self.capture_page
        )

    def _finish_result(self):
        self.flow_stack.setCurrentWidget(
            self.capture_page
        )
        self.home_requested.emit()

    def closeEvent(self, event):
        self._stop_video_recording(
            discard=True
        )
        self._stop_audio_recording(
            discard=True
        )
        self.video_player.stop()
        self.audio_player.stop()
        super().closeEvent(event)

    def _lock_other_input(self, active):
        self._apply_lock(
            self.audio_button,
            active == "video",
        )
        self._apply_lock(
            self.video_button,
            active == "audio",
        )

    def _apply_lock(self, button, locked):
        button.setProperty(
            "locked",
            locked,
        )
        button.setCursor(
            Qt.ForbiddenCursor
            if locked
            else Qt.PointingHandCursor
        )
        self._refresh_style(button)

    def _worker_running(self, worker):
        return (
            worker is not None
            and worker.isRunning()
        )

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)