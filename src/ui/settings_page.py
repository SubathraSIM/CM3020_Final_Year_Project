from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget
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
    privacy_requested = Signal()
    delete_account_requested = Signal()

    def __init__(self):
        super().__init__()
        self.current_language = "English"

        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.trends_requested.connect(self.trends_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)
        self.set_active_sidebar()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.build_content(), 1)

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
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.title = QLabel()
        self.title.setObjectName("settingsPageTitle")

        self.subtitle = QLabel()
        self.subtitle.setObjectName("settingsPageSubtitle")
        self.subtitle.setWordWrap(True)

        cards = QGridLayout()
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setHorizontalSpacing(20)
        cards.setVerticalSpacing(20)
        cards.addWidget(self.build_language_card(), 0, 0)
        cards.addWidget(self.build_privacy_card(), 0, 1)
        cards.addWidget(self.build_delete_account_card(), 1, 0, 1, 2)
        cards.setColumnStretch(0, 1)
        cards.setColumnStretch(1, 1)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(50, 28, 50, 36)
        layout.setSpacing(0)
        layout.addLayout(self.build_header())
        layout.addSpacing(24)
        layout.addWidget(self.title)
        layout.addSpacing(5)
        layout.addWidget(self.subtitle)
        layout.addSpacing(24)
        layout.addLayout(cards)
        layout.addStretch()

        return content

    def build_header(self):
        heart = QLabel()
        heart.setFixedSize(30, 30)
        heart.setAlignment(Qt.AlignCenter)
        heart.setPixmap(QPixmap(str(IMAGES / "heart.png")).scaled(
            28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))

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
        card.setObjectName("settingsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(220)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.language_heading = QLabel()
        self.language_heading.setObjectName("featureTitle")

        self.language_description = QLabel()
        self.language_description.setObjectName("featureDescription")
        self.language_description.setWordWrap(True)

        self.language_label = QLabel()
        self.language_label.setObjectName("fieldLabel")

        self.language_combo = QComboBox()
        self.language_combo.setFixedHeight(44)
        self.language_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.language_combo.setCursor(Qt.PointingHandCursor)
        self.language_combo.addItem("English", "English")
        self.language_combo.addItem("Bahasa Melayu", "Malay")
        self.language_combo.addItem("简体中文", "Chinese")
        self.language_combo.addItem("தமிழ்", "Tamil")
        self.language_combo.currentIndexChanged.connect(self.language_selected)

        self.language_note = QLabel()
        self.language_note.setObjectName("privacyNote")
        self.language_note.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(9)
        layout.addWidget(self.language_heading)
        layout.addWidget(self.language_description)
        layout.addStretch()
        layout.addWidget(self.language_label)
        layout.addWidget(self.language_combo)
        layout.addWidget(self.language_note)

        return card

    def build_privacy_card(self):
        card = QFrame()
        card.setObjectName("settingsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(220)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.privacy_heading = QLabel()
        self.privacy_heading.setObjectName("featureTitle")

        self.privacy_description = QLabel()
        self.privacy_description.setObjectName("featureDescription")
        self.privacy_description.setWordWrap(True)

        self.privacy_button = QPushButton()
        self.privacy_button.setObjectName("secondaryButton")
        self.privacy_button.setFixedHeight(44)
        self.privacy_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.privacy_button.setCursor(Qt.PointingHandCursor)
        self.privacy_button.clicked.connect(self.privacy_requested.emit)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 24, 26, 24)
        layout.setSpacing(9)
        layout.addWidget(self.privacy_heading)
        layout.addWidget(self.privacy_description)
        layout.addStretch()
        layout.addWidget(self.privacy_button)

        return card

    def build_delete_account_card(self):
        card = QFrame()
        card.setObjectName("dangerCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(155)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.delete_heading = QLabel()
        self.delete_heading.setObjectName("dangerTitle")

        self.delete_description = QLabel()
        self.delete_description.setObjectName("featureDescription")
        self.delete_description.setWordWrap(True)

        self.delete_button = QPushButton()
        self.delete_button.setObjectName("deleteAccountButton")
        self.delete_button.setFixedHeight(44)
        self.delete_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.clicked.connect(self.delete_account_requested.emit)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(8)
        layout.addWidget(self.delete_heading)
        layout.addWidget(self.delete_description)
        layout.addSpacing(6)
        layout.addWidget(self.delete_button)

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
        self.language_description.setText(self.t("language_description"))
        self.language_label.setText(self.t("application_language"))
        self.language_note.setText(self.t("language_note"))
        self.privacy_heading.setText(self.t("privacy_settings_title"))
        self.privacy_description.setText(self.t("privacy_settings_description"))
        self.privacy_button.setText(self.t("view_privacy"))
        self.delete_heading.setText(self.t("delete_account_title"))
        self.delete_description.setText(self.t("delete_account_description"))
        self.delete_button.setText(self.t("delete_account"))

        index = self.language_combo.findData(language)
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(index)
        self.language_combo.blockSignals(False)

        self.tamil_fonts()

    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"
        sizes = [
            (self.title, 18), (self.subtitle, 10),
            (self.language_heading, 11), (self.language_description, 10),
            (self.language_label, 10), (self.language_combo, 10),
            (self.language_note, 9), (self.privacy_heading, 11),
            (self.privacy_description, 10), (self.privacy_button, 10),
            (self.delete_heading, 11), (self.delete_description, 10),
            (self.delete_button, 10),
        ]

        for widget, size in sizes:
            widget.setStyleSheet(f"font-size:{size}px;" if tamil else "")


class DeleteAccountDialog(QDialog):
    def __init__(self, language="English", parent=None):
        super().__init__(parent)
        self.language = language

        self.setModal(True)
        self.setWindowTitle(get_text(language, "delete_dialog_title"))
        self.setFixedSize(580, 430)

        card = QFrame()
        card.setObjectName("deleteAccountDialogCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        title = QLabel(get_text(language, "delete_dialog_title"))
        title.setObjectName("deleteDialogTitle")

        warning = QLabel(get_text(language, "delete_dialog_warning"))
        warning.setObjectName("deleteDialogWarning")
        warning.setWordWrap(True)

        details = QLabel(get_text(language, "delete_dialog_details"))
        details.setObjectName("deleteDialogDetails")
        details.setWordWrap(True)

        self.confirm_checkbox = QCheckBox(get_text(language, "delete_dialog_confirm"))

        cancel = QPushButton(get_text(language, "cancel"))
        cancel.setObjectName("secondaryButton")
        cancel.setFixedHeight(44)
        cancel.setCursor(Qt.PointingHandCursor)
        cancel.clicked.connect(self.reject)

        self.delete_button = QPushButton(get_text(language, "delete_account_confirm"))
        self.delete_button.setObjectName("deleteAccountButton")
        self.delete_button.setFixedHeight(44)
        self.delete_button.setCursor(Qt.PointingHandCursor)
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.accept)

        self.confirm_checkbox.toggled.connect(self.delete_button.setEnabled)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.addWidget(cancel)
        buttons.addWidget(self.delete_button)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(warning)
        layout.addWidget(details)
        layout.addWidget(self.confirm_checkbox)
        layout.addStretch()
        layout.addLayout(buttons)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(card)