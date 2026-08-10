import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QWidget,
)

from src.ui.login_page import BrandPanel
from src.ui.translations import ENGLISH_TEXT, get_text


REGISTER_TEXT = {
    "register_title": "Create your account",
    "register_subtitle": "Start your private wellbeing journey.",
    "full_name": "Full name",
    "full_name_placeholder": "Enter your full name",
    "username": "Username",
    "choose_username": "Choose a username",
    "password": "Password",
    "create_password": "Create a password",
    "confirm_password": "Confirm password",
    "confirm_password_placeholder": "Enter your password again",

    "password_rule":
        "Use at least 8 characters with uppercase, lowercase, number and symbol.",

    "create_account": "Create account",
    "back_login": "Back to login",

    "register_empty": "Please complete all fields.",

    "password_weak":
        "Password must contain at least 8 characters, uppercase, lowercase, number and symbol.",

    "password_mismatch": "The passwords do not match.",
    "username_exists": "This username is already registered.",
    "account_created": "Account created successfully.",
}

ENGLISH_TEXT.update(REGISTER_TEXT)


class RegisterPage(QWidget):
    def __init__(self):
        super().__init__()

        self.current_language = "English"

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

        layout = QVBoxLayout(self)
        layout.setContentsMargins(60, 50, 60, 60)
        layout.addStretch()
        layout.addLayout(row)
        layout.addStretch()

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
        self.status_label.setMinimumHeight(38)
        self.status_label.hide()

        self.name_label = self.field_label()
        self.name_input = self.field()

        self.username_label = self.field_label()
        self.username_input = self.field()

        self.password_label = self.field_label()
        self.password_input = self.field(True)

        self.password_rule = QLabel()
        self.password_rule.setObjectName("privacyNote")
        self.password_rule.setWordWrap(True)

        self.confirm_label = self.field_label()
        self.confirm_password_input = self.field(True)

        self.create_button = QPushButton()
        self.create_button.setObjectName("primaryButton")
        self.create_button.setFixedHeight(44)
        self.create_button.setCursor(Qt.PointingHandCursor)

        self.back_button = QPushButton()
        self.back_button.setObjectName("secondaryButton")
        self.back_button.setFixedHeight(44)
        self.back_button.setCursor(Qt.PointingHandCursor)

        self.confirm_password_input.returnPressed.connect(
            self.create_button.click
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(56, 20, 56, 20)
        layout.setSpacing(0)

        layout.addWidget(self.heading)
        layout.addSpacing(3)
        layout.addWidget(self.subtitle)
        layout.addSpacing(5)
        layout.addWidget(self.status_label)
        layout.addSpacing(6)

        for field_label, field in (
            (self.name_label, self.name_input),
            (self.username_label, self.username_input),
            (self.password_label, self.password_input),
        ):
            layout.addWidget(field_label)
            layout.addSpacing(2)
            layout.addWidget(field)

            if field is self.password_input:
                layout.addSpacing(3)
                layout.addWidget(self.password_rule)

            layout.addSpacing(5)

        layout.addWidget(self.confirm_label)
        layout.addSpacing(2)
        layout.addWidget(self.confirm_password_input)
        layout.addSpacing(10)
        layout.addWidget(self.create_button)
        layout.addSpacing(6)
        layout.addWidget(self.back_button)

        return panel

    @staticmethod
    def field_label():
        widget = QLabel()
        widget.setObjectName("fieldLabel")
        return widget

    @staticmethod
    def field(password=False):
        widget = QLineEdit()
        widget.setFixedHeight(44)

        if password:
            widget.setEchoMode(QLineEdit.Password)

        return widget

    def t(self, key):
        return get_text(self.current_language, key)

    def set_language(self, language):
        self.current_language = language
        self.brand.set_language(language)

        self.heading.setText(self.t("register_title"))
        self.subtitle.setText(self.t("register_subtitle"))

        self.name_label.setText(self.t("full_name"))
        self.name_input.setPlaceholderText(self.t("full_name_placeholder"))

        self.username_label.setText(self.t("username"))
        self.username_input.setPlaceholderText(self.t("choose_username"))

        self.password_label.setText(self.t("password"))
        self.password_input.setPlaceholderText(self.t("create_password"))
        self.password_rule.setText(self.t("password_rule"))

        self.confirm_label.setText(self.t("confirm_password"))
        self.confirm_password_input.setPlaceholderText(
            self.t("confirm_password_placeholder")
        )

        self.create_button.setText(self.t("create_account"))
        self.back_button.setText(self.t("back_login"))

        self.tamil_fonts()

    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        widgets = [
            (self.heading, 20),
            (self.subtitle, 10),
            (self.name_label, 10),
            (self.username_label, 10),
            (self.password_label, 10),
            (self.confirm_label, 10),
            (self.name_input, 10),
            (self.username_input, 10),
            (self.password_input, 10),
            (self.confirm_password_input, 10),
            (self.password_rule, 9),
            (self.create_button, 10),
            (self.back_button, 10),
        ]

        for widget, size in widgets:
            widget.setStyleSheet(f"font-size:{size}px;" if tamil else "")

    @staticmethod
    def valid_password(password):
        return bool(
            len(password) >= 8
            and re.search(r"[A-Z]", password)
            and re.search(r"[a-z]", password)
            and re.search(r"\d", password)
            and re.search(r"[^A-Za-z0-9]", password)
        )

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

    def clear_fields(self):
        self.name_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()