from PySide6.QtCore import (
    QTimer,
    Qt
)

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout
)

from PySide6.QtGui import QColor


class ConsentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle(
            "Disclaimer and consent"
        )

        self.setModal(True)

        self.setWindowFlags(
            Qt.Dialog
            | Qt.FramelessWindowHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True
        )

        self.setFixedSize(
            680,
            560
        )

        card = QFrame()
        card.setObjectName("consentCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        shadow = QGraphicsDropShadowEffect(
            card
        )

        shadow.setBlurRadius(38)
        shadow.setOffset(0, 10)
        shadow.setColor(
            QColor(
                15,
                23,
                42,
                90
            )
        )

        card.setGraphicsEffect(shadow)

        icon = QLabel("♥")
        icon.setObjectName("consentHeart")
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel(
            "Before you continue"
        )

        title.setObjectName(
            "consentTitle"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        subtitle = QLabel(
            "Please read this disclaimer and provide your consent."
        )

        subtitle.setObjectName(
            "consentSubtitle"
        )

        subtitle.setAlignment(
            Qt.AlignCenter
        )

        subtitle.setWordWrap(True)

        disclaimer = QLabel(
            """
            <p><b>Solace is a wellbeing support tool, not a medical diagnostic service.</b></p>
            <p>The application may analyse text, voice and facial-expression signals during a check-in. These AI results may be inaccurate and should not replace advice from a qualified healthcare professional.</p>
            <p>Your account and check-in history are stored locally on this device. You remain in control of whether audio or video is used during a check-in.</p>
            <p>Solace is not an emergency service. Seek immediate professional or emergency support when you or another person may be in danger.</p>
            """
        )

        disclaimer.setObjectName(
            "disclaimerText"
        )

        disclaimer.setWordWrap(True)

        self.consent_checkbox = QCheckBox(
            "I have read and understood the disclaimer, and I consent to continue."
        )

        self.consent_checkbox.setObjectName(
            "consentCheckBox"
        )

        self.consent_checkbox.setCursor(
            Qt.PointingHandCursor
        )

        self.agree_button = QPushButton(
            "I agree and continue"
        )

        self.agree_button.setObjectName(
            "primaryButton"
        )

        self.agree_button.setCursor(
            Qt.PointingHandCursor
        )

        self.agree_button.setFixedHeight(
            48
        )

        self.agree_button.setEnabled(
            False
        )

        self.decline_button = QPushButton(
            "I do not agree"
        )

        self.decline_button.setObjectName(
            "secondaryButton"
        )

        self.decline_button.setCursor(
            Qt.PointingHandCursor
        )

        self.decline_button.setFixedHeight(
            48
        )

        self.consent_checkbox.toggled.connect(
            self.agree_button.setEnabled
        )

        self.agree_button.clicked.connect(
            self.accept
        )

        self.decline_button.clicked.connect(
            self.reject
        )

        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addWidget(
            self.decline_button
        )
        button_layout.addWidget(
            self.agree_button
        )

        card_layout = QVBoxLayout(card)

        card_layout.setContentsMargins(
            46,
            34,
            46,
            34
        )

        card_layout.setSpacing(12)

        card_layout.addWidget(icon)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(5)
        card_layout.addWidget(disclaimer)
        card_layout.addSpacing(5)
        card_layout.addWidget(
            self.consent_checkbox
        )

        card_layout.addSpacing(8)
        card_layout.addLayout(
            button_layout
        )

        outer_layout = QVBoxLayout(self)

        outer_layout.setContentsMargins(
            18,
            18,
            18,
            18
        )

        outer_layout.addWidget(card)


class ThankYouDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)

        self.setWindowFlags(
            Qt.Dialog
            | Qt.FramelessWindowHint
        )

        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True
        )

        self.setFixedSize(
            420,
            220
        )

        card = QFrame()
        card.setObjectName("thankYouCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        shadow = QGraphicsDropShadowEffect(
            card
        )

        shadow.setBlurRadius(32)
        shadow.setOffset(0, 8)
        shadow.setColor(
            QColor(
                15,
                23,
                42,
                80
            )
        )

        card.setGraphicsEffect(shadow)

        icon = QLabel("♥")
        icon.setObjectName("thankYouHeart")
        icon.setAlignment(Qt.AlignCenter)

        title = QLabel(
            "Thank you for visiting"
        )

        title.setObjectName(
            "thankYouTitle"
        )

        title.setAlignment(
            Qt.AlignCenter
        )

        message = QLabel(
            "You need to accept the disclaimer before using Solace."
        )

        message.setObjectName(
            "thankYouText"
        )

        message.setAlignment(
            Qt.AlignCenter
        )

        message.setWordWrap(True)

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            34,
            26,
            34,
            26
        )

        layout.setSpacing(8)
        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(message)

        outer_layout = QVBoxLayout(self)

        outer_layout.setContentsMargins(
            16,
            16,
            16,
            16
        )

        outer_layout.addWidget(card)

        QTimer.singleShot(
            1700,
            self.accept
        )
