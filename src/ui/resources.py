"""Curated external reading/viewing, not personalised medical recommendations."""
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QSizePolicy
from src.ui.translations import ENGLISH_TEXT, get_text

ENGLISH_TEXT.update({
    'resources_title': 'A little space for yourself',
    'resources_subtitle': 'Explore practical resources at your own pace.',
    'resource_watch': 'WATCH  ·  NHS',
    'resource_read': 'READ  ·  NHS',
    'resource_guide': 'GUIDE + AUDIO  ·  WHO',
    'resource_breathe': 'Take a breathing break',
    'resource_breathe_desc': 'A guided box-breathing video from the NHS Waiting Room resource collection.',
    'resource_stress': 'Find a calmer rhythm',
    'resource_stress_desc': 'A simple breathing exercise you can read and practise at your own pace.',
    'resource_ground': 'Make room for what matters',
    'resource_ground_desc': 'An illustrated stress-management guide, with accompanying audio exercises.',
    'resource_mindline': 'Explore mindline.sg',
    'resource_mindline_desc': "Singapore's national mental health platform, with a self-assessment tool and guided self-care exercises.",
    'resource_hpb': 'Everyday wellbeing tools',
    'resource_hpb_desc': "Self-care tools and resources from Singapore's Health Promotion Board to understand and manage your wellbeing.",
    'resource_helpline': 'Talk to someone (mindline 1771)',
    'resource_helpline_desc': "Singapore's national 24/7 mental health helpline and textline — reach support by call, text or online chat.",
    'resource_open': 'Open resource',
    'resource_close': 'Close',
    'resource_external': 'Opens in your browser. These external resources are in English; other languages may be available from the provider.',
    'resource_failed': 'Your browser could not be opened. Copy the link below into your browser.',
    'resource_general': 'General wellbeing information, not a personalised treatment recommendation.',
    'home_trends_title': 'See the bigger picture',
    'home_trends_desc': 'Explore your saved check-ins and notice patterns over time.',
    'home_assistant_title': 'A place for your questions',
    'home_assistant_desc': 'Ask the Solace Assistant about your saved wellbeing history.',
    'home_overview': 'Your wellbeing, in focus',
    'home_care_line': 'A moment for you, between caring for others.',
    'home_resource_link': 'Explore resource',
    'nav_workspace': 'YOUR SPACE',
    'home_step_note': 'Reflect. Understand. Take your next step.',
})

RESOURCES = [
    ('resource_watch', 'resource_breathe', 'resource_breathe_desc', 'https://londonwaitingroom.nhs.uk/box-breathing-stress', 'mint'),
    ('resource_read', 'resource_stress', 'resource_stress_desc', 'https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/', 'sand'),
    ('resource_guide', 'resource_ground', 'resource_ground_desc', 'https://www.who.int/publications/i/item/9789240003927', 'blue'),
]

class ResourceDialog(QDialog):
    def __init__(self, resource, language, parent=None):
        super().__init__(parent)
        t = lambda key: get_text(language, key)
        kind, title, description, self.url, tone = resource
        self.setWindowTitle(t(title))
        self.resize(560, 340)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 30)
        layout.setSpacing(10)

        tag = QLabel(t(kind))
        tag.setObjectName('resourceTag')
        tag.setProperty('tone', tone)
        tag.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        layout.addWidget(tag)

        for text, name in [(t(title),'resourceDialogTitle'),
                           (t(description),'resourceDialogBody'),
                           (t('resource_general'),'resourceDialogNote'),
                           (t('resource_external'),'resourceDialogNote')]:
            label = QLabel(text)
            label.setWordWrap(True)
            label.setObjectName(name)
            layout.addWidget(label)
        self.error = QLabel()
        self.error.setWordWrap(True)
        self.error.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.error.hide()
        layout.addWidget(self.error)
        row = QHBoxLayout()
        close = QPushButton(t('resource_close'))
        close.clicked.connect(self.reject)
        open_button = QPushButton(t('resource_open'))
        open_button.setObjectName('primaryButton')
        open_button.clicked.connect(lambda: self.open_resource(t))
        for button in [close, open_button]:
            button.setMinimumHeight(44)
            button.setCursor(Qt.PointingHandCursor)
            row.addWidget(button)
        layout.addLayout(row)

    def open_resource(self, t):
        if not QDesktopServices.openUrl(QUrl(self.url)):
            self.error.setText(t('resource_failed') + '\n' + self.url)
            self.error.show()

# Curated wellbeing resources for the Assistant: verified titles, descriptions
# and links only (no images). Kept separate from RESOURCES (home page) so the
# home layout stays at three illustrated cards. Every URL here is real and
# verified — the model can only surface these, never invented links.
# Each entry: (title_key, description_key, url)
WELLBEING_RESOURCES = [
    ('resource_breathe', 'resource_breathe_desc',
     'https://londonwaitingroom.nhs.uk/box-breathing-stress'),                                   # 0 NHS box-breathing
    ('resource_stress', 'resource_stress_desc',
     'https://www.nhs.uk/mental-health/self-help/guides-tools-and-activities/breathing-exercises-for-stress/'),  # 1 NHS breathing
    ('resource_ground', 'resource_ground_desc',
     'https://www.who.int/publications/i/item/9789240003927'),                                   # 2 WHO stress guide
    ('resource_mindline', 'resource_mindline_desc',
     'https://www.mindline.sg'),                                                                 # 3 mindline.sg
    ('resource_hpb', 'resource_hpb_desc',
     'https://www.hpb.gov.sg/healthy-living/mental-well-being/'),                                # 4 HPB well-being
    ('resource_helpline', 'resource_helpline_desc',
     'https://www.moh.gov.sg/seeking-healthcare/find-a-facility-or-service/mental-health-services/'),  # 5 mindline 1771
]

# Which verified resources to surface for each wellbeing band.
# Indices refer to WELLBEING_RESOURCES above.
RESOURCES_BY_BAND = {
    'low':  [5, 3, 1],   # lower range: helpline, mindline.sg, NHS breathing
    'mid':  [3, 1, 2],   # moderate: mindline.sg, NHS breathing, WHO guide
    'high': [2, 4, 0],   # higher range: WHO guide, HPB well-being, NHS box-breathing
}


def resources_for_score(score):
    """Return up to 3 verified resources ordered for the score band.
    score is 0-100 or None. Never returns invented links."""
    if score is None:
        band = 'mid'
    elif score >= 67:
        band = 'high'
    elif score >= 34:
        band = 'mid'
    else:
        band = 'low'

    order = RESOURCES_BY_BAND.get(band, [0, 1, 2])
    picked = []
    for i in order[:3]:
        if 0 <= i < len(WELLBEING_RESOURCES):
            title_key, desc_key, url = WELLBEING_RESOURCES[i]
            picked.append({
                'title_key': title_key,
                'desc_key': desc_key,
                'url': url,
            })
    return {'band': band, 'resources': picked}
