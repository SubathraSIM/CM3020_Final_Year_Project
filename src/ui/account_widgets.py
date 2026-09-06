"""Shared initials avatars and password visibility controls."""
import hashlib
import re
from pathlib import Path
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QPushButton, QLineEdit, QLabel, QToolButton
from src.ui.translations import ENGLISH_TEXT, get_text

ENGLISH_TEXT.update({'show_password':'Show password', 'hide_password':'Hide password', 'profile':'Profile'})
IMAGES = Path(__file__).resolve().parents[1] / 'images'

class AvatarButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('profileAvatar')
        self.setFixedSize(42,42)
        self.setCursor(Qt.PointingHandCursor)
        self.set_identity('')

    def set_identity(self, username):
        parts = re.findall(r'[^\W_]+', str(username), flags=re.UNICODE)
        initials = ''.join(p[0] for p in parts[:2]).upper() or '?'
        colors = ['#456AA3', '#756393', '#3F7E85', '#A56859', '#687A4D']
        index = int(hashlib.sha256(str(username).casefold().encode()).hexdigest()[:8],16) % len(colors)
        self.setText(initials)
        self.setToolTip(str(username) or 'Profile')
        self.setAccessibleName('Profile: ' + str(username))
        self.setStyleSheet(f'QPushButton {{background:{colors[index]};color:white;border:2px solid transparent;border-radius:21px;padding:0;font-size:14px;font-weight:600;}} QPushButton:hover {{border:2px solid #BACDED;}} QPushButton:focus {{border:2px solid transparent;}}')


def add_avatar(layout):
    # Keep legacy labels available to their existing setters but remove them visually.
    for i in range(layout.count()):
        widget=layout.itemAt(i).widget()
        if isinstance(widget,QLabel) and widget.objectName()=='welcomeLabel':
            widget.hide()
    avatar=AvatarButton()
    layout.addWidget(avatar)
    return avatar


class PasswordEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        self.setTextMargins(0, 0, 44, 0)

        self.eye = QToolButton(self)
        self.eye.setObjectName("passwordEyeButton")
        self.eye.setFixedSize(36, 36)
        self.eye.setIconSize(QSize(36, 36))
        self.eye.setCursor(Qt.PointingHandCursor)
        self.eye.setFocusPolicy(Qt.StrongFocus)

        self.eye.setStyleSheet("""
            QToolButton#passwordEyeButton {
                background: transparent;
                border: none;
                padding: 0;
                color: #456AA3;
            }
            QToolButton#passwordEyeButton:hover,
            QToolButton#passwordEyeButton:pressed,
            QToolButton#passwordEyeButton:focus {
                background: transparent;
                border: none;
            }
        """)

        self.eye.clicked.connect(self.toggle_visibility)
        self.textChanged.connect(self.reset_if_empty)
        self.refresh_eye()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.eye.move(
            self.width() - self.eye.width() - 7,
            (self.height() - self.eye.height()) // 2,
        )

    def refresh_eye(self):
        visible = self.echoMode() == QLineEdit.Normal
        language = getattr(self.window(), "current_language", "English")

        label = get_text(
            language,
            "hide_password" if visible else "show_password",
        )
        self.eye.setToolTip(label)
        self.eye.setAccessibleName(label)

        filename = "eye_off.png" if visible else "eye.png"
        icon = QIcon(str(IMAGES / filename))

        # Keep the control usable if an image cannot be loaded.
        if icon.isNull():
            self.eye.setIcon(QIcon())
            self.eye.setText("Hide" if visible else "Show")
        else:
            self.eye.setText("")
            self.eye.setIcon(icon)

    def toggle_visibility(self):
        visible = self.echoMode() == QLineEdit.Normal
        self.setEchoMode(
            QLineEdit.Password if visible else QLineEdit.Normal
        )
        self.refresh_eye()
        self.setFocus()

    def reset_if_empty(self, text):
        if not text:
            self.setEchoMode(QLineEdit.Password)
            self.refresh_eye()