import re
from pathlib import Path

from PySide6.QtCore import QDate, QLocale, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCalendarWidget, QComboBox, QFrame, QHBoxLayout, QLabel,
    QPlainTextEdit, QProgressBar, QPushButton, QScrollArea,
    QSizePolicy, QStackedWidget, QVBoxLayout, QWidget
)

from src.database.database import (
    get_check_in_dates,
    get_check_in_for_date,
    get_month_check_ins,
)
from src.ui.check_in_page import MiniTrendGraph
from src.ui.home_page import HoverSidebar
from src.ui.translations import ENGLISH_TEXT, get_text


ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "src" / "images"

LOCALES = {
    "English": "en_SG",
    "Malay": "ms_MY",
    "Chinese": "zh_CN",
    "Tamil": "ta_IN",
}

TREND_TEXT = {
    "history_title": "Wellbeing history",
    "history_subtitle":
        "Select a date to review the wellbeing summary saved for that check-in.",

    "monthly_trend": "This month's trend",
    "trend_note": "Each point represents a saved check-in.",
    "trend_empty": "Check in again to see the monthly trend.",

    "checkin_calendar": "Check-in calendar",
    "calendar_note": "A grey dot marks a date with a saved check-in.",
    "saved_checkin": "Saved check-in",

    "select_date": "Select a date",
    "select_date_note":
        "Select a date with a grey dot to review a saved wellbeing summary.",
    "no_checkin": "No check-in was completed on this date.",

    "latest_checkin": "Latest check-in at",
    "input_used": "Input used",

    "history_transcript": "Transcript",
    "history_recommendations": "Supportive recommendations",
    "history_signals": "Supporting signals",
}

ENGLISH_TEXT.update(TREND_TEXT)


