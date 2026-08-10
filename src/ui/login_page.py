import math
from pathlib import Path

from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from src.ui.translations import ENGLISH_TEXT, get_text


ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "src" / "images"


LOGIN_TEXT = {
    "brand_tagline": "WELLBEING, WITH CARE",
    "login_title": "Welcome back",
    "login_subtitle": "Sign in to your dashboard.",
    "username": "Username",
    "username_placeholder": "Enter your username",
    "password": "Password",
    "password_placeholder": "Enter your password",
    "login_button": "Log in",
    "new_here": "New here?",
    "create_account": "Create account",

    "login_empty": "Please enter your username and password.",
    "login_incorrect": "The username or password is incorrect.",
    "account_created_login": "Account created. You can log in now.",
}

ENGLISH_TEXT.update(LOGIN_TEXT)


class EcgMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.phase = 0
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(35)

    def animate(self):
        self.phase = (self.phase + 3) % max(1, self.width())
        self.update()

    def paintEvent(self, event):
        w, h = self.width(), self.height()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#05080B"))

        grid = QColor("#38BDF8")
        grid.setAlpha(20)
        painter.setPen(QPen(grid, 1))

        for x in range(0, w, 28):
            painter.drawLine(x, 0, x, h)

        for y in range(0, h, 28):
            painter.drawLine(0, y, w, y)

        middle = h / 2
        points = []

        for x in range(0, w + 3, 3):
            position = (x % 150) / 150
            value = 0

            if 0.28 < position < 0.32:
                value = -0.15
            elif 0.32 <= position < 0.36:
                value = 1
            elif 0.36 <= position < 0.41:
                value = -0.45
            elif 0.48 <= position < 0.60:
                value = 0.18 * math.sin((position - 0.48) / 0.12 * math.pi)

            points.append(QPointF(x, middle - value * h * 0.28))

        painter.setPen(QPen(QColor(255, 255, 255, 45), 2))
        painter.drawPolyline(QPolygonF(points))

        bright = [
            point for point in points
            if self.phase - 70 <= point.x() <= self.phase
        ]

        if len(bright) > 1:
            painter.setPen(QPen(QColor("#38BDF8"), 3))
            painter.drawPolyline(QPolygonF(bright))


