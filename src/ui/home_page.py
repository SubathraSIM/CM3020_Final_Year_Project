from src.ui.account_widgets import add_avatar
from pathlib import Path

from PySide6.QtCore import QDateTime, QLocale, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget, QScrollArea,
)

from src.ui.ui_components import GardenArtwork, AnimatedIllustration, scroll_page, reveal, float_in
from src.ui.resources import RESOURCES, ResourceDialog

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
    EXPANDED = 196

    # Shared across every page's sidebar so the open/closed choice persists
    # when navigating between pages.
    _shared_expanded = True

    def __init__(self):
        super().__init__()

        self.current_language = "English"
        self.expanded = HoverSidebar._shared_expanded

        self.setObjectName("sideBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFixedWidth(self.EXPANDED if self.expanded else self.COLLAPSED)

        # Hamburger toggle at the top.
        self.toggle_button = QPushButton()
        self.toggle_button.setObjectName("navToggle")
        self.toggle_button.setIcon(QIcon(str(IMAGES / "close_icon.png")))
        self.toggle_button.setIconSize(QSize(60, 60))
        self.toggle_button.setFixedHeight(60)
        self.toggle_button.setCursor(Qt.PointingHandCursor)
        self.toggle_button.setFocusPolicy(Qt.NoFocus)
        self.toggle_button.clicked.connect(self.toggle)

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
        layout.setContentsMargins(14, 20, 14, 20)
        layout.setSpacing(6)
        layout.addWidget(self.toggle_button)
        layout.addSpacing(8)
        layout.addWidget(self.home_button)
        layout.addWidget(self.check_in_button)
        layout.addWidget(self.trends_button)
        layout.addWidget(self.assistant_button)
        layout.addStretch()
        layout.addWidget(self.settings_button)
        layout.addWidget(self.logout_button)

        # Apply the shared collapsed/expanded state to this new sidebar.
        self.set_expanded(self.expanded)

    def make_button(self, image, key, active=False):
        button = QPushButton()
        button.setObjectName("navButton")
        button.setIcon(QIcon(str(IMAGES / image)))
        button.setIconSize(QSize(60, 60))
        button.setFixedHeight(60)
        button.setCursor(Qt.PointingHandCursor)
        button.setFocusPolicy(Qt.NoFocus)
        button.setProperty("active", active)
        button.setProperty("expanded", True)
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
        tamil = language == "Tamil"

        for button in self.buttons():
            text = get_text(language, button.property("textKey"))
            button.setToolTip(text)
            button.setAccessibleName(text)
            button.setText(f"{text}" if self.expanded else "")
            # Tamil words are longer — shrink so they fit the sidebar width.
            button.setStyleSheet("font-size:10px;" if tamil else "")

    def set_active(self, key):
        for button in self.buttons():
            active = button.property("textKey") == key
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)

    def toggle(self):
        self.set_expanded(not self.expanded)

    def set_expanded(self, expanded):
        self.expanded = expanded
        HoverSidebar._shared_expanded = expanded
        self.setFixedWidth(self.EXPANDED if expanded else self.COLLAPSED)
        # Re-apply labels: text shows only when expanded.
        self.set_language(self.current_language)
        # Centre the icons when collapsed, left-align when expanded.
        for button in self.buttons():
            button.setProperty("collapsed", not expanded)
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
        self.content = self.build_content()
        layout.addWidget(self.sidebar)
        layout.addWidget(self.content, 1)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.set_language("English")

    def showEvent(self, event):
        super().showEvent(event)
        self.sidebar.set_active("home")
        self.sidebar.set_expanded(HoverSidebar._shared_expanded)
        float_in(self.content)
        
    def build_content(self):
        content = QWidget()
        content.setObjectName("homeContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(28, 18, 28, 18)
        layout.setSpacing(10)
        layout.addLayout(self.build_header())
        self.overview_label = QLabel()
        self.overview_label.setObjectName("pageEyebrow")
        layout.addWidget(self.overview_label)
        layout.addWidget(self.build_hero())

        quick = QHBoxLayout()
        quick.setSpacing(16)
        self.quick_labels = []
        for title, description, signal, icon in [
            ('home_trends_title', 'home_trends_desc', self.trends_requested, 'trends_icon'),
            ('home_assistant_title', 'home_assistant_desc', self.assistant_requested, 'white_heart')]:
            card = QPushButton()
            card.setObjectName('quickCard')
            card.setCursor(Qt.PointingHandCursor)
            card.setMinimumHeight(72)
            card.clicked.connect(signal.emit)
            inside = QVBoxLayout(card)
            inside.setContentsMargins(16, 12, 16, 12)
            heading = QLabel(); heading.setObjectName('featureTitle')
            note = QLabel(); note.setObjectName('featureDescription'); note.setWordWrap(True)
            for label in (heading, note):
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
                inside.addWidget(label)
            self.quick_labels.append((card, heading, note, title, description))
            quick.addWidget(card, 1)
        layout.addLayout(quick)
        self.resources_title = QLabel(); self.resources_title.setObjectName('sectionTitle')
        self.resources_subtitle = QLabel(); self.resources_subtitle.setObjectName('featureDescription')
        layout.addWidget(self.resources_title)
        layout.addWidget(self.resources_subtitle)
        resource_row = QHBoxLayout(); resource_row.setSpacing(16)
        self.resource_labels = []
        for resource in RESOURCES:
            card = QPushButton(); card.setObjectName('resourceCard')
            card.setCursor(Qt.PointingHandCursor)
            card.setMinimumHeight(300)
            card.clicked.connect(lambda checked=False, r=resource: ResourceDialog(r, self.current_language, self).exec())
            inside = QVBoxLayout(card); inside.setContentsMargins(16, 12, 16, 12); inside.setSpacing(6)
            kind = QLabel(); kind.setObjectName('resourceTag'); kind.setProperty('tone',resource[4])
            title = QLabel(); title.setObjectName('resourceTitle'); title.setWordWrap(True)
            description = QLabel(); description.setObjectName('featureDescription'); description.setWordWrap(True)
            link = QLabel(); link.setObjectName('resourceLink'); link.hide()
            art = AnimatedIllustration(['yoga.jpg', 'stretch.jpg', 'reading.jpg'][len(self.resource_labels)], fit=True)
            art.setFixedHeight(190)
            inside.addWidget(art)
            for label in (kind, title, description):
                label.setAttribute(Qt.WA_TransparentForMouseEvents)
                inside.addWidget(label)
            inside.addStretch()
            self.resource_labels.append((card, kind, title, description, link, resource))
            resource_row.addWidget(card, 1)
        layout.addLayout(resource_row)
        layout.addStretch()
        return content

    def build_header(self):
        heart = QLabel()
        heart.setFixedSize(42, 42)
        heart.setPixmap(
            QPixmap(str(IMAGES / "heart.png")).scaled(
                60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation
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
        add_avatar(layout)
        return layout

    def build_hero(self):
        card = QFrame(); card.setObjectName('heroCard')
        card.setMinimumHeight(230)
        row = QHBoxLayout(card); row.setContentsMargins(0,0,0,0); row.setSpacing(0)
        text = QVBoxLayout(); text.setContentsMargins(24,20,18,20); text.setSpacing(8)
        self.hero_eyebrow = QLabel(); self.hero_eyebrow.setObjectName('heroEyebrow')
        self.hero_title = QLabel(); self.hero_title.setObjectName('heroTitle'); self.hero_title.setWordWrap(True)
        self.hero_description = QLabel(); self.hero_description.setObjectName('heroDescription'); self.hero_description.setWordWrap(True)
        self.start_button = QPushButton(); self.start_button.setObjectName('startCheckInButton')
        self.start_button.setFixedHeight(46); self.start_button.setCursor(Qt.PointingHandCursor)
        self.start_button.clicked.connect(self.check_in_requested.emit)
        self.private_note = QLabel(); self.private_note.setObjectName('privacyNote'); self.private_note.setWordWrap(True)
        for widget in (self.hero_eyebrow,self.hero_title,self.hero_description): text.addWidget(widget)
        text.addSpacing(10)
        text.addWidget(self.start_button,0,Qt.AlignLeft)
        text.addWidget(self.private_note)
        text.addStretch()
        row.addLayout(text, 3)
        artwork = AnimatedIllustration("care.jpg", fit=True); artwork.setMinimumWidth(340)
        row.addWidget(artwork, 3)
        self.hero_card = card
        return card

    def t(self, key):
        return get_text(self.current_language, key)

    def set_language(self, language):
        self.current_language = language
        self.locale = QLocale(LOCALES[language])
        self.sidebar.set_language(language)
        for widget, key in [(self.hero_eyebrow,'home_eyebrow'),(self.hero_description,'home_care_line'),
                            (self.start_button,'start_check_in'),(self.private_note,'home_private_note'),
                            (self.overview_label,'home_overview'),(self.resources_title,'resources_title'),
                            (self.resources_subtitle,'resources_subtitle')]:
            widget.setText(self.t(key))
        for card, heading, note, title, description in self.quick_labels:
            heading.setText(self.t(title)); note.setText(self.t(description))
            card.setAccessibleName(self.t(title))
        for card, kind, title, description, link, resource in self.resource_labels:
            kind.setText(self.t(resource[0])); title.setText(self.t(resource[1]))
            description.setText(self.t(resource[2])); link.setText(self.t('home_resource_link'))
            card.setAccessibleName(self.t(resource[1])); card.setToolTip(resource[3])
        self.tamil_fonts()
        self.update_clock()

    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        # Tamil text runs longer; shrink the big/hero text so it fits the
        # cards without clipping. Other languages keep the CSS defaults.
        sizes = [
            (self.hero_eyebrow, 9),
            (self.hero_title, 22),
            (self.hero_description, 12),
            (self.start_button, 11),
            (self.private_note, 10),
            (self.overview_label, 11),
            (self.resources_title, 16),
            (self.resources_subtitle, 11),
        ]
        for widget, size in sizes:
            widget.setStyleSheet(f"font-size:{size}px;" if tamil else "")

        # Quick cards + resource cards text.
        for card, heading, note, title, description in self.quick_labels:
            heading.setStyleSheet("font-size:13px;" if tamil else "")
            note.setStyleSheet("font-size:11px;" if tamil else "")
        for card, kind, title, description, link, resource in self.resource_labels:
            kind.setStyleSheet("font-size:9px;" if tamil else "")
            title.setStyleSheet("font-size:13px;" if tamil else "")
            description.setStyleSheet("font-size:11px;" if tamil else "")

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

        self.welcome_label.setText(self.locale.toString(now.date(), "dddd, d MMMM yyyy"))