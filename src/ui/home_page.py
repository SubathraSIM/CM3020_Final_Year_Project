from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    Qt,
    Signal
)

from PySide6.QtGui import QColor

from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget
)


class HoverSidebar(QFrame):
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    COLLAPSED_WIDTH = 76
    EXPANDED_WIDTH = 220

    def __init__(self):
        super().__init__()

        self.setObjectName("sideBar")

        self.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        self.setMinimumWidth(
            self.COLLAPSED_WIDTH
        )

        self.setMaximumWidth(
            self.COLLAPSED_WIDTH
        )

        self._expanded = False
        self._buttons = []

        self.brand = QLabel("♥")
        self.brand.setObjectName("sideBrand")
        self.brand.setAlignment(Qt.AlignCenter)
        self.brand.setFixedHeight(68)

        self.home_button = self._create_button(
            "⌂",
            "Home",
            active=True
        )

        self.check_in_button = self._create_button(
            "▶",
            "Check-in"
        )

        self.trends_button = self._create_button(
            "📈",
            "Trends"
        )

        self.settings_button = self._create_button(
            "⚙",
            "Settings"
        )

        self.logout_button = self._create_button(
            "↩",
            "Log out"
        )

        self.home_button.clicked.connect(
            self.home_requested.emit
        )

        self.check_in_button.clicked.connect(
            self.check_in_requested.emit
        )

        self.trends_button.clicked.connect(
            self.trends_requested.emit
        )

        self.settings_button.clicked.connect(
            self.settings_requested.emit
        )

        self.logout_button.clicked.connect(
            self.logout_requested.emit
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            10,
            12,
            10,
            12
        )

        layout.setSpacing(8)

        layout.addWidget(self.brand)
        layout.addSpacing(14)

        layout.addWidget(
            self.home_button
        )

        layout.addWidget(
            self.check_in_button
        )

        layout.addWidget(
            self.trends_button
        )

        layout.addStretch()

        layout.addWidget(
            self.settings_button
        )

        layout.addWidget(
            self.logout_button
        )

        self.minimum_animation = QPropertyAnimation(
            self,
            b"minimumWidth"
        )

        self.maximum_animation = QPropertyAnimation(
            self,
            b"maximumWidth"
        )

        for animation in (
            self.minimum_animation,
            self.maximum_animation
        ):
            animation.setDuration(180)

            animation.setEasingCurve(
                QEasingCurve.OutCubic
            )

        self.animation_group = QParallelAnimationGroup(
            self
        )

        self.animation_group.addAnimation(
            self.minimum_animation
        )

        self.animation_group.addAnimation(
            self.maximum_animation
        )

    def _create_button(
        self,
        symbol,
        label,
        active=False
    ):
        button = QPushButton(symbol)

        button.setObjectName(
            "navButton"
        )

        button.setFixedHeight(50)

        button.setCursor(
            Qt.PointingHandCursor
        )

        button.setToolTip(label)

        button.setProperty(
            "active",
            active
        )

        button.setProperty(
            "expanded",
            False
        )

        self._buttons.append(
            (
                button,
                symbol,
                label
            )
        )

        return button

    def enterEvent(self, event):
        self._change_width(True)

        super().enterEvent(event)

    def leaveEvent(self, event):
        self._change_width(False)

        super().leaveEvent(event)

    def _change_width(
        self,
        expanded
    ):
        if self._expanded == expanded:
            return

        self._expanded = expanded

        start_width = self.width()

        if expanded:
            end_width = self.EXPANDED_WIDTH
            self.brand.setText("♥   Solace")
        else:
            end_width = self.COLLAPSED_WIDTH
            self.brand.setText("♥")

        for button, symbol, label in self._buttons:
            if expanded:
                button.setText(
                    f"{symbol}    {label}"
                )
            else:
                button.setText(symbol)

            button.setProperty(
                "expanded",
                expanded
            )

            button.style().unpolish(
                button
            )

            button.style().polish(
                button
            )

        self.animation_group.stop()

        self.minimum_animation.setStartValue(
            start_width
        )

        self.minimum_animation.setEndValue(
            end_width
        )

        self.maximum_animation.setStartValue(
            start_width
        )

        self.maximum_animation.setEndValue(
            end_width
        )

        self.animation_group.start()


