from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox, QFrame, QHBoxLayout, QLabel,
    QSizePolicy, QVBoxLayout, QWidget
)

from src.ui.home_page import HoverSidebar
from src.ui.translations import get_text

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "src" / "images"


class SettingsPage(QWidget):
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    logout_requested = Signal()
    language_changed = Signal(str)

    def __init__(self):
        super().__init__()

        self.current_language = "English"

        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.trends_requested.connect(self.trends_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)

        self.set_active_sidebar()

        content = self.build_content()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(content, 1)

        self.set_language("English")

    def set_active_sidebar(self):
        buttons = (
            self.sidebar.home_button,
            self.sidebar.check_in_button,
            self.sidebar.trends_button,
            self.sidebar.settings_button,
        )

        for button in buttons:
            button.setProperty("active", False)

        self.sidebar.settings_button.setProperty("active", True)

        for button in buttons:
            button.style().unpolish(button)
            button.style().polish(button)

    def build_content(self):
        content = QWidget()
        content.setObjectName("homeContent")
        content.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.title = QLabel()
        self.title.setObjectName("sectionTitle")

        self.subtitle = QLabel()
        self.subtitle.setObjectName("formSubtitle")
        self.subtitle.setWordWrap(True)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 26, 40, 30)
        layout.setSpacing(14)
        layout.addLayout(self.build_header())
        layout.addSpacing(10)
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addSpacing(8)
        layout.addWidget(self.build_language_card())
        layout.addStretch()

        return content

    def build_header(self):
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

        layout = QHBoxLayout()
        layout.setSpacing(7)
        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()

        return layout

    def build_language_card(self):
        card = QFrame()
        card.setObjectName("featureCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMaximumWidth(620)

        self.language_heading = QLabel()
        self.language_heading.setObjectName("featureTitle")

        self.language_description = QLabel()
        self.language_description.setObjectName("featureDescription")
        self.language_description.setWordWrap(True)

        self.language_label = QLabel()
        self.language_label.setObjectName("fieldLabel")

        self.language_combo = QComboBox()
        self.language_combo.setFixedHeight(44)
        self.language_combo.setCursor(Qt.PointingHandCursor)

        self.language_combo.addItem("English", "English")
        self.language_combo.addItem("Bahasa Melayu", "Malay")
        self.language_combo.addItem("简体中文", "Chinese")
        self.language_combo.addItem("தமிழ்", "Tamil")

        self.language_combo.currentIndexChanged.connect(
            self.language_selected
        )

        self.language_note = QLabel()
        self.language_note.setObjectName("privacyNote")
        self.language_note.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(10)
        layout.addWidget(self.language_heading)
        layout.addWidget(self.language_description)
        layout.addSpacing(6)
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)
        layout.addWidget(self.language_note)

        return card

    def language_selected(self):
        language = self.language_combo.currentData()
        self.set_language(language)
        self.language_changed.emit(language)

    def t(self, key):
        return get_text(self.current_language, key)

    def set_language(self, language):
        self.current_language = language
        self.sidebar.set_language(language)

        self.title.setText(self.t("settings_title"))
        self.subtitle.setText(self.t("settings_subtitle"))
        self.language_heading.setText(self.t("language"))
        self.language_description.setText(
            self.t("language_description")
        )
        self.language_label.setText(
            self.t("application_language")
        )
        self.language_note.setText(
            self.t("language_note")
        )

        index = self.language_combo.findData(language)

        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)

        self.tamil_fonts()

    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        sizes = [
            (self.title, 18),
            (self.subtitle, 10),
            (self.language_heading, 11),
            (self.language_description, 10),
            (self.language_label, 10),
            (self.language_combo, 10),
            (self.language_note, 9),
        ]

        for widget, size in sizes:
            widget.setStyleSheet(
                f"font-size:{size}px;" if tamil else ""
            )