class CheckInCalendar(QCalendarWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.saved_dates = set()

    def set_saved_dates(self, dates):
        self.saved_dates = {
            date.toString("yyyy-MM-dd")
            for date in dates
        }
        self.updateCells()

    def paintCell(self, painter, rect, date):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(rect, QColor("#FFFFFF"))

        selected = date == self.selectedDate()
        current_month = (
            date.year() == self.yearShown()
            and date.month() == self.monthShown()
        )

        if selected:
            diameter = min(38, rect.width() - 8, rect.height() - 6)
            centre = rect.center()

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#0875CE"))
            painter.drawEllipse(
                QRectF(
                    centre.x() - diameter / 2,
                    centre.y() - diameter / 2 - 1,
                    diameter,
                    diameter,
                )
            )
            painter.setPen(QColor("#FFFFFF"))

        elif current_month:
            painter.setPen(QColor("#111827"))

        else:
            painter.setPen(QColor("#9CA3AF"))

        painter.drawText(
            rect.adjusted(0, -2, 0, -2),
            Qt.AlignCenter,
            str(date.day()),
        )

        if (
            date.toString("yyyy-MM-dd") in self.saved_dates
            and not selected
        ):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#9CA3AF"))
            painter.drawEllipse(
                QRectF(
                    rect.center().x() - 2.5,
                    rect.bottom() - 7,
                    5,
                    5,
                )
            )

        painter.restore()


class TrendsPage(QWidget):
    home_requested = Signal()
    check_in_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()

        self.user_id = None
        self.current_language = "English"
        self.locale = QLocale(LOCALES["English"])

        self.sidebar = HoverSidebar()
        self.sidebar.home_requested.connect(self.home_requested.emit)
        self.sidebar.check_in_requested.connect(self.check_in_requested.emit)
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
        )

        for button in buttons:
            button.setProperty("active", False)

        self.sidebar.trends_button.setProperty("active", True)

        for button in buttons:
            button.style().unpolish(button)
            button.style().polish(button)

    # --------------------------------------------------
    # Page
    # --------------------------------------------------

    def build_content(self):
        content = QWidget()
        content.setObjectName("trendsPageContent")

        self.title = QLabel()
        self.title.setObjectName("trendsPageTitle")

        self.subtitle = QLabel()
        self.subtitle.setObjectName("trendsPageSubtitle")
        self.subtitle.setWordWrap(True)

        body = QHBoxLayout()
        body.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(18)
        left.addWidget(self.build_graph_card())
        left.addWidget(self.build_calendar_card())

        body.addLayout(left, 2)
        body.addWidget(self.build_summary_panel(), 3)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(38, 22, 38, 26)
        layout.setSpacing(14)
        layout.addLayout(self.build_header())
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        layout.addLayout(body, 1)

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

        self.user_label = QLabel()
        self.user_label.setObjectName("welcomeLabel")
        self.user_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        layout = QHBoxLayout()
        layout.setSpacing(7)
        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()
        layout.addWidget(self.user_label)

        return layout

    # --------------------------------------------------
    # Trend graph
    # --------------------------------------------------

    def build_graph_card(self):
        card = QFrame()
        card.setObjectName("trendsGraphCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumWidth(335)
        card.setMaximumWidth(390)

        self.graph_title = QLabel()
        self.graph_title.setObjectName("trendsCardTitle")

        self.graph_note = QLabel()
        self.graph_note.setObjectName("trendsCardNote")
        self.graph_note.setWordWrap(True)

        self.trend_graph = MiniTrendGraph()

        self.trend_empty = QLabel()
        self.trend_empty.setObjectName("trendRequirement")
        self.trend_empty.setAlignment(Qt.AlignCenter)
        self.trend_empty.setWordWrap(True)
        self.trend_empty.hide()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        layout.addWidget(self.graph_title)
        layout.addWidget(self.graph_note)
        layout.addWidget(self.trend_graph, 1)
        layout.addWidget(self.trend_empty)

        return card

    # --------------------------------------------------
    # Calendar
    # --------------------------------------------------

    def build_calendar_card(self):
        card = QFrame()
        card.setObjectName("trendsCalendarCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumWidth(335)
        card.setMaximumWidth(390)

        self.calendar_title = QLabel()
        self.calendar_title.setObjectName("trendsCardTitle")

        self.calendar_note = QLabel()
        self.calendar_note.setObjectName("trendsCardNote")
        self.calendar_note.setWordWrap(True)

        self.calendar = CheckInCalendar()
        self.calendar.setObjectName("wellbeingCalendar")
        self.calendar.setGridVisible(False)
        self.calendar.setMaximumHeight(270)
        self.calendar.setNavigationBarVisible(False)
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setHorizontalHeaderFormat(
            QCalendarWidget.HorizontalHeaderFormat.ShortDayNames
        )
        self.calendar.setMaximumDate(QDate.currentDate())
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.calendar.currentPageChanged.connect(self.calendar_page_changed)
        self.calendar.selectionChanged.connect(self.load_selected_date)

        self.nav_prev = QPushButton("‹")
        self.nav_next = QPushButton("›")

        for button in (self.nav_prev, self.nav_next):
            button.setObjectName("calNavArrow")
            button.setFixedSize(34, 30)
            button.setCursor(Qt.PointingHandCursor)

        self.nav_prev.clicked.connect(lambda: self.move_month(-1))
        self.nav_next.clicked.connect(lambda: self.move_month(1))

        self.month_combo = QComboBox()
        self.month_combo.setObjectName("calNavCombo")
        self.month_combo.setCursor(Qt.PointingHandCursor)

        self.year_combo = QComboBox()
        self.year_combo.setObjectName("calNavCombo")
        self.year_combo.setCursor(Qt.PointingHandCursor)

        year = QDate.currentDate().year()

        for value in range(year - 10, year + 1):
            self.year_combo.addItem(str(value), value)

        self.month_combo.currentIndexChanged.connect(self.nav_changed)
        self.year_combo.currentIndexChanged.connect(self.nav_changed)

        nav = QHBoxLayout()
        nav.setContentsMargins(6, 4, 6, 4)
        nav.setSpacing(6)
        nav.addWidget(self.nav_prev)
        nav.addWidget(self.month_combo, 1)
        nav.addWidget(self.year_combo, 1)
        nav.addWidget(self.nav_next)

        nav_bar = QFrame()
        nav_bar.setObjectName("calNavBar")
        nav_bar.setAttribute(Qt.WA_StyledBackground, True)
        nav_bar.setLayout(nav)

        dot = QLabel("●")
        dot.setObjectName("calendarLegendDot")
        dot.setStyleSheet("color:#9CA3AF; font-size:11px;")

        self.legend_text = QLabel()
        self.legend_text.setObjectName("calendarLegendText")

        legend = QHBoxLayout()
        legend.setSpacing(7)
        legend.addWidget(dot)
        legend.addWidget(self.legend_text)
        legend.addStretch()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(10)
        layout.addWidget(self.calendar_title)
        layout.addWidget(self.calendar_note)
        layout.addWidget(nav_bar)
        layout.addWidget(self.calendar, 1)
        layout.addLayout(legend)

        return card

    # --------------------------------------------------
    # History panel
    # --------------------------------------------------

    def build_summary_panel(self):
        panel = QFrame()
        panel.setObjectName("historyPanel")
        panel.setAttribute(Qt.WA_StyledBackground, True)

        self.summary_stack = QStackedWidget()
        self.empty_state = self.build_empty_state()
        self.summary_state = self.build_summary_state()

        self.summary_stack.addWidget(self.empty_state)
        self.summary_stack.addWidget(self.summary_state)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.summary_stack)

        return panel

    def build_empty_state(self):
        page = QWidget()
        page.setObjectName("historyEmptyState")

        self.empty_date = QLabel()
        self.empty_date.setObjectName("historyEmptyTitle")
        self.empty_date.setAlignment(Qt.AlignCenter)

        self.empty_message = QLabel()
        self.empty_message.setObjectName("historyEmptyMessage")
        self.empty_message.setAlignment(Qt.AlignCenter)
        self.empty_message.setWordWrap(True)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(42, 42, 42, 42)
        layout.addStretch()
        layout.addWidget(self.empty_date)
        layout.addWidget(self.empty_message)
        layout.addStretch()

        return page

    def build_summary_state(self):
        page = QWidget()
        page.setObjectName("historySummaryState")

        scroll = QScrollArea()
        scroll.setObjectName("historyScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        content = QWidget()
        content.setObjectName("historyScrollContent")

        self.selected_date = QLabel()
        self.selected_date.setObjectName("historySelectedDate")

        self.selected_time = QLabel()
        self.selected_time.setObjectName("historySelectedTime")

        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.selected_date)
        layout.addWidget(self.selected_time)
        layout.addWidget(self.build_saved_summary_card())
        layout.addWidget(self.build_signals_card())
        layout.addWidget(self.build_transcript_card())
        layout.addWidget(self.build_recommendation_card())
        layout.addStretch()

        scroll.setWidget(content)

        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        return page

    def build_saved_summary_card(self):
        card = QFrame()
        card.setObjectName("historySummaryCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        self.history_image = QLabel()
        self.history_image.setObjectName("historyResultImage")
        self.history_image.setFixedSize(QSize(100, 100))
        self.history_image.setAlignment(Qt.AlignCenter)

        self.history_phrase = QLabel()
        self.history_phrase.setObjectName("historyPhrase")
        self.history_phrase.setWordWrap(True)

        self.history_explanation = QLabel()
        self.history_explanation.setObjectName("historyExplanation")
        self.history_explanation.setWordWrap(True)

        self.history_progress = QProgressBar()
        self.history_progress.setObjectName("trendHistoryProgress")
        self.history_progress.setRange(0, 100)

        self.history_input = QLabel()
        self.history_input.setObjectName("historyInputType")

        text = QVBoxLayout()
        text.setSpacing(8)
        text.addWidget(self.history_phrase)
        text.addWidget(self.history_explanation)
        text.addWidget(self.history_progress)
        text.addWidget(self.history_input)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(18)
        layout.addWidget(self.history_image, 0, Qt.AlignTop)
        layout.addLayout(text, 1)

        return card

    # --------------------------------------------------
    # Five supporting signals
    # --------------------------------------------------

    def build_signals_card(self):
        card = QFrame()
        card.setObjectName("historyDetailsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        self.signals_title = QLabel()
        self.signals_title.setObjectName("trendsCardTitle")

        self.signal_names = {}
        self.signal_values = {}

        rows = QVBoxLayout()
        rows.setSpacing(6)

        for key in (
            "blink_rate",
            "head_position",
            "speech_rate",
            "disfluency",
            "lexical_variety",
        ):
            name = QLabel()
            name.setObjectName("scoreCaveat")

            value = QLabel()
            value.setObjectName("scoreLabel")
            value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            self.signal_names[key] = name
            self.signal_values[key] = value

            row = QHBoxLayout()
            row.addWidget(name)
            row.addStretch()
            row.addWidget(value)
            rows.addLayout(row)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self.signals_title)
        layout.addLayout(rows)

        return card

    def build_transcript_card(self):
        card = QFrame()
        card.setObjectName("historyDetailsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        self.transcript_title = QLabel()
        self.transcript_title.setObjectName("trendsCardTitle")

        self.history_transcript = QPlainTextEdit()
        self.history_transcript.setObjectName("historyTranscript")
        self.history_transcript.setReadOnly(True)
        self.history_transcript.setMinimumHeight(92)
        self.history_transcript.setMaximumHeight(125)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self.transcript_title)
        layout.addWidget(self.history_transcript)

        return card

    def build_recommendation_card(self):
        card = QFrame()
        card.setObjectName("historyDetailsCard")
        card.setAttribute(Qt.WA_StyledBackground, True)

        self.recommendation_title = QLabel()
        self.recommendation_title.setObjectName("trendsCardTitle")

        self.recommendation_layout = QVBoxLayout()
        self.recommendation_layout.setSpacing(8)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        layout.addWidget(self.recommendation_title)
        layout.addLayout(self.recommendation_layout)

        return card

    # --------------------------------------------------
    # Translation
    # --------------------------------------------------

    def t(self, key):
        return get_text(self.current_language, key)

    def set_language(self, language):
        self.current_language = language
        self.locale = QLocale(LOCALES[language])
        self.sidebar.set_language(language)
        self.calendar.setLocale(self.locale)

        self.title.setText(self.t("history_title"))
        self.subtitle.setText(self.t("history_subtitle"))
        self.graph_title.setText(self.t("monthly_trend"))
        self.graph_note.setText(self.t("trend_note"))
        self.trend_empty.setText(self.t("trend_empty"))
        self.calendar_title.setText(self.t("checkin_calendar"))
        self.calendar_note.setText(self.t("calendar_note"))
        self.legend_text.setText(self.t("saved_checkin"))
        self.signals_title.setText(self.t("history_signals"))
        self.transcript_title.setText(self.t("history_transcript"))
        self.recommendation_title.setText(
            self.t("history_recommendations")
        )

        for key, label in self.signal_names.items():
            label.setText(self.t(key))

        self.update_month_names()

        if self.user_id is not None:
            self.load_selected_date()

        self.tamil_fonts()

    def update_month_names(self):
        month = self.calendar.monthShown()

        self.month_combo.blockSignals(True)
        self.month_combo.clear()

        for number in range(1, 13):
            self.month_combo.addItem(
                self.locale.monthName(
                    number,
                    QLocale.FormatType.LongFormat,
                )
            )

        self.month_combo.setCurrentIndex(month - 1)
        self.month_combo.blockSignals(False)

    def tamil_fonts(self):
        tamil = self.current_language == "Tamil"

        sizes = [
            (self.title, 18),
            (self.subtitle, 10),
            (self.graph_title, 11),
            (self.graph_note, 9),
            (self.trend_empty, 9),
            (self.calendar_title, 11),
            (self.calendar_note, 9),
            (self.legend_text, 9),
            (self.signals_title, 11),
            (self.transcript_title, 11),
            (self.recommendation_title, 11),
            (self.history_phrase, 17),
            (self.history_explanation, 10),
            (self.history_input, 9),
        ]

        for widget, size in sizes:
            widget.setStyleSheet(
                f"font-size:{size}px;" if tamil else ""
            )

        for widget in self.signal_names.values():
            widget.setStyleSheet(
                "font-size:9px;" if tamil else ""
            )

        for widget in self.signal_values.values():
            widget.setStyleSheet(
                "font-size:9px;" if tamil else ""
            )

    # --------------------------------------------------
    # User / loading
    # --------------------------------------------------

    def set_user(self, full_name, user_id=None):
        self.user_label.setText(
            full_name.split()[0] if full_name else ""
        )
        self.user_id = user_id

    def refresh_page(self):
        today = QDate.currentDate()

        self.calendar.setCurrentPage(
            today.year(),
            today.month(),
        )
        self.calendar.setSelectedDate(today)

        self.year_combo.setCurrentIndex(
            self.year_combo.findData(today.year())
        )

        self.load_month_markers(
            today.year(),
            today.month(),
        )
        self.load_selected_date()
        self.load_trend_graph()

    def load_trend_graph(self):
        points = get_month_check_ins(self.user_id, 31)

        if len(points) < 2:
            self.trend_graph.hide()
            self.trend_empty.show()
            return

        self.trend_empty.hide()
        self.trend_graph.set_points(points)
        self.trend_graph.show()

    # --------------------------------------------------
    # Calendar navigation
    # --------------------------------------------------

    def nav_changed(self):
        year = self.year_combo.currentData()
        month = self.month_combo.currentIndex() + 1

        if month > 0:
            self.calendar.setCurrentPage(year, month)

    def move_month(self, amount):
        date = QDate(
            self.calendar.yearShown(),
            self.calendar.monthShown(),
            1,
        ).addMonths(amount)

        if date <= QDate.currentDate():
            self.calendar.setCurrentPage(
                date.year(),
                date.month(),
            )

    def calendar_page_changed(self, year, month):
        self.load_month_markers(year, month)

        self.month_combo.blockSignals(True)
        self.year_combo.blockSignals(True)

        self.month_combo.setCurrentIndex(month - 1)
        self.year_combo.setCurrentIndex(
            self.year_combo.findData(year)
        )

        self.month_combo.blockSignals(False)
        self.year_combo.blockSignals(False)

        next_month = QDate(year, month, 1).addMonths(1)
        self.nav_next.setEnabled(
            next_month <= QDate.currentDate()
        )

    def load_month_markers(self, year, month):
        dates = [
            QDate.fromString(text, "yyyy-MM-dd")
            for text in get_check_in_dates(
                self.user_id,
                year,
                month,
            )
        ]

        self.calendar.set_saved_dates(dates)

    # --------------------------------------------------
    # Saved check-in
    # --------------------------------------------------

    def load_selected_date(self):
        date = self.calendar.selectedDate()

        formatted = self.locale.toString(
            date,
            "dddd, d MMMM yyyy",
        )

        check_in = get_check_in_for_date(
            self.user_id,
            date.toString("yyyy-MM-dd"),
        )

        if check_in is None:
            self.empty_date.setText(formatted)
            self.empty_message.setText(self.t("no_checkin"))
            self.summary_stack.setCurrentWidget(
                self.empty_state
            )
            return

        self.show_check_in(formatted, check_in)

    def show_check_in(self, formatted_date, check_in):
        self.selected_date.setText(formatted_date)

        time = str(check_in["created_at_local"])[11:16]

        self.selected_time.setText(
            f"{self.t('latest_checkin')} {time}"
        )

        score = round(float(check_in["wellbeing_score"]))

        self.history_phrase.setText(check_in["summary"])
        self.history_explanation.setText(
            check_in["explanation"]
        )

        self.history_progress.setValue(score)
        self.history_progress.setFormat(
            f"{score} / 100"
        )

        self.history_progress.setProperty(
            "zone",
            self.score_zone(score),
        )

        self.refresh_style(self.history_progress)

        self.history_input.setText(
            f"{self.t('input_used')}: "
            f"{self.t(check_in['input_type'])}"
        )

        self.set_result_image(score)
        self.set_signals(check_in)

        self.history_transcript.setPlainText(
            check_in["transcript"]
        )

        self.set_recommendations(
            check_in["recommendation"]
        )

        self.summary_stack.setCurrentWidget(
            self.summary_state
        )

    # --------------------------------------------------
    # Five saved supporting signals
    # --------------------------------------------------

    def set_signals(self, check_in):
        na = self.t("not_available")

        head_keys = {
            "Centred": "head_centred",
            "Slightly off-centre": "head_slightly_off",
            "Off-centre": "head_off",
        }

        blink = check_in["blink_rate"]
        head = check_in["head_position"]
        speech = check_in["speech_rate"]
        disfluency = check_in["disfluency_rate"]
        lexical = check_in["lexical_variety"]

        values = {
            "blink_rate":
                f"{blink:.1f}/min" if blink is not None else na,

            "head_position":
                self.t(head_keys[head]) if head is not None else na,

            "speech_rate":
                f"{speech:.0f}/min" if speech is not None else na,

            "disfluency":
                f"{disfluency * 100:.1f}%" if disfluency is not None else na,

            "lexical_variety":
                f"{lexical:.2f}" if lexical is not None else na,
        }

        for key, value in values.items():
            self.signal_values[key].setText(value)

    # --------------------------------------------------
    # Result image / recommendations
    # --------------------------------------------------

    def set_result_image(self, score):
        if score >= 67:
            image = "wellbeing_high.png"
        elif score >= 34:
            image = "wellbeing_mid.png"
        else:
            image = "wellbeing_low.png"

        pixmap = QPixmap(str(IMAGES / image))

        self.history_image.setPixmap(
            pixmap.scaled(
                88,
                88,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def set_recommendations(self, text):
        while self.recommendation_layout.count():
            item = self.recommendation_layout.takeAt(0)

            if item.widget():
                item.widget().deleteLater()

        items = re.split(
            r"(?=\b[1-3][.)]\s*)",
            text,
        )

        for item in items:
            item = item.strip().replace("**", "")

            if not item:
                continue

            label = QLabel(item)
            label.setObjectName(
                "historyRecommendationItem"
            )
            label.setWordWrap(True)

            if self.current_language == "Tamil":
                label.setStyleSheet(
                    "font-size:9px;"
                )

            self.recommendation_layout.addWidget(label)

    @staticmethod
    def score_zone(score):
        if score >= 67:
            return "high"
        if score >= 34:
            return "mid"
        return "low"

    @staticmethod
    def refresh_style(widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)