class HomePage(QWidget):
    logout_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    settings_requested = Signal()
    help_requested = Signal()

    def __init__(self):
        super().__init__()

        self.sidebar = HoverSidebar()

        self.sidebar.logout_requested.connect(
            self.logout_requested.emit
        )

        self.sidebar.check_in_requested.connect(
            self.check_in_requested.emit
        )

        self.sidebar.trends_requested.connect(
            self.trends_requested.emit
        )

        self.sidebar.settings_requested.connect(
            self.settings_requested.emit
        )

        content = self._build_content()

        root_layout = QHBoxLayout(self)

        root_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        root_layout.setSpacing(0)

        root_layout.addWidget(
            self.sidebar
        )

        root_layout.addWidget(
            content,
            1
        )

    def _build_content(self):
        content = QWidget()

        content.setObjectName(
            "homeContent"
        )

        content.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        header = self._build_header()
        hero_card = self._build_hero_card()

        section_title = QLabel("Explore")

        section_title.setObjectName(
            "sectionTitle"
        )

        features_layout = QHBoxLayout()

        features_layout.setSpacing(16)

        features_layout.addWidget(
            self._feature_card(
                "✦",
                "Check-in",
                "Use text, voice or optional video."
            ),
            1
        )

        features_layout.addWidget(
            self._feature_card(
                "📈",
                "Trends",
                "View changes in your wellbeing."
            ),
            1
        )

        features_layout.addWidget(
            self._feature_card(
                "◆",
                "Privacy",
                "Your data stays on this device."
            ),
            1
        )

        page_layout = QVBoxLayout(content)

        page_layout.setContentsMargins(
            40,
            26,
            40,
            30
        )

        page_layout.setSpacing(20)

        page_layout.addLayout(header)
        page_layout.addWidget(hero_card)
        page_layout.addWidget(section_title)
        page_layout.addLayout(features_layout)
        page_layout.addStretch()

        self.floating_help_button = QPushButton(
            "?"
        )

        self.floating_help_button.setObjectName(
            "floatingHelpButton"
        )

        self.floating_help_button.setFixedSize(
            58,
            58
        )

        self.floating_help_button.setCursor(
            Qt.PointingHandCursor
        )

        self.floating_help_button.setToolTip(
            "Open help"
        )

        self.floating_help_button.clicked.connect(
            self.help_requested.emit
        )

        wrapper = QWidget()

        wrapper.setObjectName(
            "homeWrapper"
        )

        wrapper_layout = QGridLayout(
            wrapper
        )

        wrapper_layout.setContentsMargins(
            0,
            0,
            24,
            24
        )

        wrapper_layout.addWidget(
            content,
            0,
            0
        )

        wrapper_layout.addWidget(
            self.floating_help_button,
            0,
            0,
            Qt.AlignRight
            | Qt.AlignBottom
        )

        return wrapper

    def _build_header(self):
        heart = QLabel("♥")
        heart.setObjectName("homeHeart")

        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        self.welcome_label = QLabel(
            "Welcome"
        )

        self.welcome_label.setObjectName(
            "welcomeLabel"
        )

        self.welcome_label.setAlignment(
            Qt.AlignRight
            | Qt.AlignVCenter
        )

        layout = QHBoxLayout()

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.setSpacing(8)

        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()

        layout.addWidget(
            self.welcome_label
        )

        return layout

    def _build_hero_card(self):
        card = QFrame()

        card.setObjectName(
            "heroCard"
        )

        card.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        card.setMinimumHeight(240)

        self._add_shadow(
            card,
            32,
            8
        )

        eyebrow = QLabel(
            "PRIVATE WELLBEING SUPPORT"
        )

        eyebrow.setObjectName(
            "heroEyebrow"
        )

        title = QLabel(
            "Understand how you feel"
        )

        title.setObjectName(
            "heroTitle"
        )

        description = QLabel(
            "Complete a short check-in using "
            "the signals you choose."
        )

        description.setObjectName(
            "heroDescription"
        )

        description.setWordWrap(True)

        description.setMaximumWidth(
            520
        )

        self.start_button = QPushButton(
            "Start check-in"
        )

        self.start_button.setObjectName(
            "startCheckInButton"
        )

        self.start_button.setCursor(
            Qt.PointingHandCursor
        )

        self.start_button.setFixedSize(
            210,
            50
        )

        self.start_button.clicked.connect(
            self.check_in_requested.emit
        )

        privacy_note = QLabel(
            "Private and stored locally."
        )

        privacy_note.setObjectName(
            "privacyNote"
        )

        text_layout = QVBoxLayout()

        text_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        text_layout.setSpacing(10)

        text_layout.addWidget(eyebrow)
        text_layout.addWidget(title)
        text_layout.addWidget(description)

        text_layout.addSpacing(6)

        text_layout.addWidget(
            self.start_button,
            0,
            Qt.AlignLeft
        )

        text_layout.addWidget(
            privacy_note
        )

        visual_circle = QFrame()

        visual_circle.setObjectName(
            "heroVisualCircle"
        )

        visual_circle.setFixedSize(
            150,
            150
        )

        visual_circle.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        visual_heart = QLabel("♥")

        visual_heart.setObjectName(
            "heroVisualHeart"
        )

        visual_heart.setAlignment(
            Qt.AlignCenter
        )

        circle_layout = QVBoxLayout(
            visual_circle
        )

        circle_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        circle_layout.addWidget(
            visual_heart
        )

        visual_text = QLabel(
            "Private  •  Local"
        )

        visual_text.setObjectName(
            "heroVisualText"
        )

        visual_text.setAlignment(
            Qt.AlignCenter
        )

        visual_layout = QVBoxLayout()

        visual_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        visual_layout.setSpacing(12)

        visual_layout.addStretch()

        visual_layout.addWidget(
            visual_circle,
            0,
            Qt.AlignHCenter
        )

        visual_layout.addWidget(
            visual_text
        )

        visual_layout.addStretch()

        layout = QHBoxLayout(card)

        layout.setContentsMargins(
            40,
            30,
            40,
            30
        )

        layout.setSpacing(34)

        layout.addLayout(
            text_layout,
            3
        )

        layout.addLayout(
            visual_layout,
            1
        )

        return card

    def _feature_card(
        self,
        symbol,
        title_text,
        description_text
    ):
        card = QFrame()

        card.setObjectName(
            "featureCard"
        )

        card.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        card.setMinimumHeight(150)

        self._add_shadow(
            card,
            20,
            5
        )

        icon = QLabel(symbol)

        icon.setObjectName(
            "featureIcon"
        )

        icon.setAlignment(
            Qt.AlignCenter
        )

        icon.setFixedSize(
            42,
            42
        )

        title = QLabel(title_text)

        title.setObjectName(
            "featureTitle"
        )

        description = QLabel(
            description_text
        )

        description.setObjectName(
            "featureDescription"
        )

        description.setWordWrap(True)

        layout = QVBoxLayout(card)

        layout.setContentsMargins(
            20,
            18,
            20,
            18
        )

        layout.setSpacing(10)

        layout.addWidget(icon)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addStretch()

        return card

    def _add_shadow(
        self,
        widget,
        blur_radius,
        vertical_offset
    ):
        shadow = QGraphicsDropShadowEffect(
            widget
        )

        shadow.setBlurRadius(
            blur_radius
        )

        shadow.setOffset(
            0,
            vertical_offset
        )

        shadow.setColor(
            QColor(
                15,
                23,
                42,
                28
            )
        )

        widget.setGraphicsEffect(
            shadow
        )

    def set_user(
        self,
        full_name
    ):
        if full_name:
            first_name = full_name.split()[0]

            self.welcome_label.setText(
                f"Welcome, {first_name}"
            )
        else:
            self.welcome_label.setText(
                "Welcome"
            )