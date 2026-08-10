from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QVBoxLayout,
)

from src.ui.translations import ENGLISH_TEXT, get_text


ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "src" / "images"


CONSENT_TEXT = {
    "consent_window": "Disclaimer and consent",
    "consent_title": "Before you continue",
    "consent_subtitle": "Please read this information before using Solace.",

    "disclaimer_main":
        "Solace is a wellbeing support tool, not a medical diagnostic service.",

    "disclaimer_ai":
        "During a check-in, Solace may analyse text, voice and facial-expression "
        "signals together with supporting signals such as blink rate, head position, "
        "speech rate, disfluency and lexical variety. AI results may be inaccurate "
        "and should not replace advice from a qualified healthcare professional.",

    "disclaimer_privacy":
        "Your account and saved check-in history are stored locally on this device. "
        "You choose whether to use audio or video for each check-in.",

    "disclaimer_emergency":
        "Solace is not an emergency service. Seek immediate professional or emergency "
        "support if you or another person may be in danger.",

    "consent_checkbox":
        "I have read and understood the information above, and I consent to continue.",

    "consent_agree": "I agree and continue",
    "consent_decline": "I do not agree",

    "thank_you_title": "Thank you for visiting",
    "thank_you_message":
        "You need to accept the disclaimer before using Solace.",
}

ENGLISH_TEXT.update(CONSENT_TEXT)


def heart_image(size):
    heart = QLabel()
    heart.setFixedSize(size, size)
    heart.setAlignment(Qt.AlignCenter)
    heart.setPixmap(
        QPixmap(str(IMAGES / "heart.png")).scaled(
            size - 8,
            size - 8,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )
    )
    return heart


class ConsentDialog(QDialog):
    def __init__(self, parent=None, initial_language="English"):
        super().__init__(parent)

        self.selected_language = initial_language

        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(680, 560)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.build_language_page())
        self.stack.addWidget(self.build_consent_page())

        index = self.language_combo.findData(initial_language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.addWidget(self.stack)

    def build_language_page(self):
        card = QFrame()
        card.setObjectName("consentCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        title = QLabel("Choose your language")
        title.setObjectName("consentTitle")
        title.setAlignment(Qt.AlignCenter)

        note = QLabel("Choose the language you want to use throughout Solace.")
        note.setObjectName("consentSubtitle")
        note.setAlignment(Qt.AlignCenter)
        note.setWordWrap(True)

        later = QLabel("You can change this later in Settings.")
        later.setObjectName("privacyNote")
        later.setAlignment(Qt.AlignCenter)

        self.language_combo = QComboBox()
        self.language_combo.setFixedHeight(48)
        self.language_combo.setCursor(Qt.PointingHandCursor)
        self.language_combo.addItem("English", "English")
        self.language_combo.addItem("Bahasa Melayu", "Malay")
        self.language_combo.addItem("简体中文", "Chinese")
        self.language_combo.addItem("தமிழ்", "Tamil")

        next_button = QPushButton("Next")
        next_button.setObjectName("primaryButton")
        next_button.setFixedHeight(48)
        next_button.setCursor(Qt.PointingHandCursor)
        next_button.clicked.connect(self.show_consent)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(70, 55, 70, 55)
        layout.setSpacing(16)
        layout.addStretch()
        layout.addWidget(heart_image(64), 0, Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addSpacing(8)
        layout.addWidget(self.language_combo)
        layout.addWidget(later)
        layout.addSpacing(4)
        layout.addWidget(next_button)
        layout.addStretch()

        return card

    def build_consent_page(self):
        card = QFrame()
        card.setObjectName("consentCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        self.title = QLabel()
        self.title.setObjectName("consentTitle")
        self.title.setAlignment(Qt.AlignCenter)

        self.subtitle = QLabel()
        self.subtitle.setObjectName("consentSubtitle")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setWordWrap(True)

        self.disclaimer = QLabel()
        self.disclaimer.setObjectName("disclaimerText")
        self.disclaimer.setWordWrap(True)
        self.disclaimer.setTextFormat(Qt.RichText)

        self.checkbox = QCheckBox()
        self.checkbox.setObjectName("consentCheckBox")
        self.checkbox.setCursor(Qt.PointingHandCursor)

        self.decline = QPushButton()
        self.decline.setObjectName("secondaryButton")
        self.decline.setFixedHeight(48)
        self.decline.setCursor(Qt.PointingHandCursor)
        self.decline.clicked.connect(self.reject)

        self.agree = QPushButton()
        self.agree.setObjectName("primaryButton")
        self.agree.setFixedHeight(48)
        self.agree.setCursor(Qt.PointingHandCursor)
        self.agree.setEnabled(False)
        self.agree.clicked.connect(self.accept)

        self.checkbox.toggled.connect(self.agree.setEnabled)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addWidget(self.decline)
        buttons.addWidget(self.agree)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(46, 28, 46, 28)
        layout.setSpacing(10)
        layout.addWidget(heart_image(52), 0, Qt.AlignCenter)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addWidget(self.disclaimer)
        layout.addWidget(self.checkbox)
        layout.addSpacing(4)
        layout.addLayout(buttons)

        return card

    def t(self, key):
        return get_text(self.selected_language, key)

    def show_consent(self):
        self.selected_language = self.language_combo.currentData()

        self.setWindowTitle(self.t("consent_window"))
        self.title.setText(self.t("consent_title"))
        self.subtitle.setText(self.t("consent_subtitle"))
        self.checkbox.setText(self.t("consent_checkbox"))
        self.agree.setText(self.t("consent_agree"))
        self.decline.setText(self.t("consent_decline"))

        self.disclaimer.setText(
            f"<p><b>{self.t('disclaimer_main')}</b></p>"
            f"<p>{self.t('disclaimer_ai')}</p>"
            f"<p>{self.t('disclaimer_privacy')}</p>"
            f"<p>{self.t('disclaimer_emergency')}</p>"
        )

        self.tamil_fonts()
        self.stack.setCurrentIndex(1)

    def tamil_fonts(self):
        tamil = self.selected_language == "Tamil"

        widgets = [
            (self.title, 17),
            (self.subtitle, 9),
            (self.disclaimer, 9),
            (self.checkbox, 9),
            (self.agree, 9),
            (self.decline, 9),
        ]

        for widget, size in widgets:
            widget.setStyleSheet(f"font-size:{size}px;" if tamil else "")


class ThankYouDialog(QDialog):
    def __init__(self, language="English", parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(420, 220)

        card = QFrame()
        card.setObjectName("thankYouCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        title = QLabel(get_text(language, "thank_you_title"))
        title.setObjectName("thankYouTitle")
        title.setAlignment(Qt.AlignCenter)

        message = QLabel(get_text(language, "thank_you_message"))
        message.setObjectName("thankYouText")
        message.setAlignment(Qt.AlignCenter)
        message.setWordWrap(True)

        if language == "Tamil":
            title.setStyleSheet("font-size:15px;")
            message.setStyleSheet("font-size:9px;")

        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 24, 34, 24)
        layout.setSpacing(8)
        layout.addWidget(heart_image(48), 0, Qt.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(message)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(card)

        QTimer.singleShot(1700, self.accept)