class BrandPanel(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName("brandPanel")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.ecg = EcgMonitor(self)

        heart = QLabel()
        heart.setFixedSize(76, 76)
        heart.setAlignment(Qt.AlignCenter)
        heart.setPixmap(
            QPixmap(str(IMAGES / "heart.png")).scaled(
                64, 64,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        name = QLabel("Solace")
        name.setObjectName("brandName")
        name.setAlignment(Qt.AlignCenter)

        self.tagline = QLabel()
        self.tagline.setObjectName("brandTagline")
        self.tagline.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch()
        layout.addWidget(heart, 0, Qt.AlignCenter)
        layout.addWidget(name)
        layout.addWidget(self.tagline)
        layout.addStretch()

    def set_language(self, language):
        self.tagline.setText(get_text(language, "brand_tagline"))
        self.tagline.setStyleSheet(
            "font-size:9px;" if language == "Tamil" else ""
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.ecg.setGeometry(self.rect())
        self.ecg.lower()


class LoginPage(QWidget):
    language_changed = Signal(str)

    def __init__(self):
        super().__init__()

        self.current_language = "English"

        # Compact language selector available before login.
        self.language_combo = QComboBox()
        self.language_combo.setObjectName("loginLanguageCombo")
        self.language_combo.setFixedHeight(36)
        self.language_combo.setCursor(Qt.PointingHandCursor)
        self.language_combo.setToolTip("Language")
        self.language_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.language_combo.addItem("English", "English")
        self.language_combo.addItem("Malay", "Malay")
        self.language_combo.addItem("Chinese", "Chinese")
        self.language_combo.addItem("Tamil", "Tamil")
        self.language_combo.currentIndexChanged.connect(
            self.language_selected
        )

        card = QFrame()
        card.setObjectName("appCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setFixedSize(940, 560)

        self.brand = BrandPanel()
        form = self.build_form()

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)
        card_layout.addWidget(self.brand, 47)
        card_layout.addWidget(form, 53)

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(card)
        row.addStretch()

        language_row = QHBoxLayout()
        language_row.setContentsMargins(0, 0, 0, 0)
        language_row.addStretch()
        language_row.addWidget(self.language_combo)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 50, 60, 30)
        layout.addStretch()
        layout.addLayout(row)
        layout.addStretch()
        layout.addLayout(language_row)

        self.set_language("English")

    def build_form(self):
        panel = QFrame()
        panel.setObjectName("formPanel")
        panel.setAttribute(Qt.WA_StyledBackground, True)

        self.heading = QLabel()
        self.heading.setObjectName("formTitle")

        self.subtitle = QLabel()
        self.subtitle.setObjectName("formSubtitle")
        self.subtitle.setWordWrap(True)

        self.status_label = QLabel()
        self.status_label.setObjectName("statusMessage")
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(42)
        self.status_label.hide()

        self.username_label = QLabel()
        self.username_label.setObjectName("fieldLabel")

        self.username_input = QLineEdit()
        self.username_input.setFixedHeight(50)

        self.password_label = QLabel()
        self.password_label.setObjectName("fieldLabel")

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setFixedHeight(50)

        self.login_button = QPushButton()
        self.login_button.setObjectName("primaryButton")
        self.login_button.setFixedHeight(48)
        self.login_button.setCursor(Qt.PointingHandCursor)

        self.register_button = QPushButton()
        self.register_button.setObjectName("secondaryButton")
        self.register_button.setFixedHeight(48)
        self.register_button.setCursor(Qt.PointingHandCursor)

        self.password_input.returnPressed.connect(self.login_button.click)

        self.divider_label = QLabel()
        self.divider_label.setObjectName("dividerLabel")
        self.divider_label.setAlignment(Qt.AlignCenter)

        left_line = QFrame()
        left_line.setObjectName("dividerLine")
        left_line.setFixedHeight(1)

        right_line = QFrame()
        right_line.setObjectName("dividerLine")
        right_line.setFixedHeight(1)

        divider = QHBoxLayout()
        divider.addWidget(left_line, 1)
        divider.addWidget(self.divider_label)
        divider.addWidget(right_line, 1)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(56, 38, 56, 38)
        layout.addStretch()
        layout.addWidget(self.heading)
        layout.addSpacing(6)
        layout.addWidget(self.subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.status_label)
        layout.addSpacing(14)
        layout.addWidget(self.username_label)
        layout.addSpacing(5)
        layout.addWidget(self.username_input)
        layout.addSpacing(14)
        layout.addWidget(self.password_label)
        layout.addSpacing(5)
        layout.addWidget(self.password_input)
        layout.addSpacing(20)
        layout.addWidget(self.login_button)
        layout.addSpacing(16)
        layout.addLayout(divider)
        layout.addSpacing(16)
        layout.addWidget(self.register_button)
        layout.addStretch()

        return panel

    def language_selected(self):
        language = self.language_combo.currentData()

        if not language:
            return

        self.clear_status()
        self.set_language(language)
        self.language_changed.emit(language)

    def resize_language_combo(self):
        # Keep the selector pill compact while allowing longer language names.
        text_width = self.language_combo.fontMetrics().horizontalAdvance(
            self.language_combo.currentText()
        )
        self.language_combo.setFixedWidth(
            max(100, min(170, text_width + 50))
        )

    def t(self, key):
        return get_text(self.current_language, key)

    def set_language(self, language):
        self.current_language = language
        self.brand.set_language(language)

        self.heading.setText(self.t("login_title"))
        self.subtitle.setText(self.t("login_subtitle"))
        self.username_label.setText(self.t("username"))
        self.username_input.setPlaceholderText(self.t("username_placeholder"))
        self.password_label.setText(self.t("password"))
        self.password_input.setPlaceholderText(self.t("password_placeholder"))
        self.login_button.setText(self.t("login_button"))
        self.register_button.setText(self.t("create_account"))
        self.divider_label.setText(self.t("new_here"))

        index = self.language_combo.findData(language)
        if index >= 0:
            self.language_combo.blockSignals(True)
            self.language_combo.setCurrentIndex(index)
            self.language_combo.blockSignals(False)

        tamil = language == "Tamil"

        widgets = [
            (self.heading, 20),
            (self.subtitle, 10),
            (self.username_label, 10),
            (self.password_label, 10),
            (self.username_input, 10),
            (self.password_input, 10),
            (self.login_button, 10),
            (self.register_button, 10),
            (self.divider_label, 9),
            (self.language_combo, 10),
        ]

        for widget, size in widgets:
            widget.setStyleSheet(f"font-size:{size}px;" if tamil else "")

        self.resize_language_combo()

    def show_status(self, message, status_type):
        icon = "✓" if status_type == "success" else "!"
        self.status_label.setText(f"{icon}  {message}")
        self.status_label.setProperty("statusType", status_type)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.show()

    def clear_status(self):
        self.status_label.clear()
        self.status_label.hide()

    def clear_password(self):
        self.password_input.clear()