from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget
)

from src.ui.login_page import BrandPanel


class RegisterPage(QWidget):
    def __init__(self):
        super().__init__()

        app_card = self._build_card()

        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(app_card)
        row.addStretch()

        page_layout = QVBoxLayout(self)

        page_layout.setContentsMargins(
            60,
            50,
            60,
            60
        )

        page_layout.addStretch()
        page_layout.addLayout(row)
        page_layout.addStretch()

    def _build_card(self):
        app_card = QFrame()

        app_card.setObjectName(
            "appCard"
        )

        app_card.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        app_card.setFixedSize(
            940,
            560
        )

        card_layout = QHBoxLayout(
            app_card
        )

        card_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        card_layout.setSpacing(0)

        card_layout.addWidget(
            BrandPanel(),
            47
        )

        card_layout.addWidget(
            self._build_form_panel(),
            53
        )

        return app_card

    def _build_form_panel(self):
        panel = QFrame()

        panel.setObjectName(
            "formPanel"
        )

        panel.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        heading = QLabel(
            "Create your account"
        )

        heading.setObjectName(
            "formTitle"
        )

        subtitle = QLabel(
            "Start your private wellbeing journey."
        )

        subtitle.setObjectName(
            "formSubtitle"
        )

        self.status_label = QLabel()

        self.status_label.setObjectName(
            "statusMessage"
        )

        self.status_label.setWordWrap(
            True
        )

        self.status_label.setMinimumHeight(
            40
        )

        self.status_label.hide()

        name_label = self._field_label(
            "Full name"
        )

        self.name_input = self._input(
            "Enter your full name"
        )

        username_label = self._field_label(
            "Username"
        )

        self.username_input = self._input(
            "Choose a username"
        )

        password_label = self._field_label(
            "Password"
        )

        self.password_input = self._input(
            "Create a password",
            password=True
        )

        confirm_label = self._field_label(
            "Confirm password"
        )

        self.confirm_password_input = self._input(
            "Enter your password again",
            password=True
        )

        self.create_button = QPushButton(
            "Create account"
        )

        self.create_button.setObjectName(
            "primaryButton"
        )

        self.create_button.setCursor(
            Qt.PointingHandCursor
        )

        self.create_button.setFixedHeight(
            44
        )

        self.back_button = QPushButton(
            "Back to login"
        )

        self.back_button.setObjectName(
            "secondaryButton"
        )

        self.back_button.setCursor(
            Qt.PointingHandCursor
        )

        self.back_button.setFixedHeight(
            44
        )

        self.confirm_password_input.returnPressed.connect(
            self.create_button.click
        )

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            56,
            20,
            56,
            20
        )

        layout.setSpacing(0)

        layout.addWidget(heading)
        layout.addSpacing(3)
        layout.addWidget(subtitle)
        layout.addSpacing(5)

        layout.addWidget(
            self.status_label
        )

        layout.addSpacing(8)

        layout.addWidget(name_label)
        layout.addSpacing(2)
        layout.addWidget(
            self.name_input
        )

        layout.addSpacing(5)
        layout.addWidget(username_label)
        layout.addSpacing(2)
        layout.addWidget(
            self.username_input
        )

        layout.addSpacing(5)
        layout.addWidget(password_label)
        layout.addSpacing(2)
        layout.addWidget(
            self.password_input
        )

        layout.addSpacing(5)
        layout.addWidget(confirm_label)
        layout.addSpacing(2)
        layout.addWidget(
            self.confirm_password_input
        )

        layout.addSpacing(10)
        layout.addWidget(
            self.create_button
        )

        layout.addSpacing(6)
        layout.addWidget(
            self.back_button
        )

        return panel

    def _field_label(self, text):
        label = QLabel(text)

        label.setObjectName(
            "fieldLabel"
        )

        return label

    def _input(
        self,
        placeholder,
        password=False
    ):
        field = QLineEdit()

        field.setPlaceholderText(
            placeholder
        )

        field.setFixedHeight(44)

        if password:
            field.setEchoMode(
                QLineEdit.Password
            )

        return field

    def show_status(
        self,
        message,
        status_type
    ):
        icon = (
            "✓"
            if status_type == "success"
            else "!"
        )

        self.status_label.setText(
            f"{icon}  {message}"
        )

        self.status_label.setProperty(
            "statusType",
            status_type
        )

        self.status_label.style().unpolish(
            self.status_label
        )

        self.status_label.style().polish(
            self.status_label
        )

        self.status_label.show()

    def clear_status(self):
        self.status_label.clear()
        self.status_label.hide()

    def clear_fields(self):
        self.name_input.clear()
        self.username_input.clear()
        self.password_input.clear()
        self.confirm_password_input.clear()
