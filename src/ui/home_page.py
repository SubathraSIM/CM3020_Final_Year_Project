from pathlib import Path

from PySide6.QtCore import QDateTime, QLocale, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from src.ui.translations import ENGLISH_TEXT, get_text


ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "src" / "images"

LOCALES = {
    "English": "en_SG",
    "Malay": "ms_MY",
    "Chinese": "zh_CN",
    "Tamil": "ta_IN",
}

HOME_TEXT = {
    "assistant": "Assistant",
    "home_eyebrow": "PRIVATE WELLBEING CHECK-IN",
    "home_description": "Take a short check-in to reflect on how you are feeling today.",

    "good_morning": "Good morning",
    "good_afternoon": "Good afternoon",
    "good_evening": "Good evening",

    "today": "Today",
    "wellbeing_reminders": "Wellbeing reminders",

    "tip_pause_title": "Pause and reset",
    "tip_pause_text":
        "Take one quiet minute between demanding tasks to slow down and reset.",

    "tip_hydrate_title": "Hydrate and refuel",
    "tip_hydrate_text":
        "Remember water and regular meals during long or busy shifts.",

    "tip_pattern_title": "Notice your patterns",
    "tip_pattern_text":
        "Regular check-ins can help you notice changes in how you have been feeling.",

    "home_private_note": "Your check-in history is stored locally on this device.",
}

ENGLISH_TEXT.update(HOME_TEXT)


class HoverSidebar(QFrame):
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    assistant_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    COLLAPSED = 76
    EXPANDED = 220

    def __init__(self):
        super().__init__()

        self.current_language = "English"
        self.expanded = False

        self.setObjectName("sideBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(self.COLLAPSED)

        self.home_button = self.make_button("home_icon.png", "home", True)
        self.check_in_button = self.make_button("check_in_icon.png", "check_in")
        self.trends_button = self.make_button("trends_icon.png", "trends")
        self.assistant_button = self.make_button("white_heart.png", "assistant")
        self.settings_button = self.make_button("settings_icon.png", "settings")
        self.logout_button = self.make_button("logout.png", "logout")

        self.home_button.clicked.connect(self.home_requested.emit)
        self.check_in_button.clicked.connect(self.check_in_requested.emit)
        self.trends_button.clicked.connect(self.trends_requested.emit)
        self.assistant_button.clicked.connect(self.assistant_requested.emit)
        self.settings_button.clicked.connect(self.settings_requested.emit)
        self.logout_button.clicked.connect(self.logout_requested.emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 18, 10, 12)
        layout.setSpacing(6)
        layout.addWidget(self.home_button)
        layout.addWidget(self.check_in_button)
        layout.addWidget(self.trends_button)
        layout.addWidget(self.assistant_button)
        layout.addStretch()
        layout.addWidget(self.settings_button)
        layout.addWidget(self.logout_button)

    def make_button(self, image, key, active=False):
        button = QPushButton()
        button.setObjectName("navButton")
        button.setIcon(QIcon(str(IMAGES / image)))
        button.setIconSize(QSize(38, 38))
        button.setFixedHeight(54)
        button.setCursor(Qt.PointingHandCursor)
        button.setProperty("active", active)
        button.setProperty("expanded", False)
        button.setProperty("textKey", key)
        return button

    def buttons(self):
        return (
            self.home_button,
            self.check_in_button,
            self.trends_button,
            self.assistant_button,
            self.settings_button,
            self.logout_button,
        )

    def set_language(self, language):
        self.current_language = language

        for button in self.buttons():
            text = get_text(language, button.property("textKey"))
            button.setToolTip(text)
            button.setText(f"   {text}" if self.expanded else "")

    def enterEvent(self, event):
        self.set_expanded(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.set_expanded(False)
        super().leaveEvent(event)

    def set_expanded(self, expanded):
        self.expanded = expanded
        self.setFixedWidth(self.EXPANDED if expanded else self.COLLAPSED)

        for button in self.buttons():
            text = get_text(self.current_language, button.property("textKey"))
            button.setText(f"   {text}" if expanded else "")
            button.setProperty("expanded", expanded)
            button.style().unpolish(button)
            button.style().polish(button)


class HomePage(QWidget):
    check_in_requested = Signal()
    trends_requested = Signal()
    assistant_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()

        self.current_language = "English"
        self.first_name = ""
        self.locale = QLocale(LOCALES["English"])

        self.sidebar = HoverSidebar()
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
        self.sidebar.trends_requested.connect(self.trends_requested.emit)
        self.sidebar.assistant_requested.connect(self.assistant_requested.emit)
        self.sidebar.settings_requested.connect(self.settings_requested.emit)
        self.sidebar.logout_requested.connect(self.logout_requested.emit)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.sidebar)
        layout.addWidget(self.build_content(), 1)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.set_language("English")

    def build_content(self):
        content = QWidget()
        content.setObjectName("homeContent")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(16)
        hero_row.addWidget(self.build_hero(), 3)
        hero_row.addWidget(self.build_time_card(), 1)

        self.reminder_title = QLabel()
        self.reminder_title.setObjectName("sectionTitle")

        pause, self.pause_title, self.pause_text = self.tip_card()
        hydrate, self.hydrate_title, self.hydrate_text = self.tip_card()
        pattern, self.pattern_title, self.pattern_text = self.tip_card()

        tips = QHBoxLayout()
        tips.setSpacing(16)
        tips.addWidget(pause, 1)
        tips.addWidget(hydrate, 1)
        tips.addWidget(pattern, 1)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(40, 26, 40, 30)
        layout.setSpacing(20)
        layout.addLayout(self.build_header())
        layout.addSpacing(4)
        layout.addLayout(hero_row)
        layout.addWidget(self.reminder_title)
        layout.addLayout(tips)
        layout.addStretch()

        return content

    def build_header(self):
        heart = QLabel()
        heart.setFixedSize(30, 30)
        heart.setPixmap(
            QPixmap(str(IMAGES / "heart.png")).scaled(
                28, 28, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        heart.setAlignment(Qt.AlignCenter)

        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        self.welcome_label = QLabel()
        self.welcome_label.setObjectName("welcomeLabel")
        self.welcome_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout = QHBoxLayout()
        layout.setSpacing(7)
        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()
        layout.addWidget(self.welcome_label)
        return layout

    def build_hero(self):
        card = QFrame()
        card.setObjectName("heroCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(235)

        self.hero_eyebrow = QLabel()
        self.hero_eyebrow.setObjectName("heroEyebrow")

        self.hero_title = QLabel()
        self.hero_title.setObjectName("heroTitle")
        self.hero_title.setWordWrap(True)

        self.hero_description = QLabel()
        self.hero_description.setObjectName("heroDescription")
        self.hero_description.setWordWrap(True)

        self.start_button = QPushButton()
        self.start_button.setObjectName("startCheckInButton")
        self.start_button.setFixedHeight(50)
        self.start_button.setMinimumWidth(210)
        self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.check_in_requested.emit)

        self.private_note = QLabel()
        self.private_note.setObjectName("privacyNote")
        self.private_note.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(36, 28, 36, 28)
        layout.setSpacing(10)
        layout.addWidget(self.hero_eyebrow)
        layout.addWidget(self.hero_title)
        layout.addWidget(self.hero_description)
        layout.addStretch()
        layout.addWidget(self.start_button, 0, Qt.AlignLeft)
        layout.addWidget(self.private_note)

        return card

    def build_time_card(self):
        card = QFrame()
        card.setObjectName("featureCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumWidth(220)

        self.today_title = QLabel()
        self.today_title.setObjectName("featureTitle")

        self.time_value = QLabel()
        self.time_value.setObjectName("homeTime")
        self.time_value.setAlignment(Qt.AlignCenter)

        self.date_value = QLabel()
        self.date_value.setObjectName("featureDescription")
        self.date_value.setAlignment(Qt.AlignCenter)
        self.date_value.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(10)
        layout.addWidget(self.today_title)
        layout.addStretch()
        layout.addWidget(self.time_value)
        layout.addWidget(self.date_value)
        layout.addStretch()

        return card

    def tip_card(self):
        card = QFrame()
        card.setObjectName("featureCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumHeight(135)

        title = QLabel()
        title.setObjectName("featureTitle")
        title.setWordWrap(True)

        text = QLabel()
        text.setObjectName("featureDescription")
        text.setWordWrap(True)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(text)
        layout.addStretch()

        return card, title, text

    def t(self, key):
        return get_text(self.current_language, key)

    def set_language(self, language):
        self.current_language = language
        self.locale = QLocale(LOCALES[language])
        self.sidebar.set_language(language)

        texts = {
            self.hero_eyebrow: "home_eyebrow",
            self.hero_description: "home_description",
            self.start_button: "start_check_in",
            self.private_note: "home_private_note",
            self.today_title: "today",
            self.reminder_title: "wellbeing_reminders",
            self.pause_title: "tip_pause_title",
            self.pause_text: "tip_pause_text",
            self.hydrate_title: "tip_hydrate_title",
            self.hydrate_text: "tip_hydrate_text",
            self.pattern_title: "tip_pattern_title",
            self.pattern_text: "tip_pattern_text",
        }

        for widget, key in texts.items():
            widget.setText(self.t(key))

        self.start_button.setMinimumWidth(250 if language == "Tamil" else 210)
        self.update_clock()
        self.tamil_fonts()

    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        widgets = [
            (self.hero_title, 24),
            (self.hero_eyebrow, 9),
            (self.hero_description, 10),
            (self.start_button, 10),
            (self.private_note, 9),
            (self.today_title, 10),
            (self.reminder_title, 15),
            (self.pause_title, 11),
            (self.pause_text, 9),
            (self.hydrate_title, 11),
            (self.hydrate_text, 9),
            (self.pattern_title, 11),
            (self.pattern_text, 9),
            (self.welcome_label, 10),
        ]

        for widget, size in widgets:
            widget.setStyleSheet(f"font-size:{size}px;" if tamil else "")

    def set_user(self, full_name):
        self.first_name = full_name.split()[0] if full_name else ""
        self.update_clock()

    def update_clock(self):
        now = QDateTime.currentDateTime()
        hour = now.time().hour()

        if hour < 12:
            greeting = self.t("good_morning")
        elif hour < 18:
            greeting = self.t("good_afternoon")
        else:
            greeting = self.t("good_evening")

        self.hero_title.setText(
            f"{greeting}, {self.first_name}" if self.first_name else greeting
        )

        welcome = self.t("welcome")
        self.welcome_label.setText(
            f"{welcome}, {self.first_name}" if self.first_name else welcome
        )

        self.time_value.setText(now.time().toString("HH:mm"))
        self.date_value.setText(
            self.locale.toString(now.date(), "dddd, d MMMM yyyy")
        )