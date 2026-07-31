import re
from pathlib import Path

from PySide6.QtCore import QDate, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import (
    QCalendarWidget,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.database.database import (
    get_check_in_dates,
    get_check_in_for_date,
    get_month_check_ins,
)
from src.ui.check_in_page import MiniTrendGraph
from src.ui.home_page import HoverSidebar


PROJECT_ROOT = Path(__file__).resolve().parents[2]
IMAGES_FOLDER = PROJECT_ROOT / "src" / "images"


class CheckInCalendar(QCalendarWidget):
    """Calendar with a blue selected date and grey saved-check-in dots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._saved_date_keys = set()

    def set_saved_dates(self, dates):
        self._saved_date_keys = {
            date.toString("yyyy-MM-dd")
            for date in dates
            if date.isValid()
        }
        self.updateCells()

    def paintCell(self, painter, rect, date):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setClipRect(rect)
        painter.fillRect(rect, QColor("#FFFFFF"))

        is_selected = date == self.selectedDate()
        is_current_month = (
            date.year() == self.yearShown()
            and date.month() == self.monthShown()
        )
        is_enabled = (
            date >= self.minimumDate()
            and date <= self.maximumDate()
        )

        if is_selected:
            diameter = min(
                38.0,
                float(rect.width() - 8),
                float(rect.height() - 6),
            )
            centre = rect.center()
            circle = QRectF(
                centre.x() - diameter / 2,
                centre.y() - diameter / 2 - 1,
                diameter,
                diameter,
            )

            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#0875CE"))
            painter.drawEllipse(circle)
            painter.setPen(QColor("#FFFFFF"))
        elif not is_enabled:
            painter.setPen(QColor("#CBD5E1"))
        elif is_current_month:
            painter.setPen(QColor("#111827"))
        else:
            painter.setPen(QColor("#9CA3AF"))

        font = painter.font()
        font.setBold(False)
        painter.setFont(font)

        text_rect = rect.adjusted(0, -2, 0, -2)
        painter.drawText(
            text_rect,
            Qt.AlignCenter,
            str(date.day()),
        )

        date_key = date.toString("yyyy-MM-dd")

        if (
            date_key in self._saved_date_keys
            and not is_selected
        ):
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor("#9CA3AF"))
            painter.drawEllipse(
                QRectF(
                    rect.center().x() - 2.5,
                    rect.bottom() - 7.0,
                    5.0,
                    5.0,
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

        self.sidebar = HoverSidebar()

        self.sidebar.home_requested.connect(
            self.home_requested.emit
        )
        self.sidebar.check_in_requested.connect(
            self.check_in_requested.emit
        )
        self.sidebar.logout_requested.connect(
            self.logout_requested.emit
        )

        self.sidebar.home_button.setProperty(
            "active",
            False,
        )
        self.sidebar.check_in_button.setProperty(
            "active",
            False,
        )
        self.sidebar.trends_button.setProperty(
            "active",
            True,
        )

        self._refresh_style(
            self.sidebar.home_button
        )
        self._refresh_style(
            self.sidebar.check_in_button
        )
        self._refresh_style(
            self.sidebar.trends_button
        )

        content = self._build_content()

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        root_layout.setSpacing(0)
        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(content, 1)

    def _build_content(self):
        content = QWidget()
        content.setObjectName("trendsPageContent")

        page_layout = QVBoxLayout(content)
        page_layout.setContentsMargins(
            38,
            22,
            38,
            26,
        )
        page_layout.setSpacing(14)

        page_layout.addLayout(
            self._build_header()
        )

        title = QLabel("Wellbeing history")
        title.setObjectName("trendsPageTitle")

        subtitle = QLabel(
            "Select a date to review the wellbeing "
            "summary saved for that check-in."
        )
        subtitle.setObjectName("trendsPageSubtitle")

        page_layout.addWidget(title)
        page_layout.addWidget(subtitle)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(18)

        left_column = QVBoxLayout()
        left_column.setContentsMargins(0, 0, 0, 0)
        left_column.setSpacing(18)
        left_column.addWidget(
            self._build_trend_graph_card()
        )
        left_column.addWidget(
            self._build_calendar_card()
        )

        body_layout.addLayout(left_column, 2)
        body_layout.addWidget(
            self._build_summary_panel(),
            3,
        )

        page_layout.addLayout(body_layout, 1)

        return content

    def _build_header(self):
        heart = QLabel("♥")
        heart.setObjectName("homeHeart")

        brand = QLabel("Solace")
        brand.setObjectName("homeBrand")

        self.user_label = QLabel()
        self.user_label.setObjectName("welcomeLabel")
        self.user_label.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(heart)
        layout.addWidget(brand)
        layout.addStretch()
        layout.addWidget(self.user_label)

        return layout

    def _build_trend_graph_card(self):
        card = QFrame()
        card.setObjectName("trendsGraphCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setMinimumWidth(335)
        card.setMaximumWidth(390)

        title = QLabel("This month's trend")
        title.setObjectName("trendsCardTitle")

        note = QLabel("Hover a point to see that check-in.")
        note.setObjectName("trendsCardNote")
        note.setWordWrap(True)

        self.trend_graph = MiniTrendGraph()

        self.trend_empty = QLabel(
            "Check in again to see the monthly trend."
        )
        self.trend_empty.setObjectName("trendRequirement")
        self.trend_empty.setWordWrap(True)
        self.trend_empty.setAlignment(Qt.AlignCenter)
        self.trend_empty.hide()

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(self.trend_graph, 1)
        layout.addWidget(self.trend_empty)

        return card

    def _build_calendar_card(self):
        card = QFrame()
        card.setObjectName("trendsCalendarCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )
        card.setMinimumWidth(335)
        card.setMaximumWidth(390)

        title = QLabel("Check-in calendar")
        title.setObjectName("trendsCardTitle")

        note = QLabel(
            "A grey dot marks a date with a saved check-in."
        )
        note.setObjectName("trendsCardNote")
        note.setWordWrap(True)

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
        self.calendar.setMaximumDate(
            QDate.currentDate()
        )
        self.calendar.setSelectedDate(
            QDate.currentDate()
        )
        self.calendar.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.calendar.currentPageChanged.connect(
            self._calendar_page_changed
        )
        self.calendar.selectionChanged.connect(
            self._selected_date_changed
        )

        legend_dot = QLabel("●")
        legend_dot.setObjectName("calendarLegendDot")
        legend_dot.setStyleSheet(
            "color: #9CA3AF; font-size: 11px;"
        )

        legend_text = QLabel("Saved check-in")
        legend_text.setObjectName("calendarLegendText")

        legend_layout = QHBoxLayout()
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(7)
        legend_layout.addWidget(legend_dot)
        legend_layout.addWidget(legend_text)
        legend_layout.addStretch()

        self._nav_syncing = False

        self.nav_prev = QPushButton("\u2039")
        self.nav_prev.setObjectName("calNavArrow")
        self.nav_prev.setFixedSize(34, 30)
        self.nav_prev.setCursor(Qt.PointingHandCursor)
        self.nav_prev.clicked.connect(self._go_prev_month)

        self.nav_next = QPushButton("\u203A")
        self.nav_next.setObjectName("calNavArrow")
        self.nav_next.setFixedSize(34, 30)
        self.nav_next.setCursor(Qt.PointingHandCursor)
        self.nav_next.clicked.connect(self._go_next_month)

        self.month_combo = QComboBox()
        self.month_combo.setObjectName("calNavCombo")
        self.month_combo.setCursor(Qt.PointingHandCursor)
        for month_name in [
            "January", "February", "March", "April",
            "May", "June", "July", "August",
            "September", "October", "November", "December",
        ]:
            self.month_combo.addItem(month_name)

        self.year_combo = QComboBox()
        self.year_combo.setObjectName("calNavCombo")
        self.year_combo.setCursor(Qt.PointingHandCursor)
        current_year = QDate.currentDate().year()
        for year_value in range(current_year - 10, current_year + 1):
            self.year_combo.addItem(str(year_value), year_value)

        today = QDate.currentDate()
        self.month_combo.setCurrentIndex(today.month() - 1)
        self.year_combo.setCurrentIndex(self.year_combo.count() - 1)

        self.month_combo.currentIndexChanged.connect(self._nav_changed)
        self.year_combo.currentIndexChanged.connect(self._nav_changed)

        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(6, 4, 6, 4)
        nav_layout.setSpacing(6)
        nav_layout.addWidget(self.nav_prev)
        nav_layout.addWidget(self.month_combo, 1)
        nav_layout.addWidget(self.year_combo, 1)
        nav_layout.addWidget(self.nav_next)

        nav_bar = QFrame()
        nav_bar.setObjectName("calNavBar")
        nav_bar.setAttribute(Qt.WA_StyledBackground, True)
        nav_bar.setLayout(nav_layout)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(note)
        layout.addWidget(nav_bar)
        layout.addWidget(self.calendar, 1)
        layout.addLayout(legend_layout)

        return card

    def _build_summary_panel(self):
        panel = QFrame()
        panel.setObjectName("historyPanel")
        panel.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        self.summary_stack = QStackedWidget()

        self.empty_state = self._build_empty_state()
        self.summary_state = self._build_summary_state()

        self.summary_stack.addWidget(
            self.empty_state
        )
        self.summary_stack.addWidget(
            self.summary_state
        )

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.summary_stack)

        return panel

    def _build_empty_state(self):
        page = QWidget()
        page.setObjectName("historyEmptyState")

        self.empty_date_label = QLabel(
            "Select a date"
        )
        self.empty_date_label.setObjectName(
            "historyEmptyTitle"
        )
        self.empty_date_label.setAlignment(
            Qt.AlignCenter
        )

        self.empty_message = QLabel(
            "Select a date with a grey dot to review "
            "a saved wellbeing summary."
        )
        self.empty_message.setObjectName(
            "historyEmptyMessage"
        )
        self.empty_message.setAlignment(
            Qt.AlignCenter
        )
        self.empty_message.setWordWrap(True)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(
            42,
            42,
            42,
            42,
        )
        layout.addStretch()
        layout.addWidget(self.empty_date_label)
        layout.addWidget(self.empty_message)
        layout.addStretch()

        return page

    def _build_summary_state(self):
        page = QWidget()
        page.setObjectName("historySummaryState")

        scroll = QScrollArea()
        scroll.setObjectName("historyScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_content = QWidget()
        scroll_content.setObjectName(
            "historyScrollContent"
        )

        content_layout = QVBoxLayout(
            scroll_content
        )
        content_layout.setContentsMargins(
            18,
            18,
            18,
            18,
        )
        content_layout.setSpacing(12)

        self.selected_date_label = QLabel()
        self.selected_date_label.setObjectName(
            "historySelectedDate"
        )

        self.selected_time_label = QLabel()
        self.selected_time_label.setObjectName(
            "historySelectedTime"
        )

        content_layout.addWidget(
            self.selected_date_label
        )
        content_layout.addWidget(
            self.selected_time_label
        )

        content_layout.addWidget(
            self._build_saved_summary_card()
        )
        content_layout.addWidget(
            self._build_transcript_history_card()
        )
        content_layout.addWidget(
            self._build_recommendation_history_card()
        )
        content_layout.addStretch()

        scroll.setWidget(scroll_content)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

        return page

    def _build_saved_summary_card(self):
        card = QFrame()
        card.setObjectName("historySummaryCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        self.history_image = QLabel()
        self.history_image.setObjectName(
            "historyResultImage"
        )
        self.history_image.setFixedSize(
            QSize(100, 100)
        )
        self.history_image.setAlignment(
            Qt.AlignCenter
        )

        self.history_phrase = QLabel()
        self.history_phrase.setObjectName(
            "historyPhrase"
        )
        self.history_phrase.setWordWrap(True)

        self.history_explanation = QLabel()
        self.history_explanation.setObjectName(
            "historyExplanation"
        )
        self.history_explanation.setWordWrap(True)

        self.history_progress = QProgressBar()
        self.history_progress.setObjectName(
            "trendHistoryProgress"
        )
        self.history_progress.setRange(0, 100)
        self.history_progress.setTextVisible(True)

        self.history_input_type = QLabel()
        self.history_input_type.setObjectName(
            "historyInputType"
        )

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(8)
        text_layout.addWidget(
            self.history_phrase
        )
        text_layout.addWidget(
            self.history_explanation
        )
        text_layout.addWidget(
            self.history_progress
        )
        text_layout.addWidget(
            self.history_input_type
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(
            20,
            18,
            20,
            18,
        )
        layout.setSpacing(18)
        layout.addWidget(
            self.history_image,
            0,
            Qt.AlignTop,
        )
        layout.addLayout(text_layout, 1)

        return card

    def _build_transcript_history_card(self):
        card = QFrame()
        card.setObjectName("historyDetailsCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        title = QLabel("Transcript")
        title.setObjectName("trendsCardTitle")

        self.history_transcript = QPlainTextEdit()
        self.history_transcript.setObjectName(
            "historyTranscript"
        )
        self.history_transcript.setReadOnly(True)
        self.history_transcript.setMinimumHeight(92)
        self.history_transcript.setMaximumHeight(125)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        layout.setSpacing(9)
        layout.addWidget(title)
        layout.addWidget(self.history_transcript)

        return card

    def _build_recommendation_history_card(self):
        card = QFrame()
        card.setObjectName("historyDetailsCard")
        card.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        title = QLabel(
            "Supportive recommendations"
        )
        title.setObjectName("trendsCardTitle")

        self.recommendation_container = QWidget()
        self.recommendation_container.setObjectName(
            "historyRecommendationContainer"
        )

        self.recommendation_layout = QVBoxLayout(
            self.recommendation_container
        )
        self.recommendation_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.recommendation_layout.setSpacing(8)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(
            18,
            16,
            18,
            16,
        )
        layout.setSpacing(9)
        layout.addWidget(title)
        layout.addWidget(
            self.recommendation_container
        )

        return card

    def set_user(
        self,
        full_name,
        user_id=None,
    ):
        first_name = (
            full_name.split()[0]
            if full_name
            else ""
        )

        self.user_label.setText(first_name)
        self.user_id = user_id

    def refresh_page(self):
        today = QDate.currentDate()

        self.calendar.setCurrentPage(
            today.year(),
            today.month(),
        )
        self.calendar.setSelectedDate(today)

        self._load_month_markers(
            today.year(),
            today.month(),
        )
        self._load_selected_date()
        self._load_trend_graph()

    def _load_trend_graph(self):
        if self.user_id is None:
            self.trend_graph.hide()
            self.trend_empty.show()
            return

        points = get_month_check_ins(
            self.user_id,
            31,
        )

        if len(points) < 2:
            self.trend_graph.hide()
            self.trend_empty.show()
        else:
            self.trend_empty.hide()
            self.trend_graph.set_points(points)
            self.trend_graph.show()

    def _nav_changed(self, *_):
        if self._nav_syncing:
            return
        year = self.year_combo.currentData()
        month = self.month_combo.currentIndex() + 1
        if year is None:
            return
        self.calendar.setCurrentPage(year, month)

    def _go_prev_month(self):
        shown = QDate(
            self.calendar.yearShown(),
            self.calendar.monthShown(),
            1,
        ).addMonths(-1)
        self.calendar.setCurrentPage(shown.year(), shown.month())

    def _go_next_month(self):
        shown = QDate(
            self.calendar.yearShown(),
            self.calendar.monthShown(),
            1,
        ).addMonths(1)
        if shown > QDate.currentDate():
            return
        self.calendar.setCurrentPage(shown.year(), shown.month())

    def _sync_nav(self, year, month):
        self._nav_syncing = True
        self.month_combo.setCurrentIndex(month - 1)
        year_index = self.year_combo.findData(year)
        if year_index >= 0:
            self.year_combo.setCurrentIndex(year_index)
        self.nav_next.setEnabled(
            QDate(year, month, 1).addMonths(1)
            <= QDate.currentDate()
        )
        self._nav_syncing = False

    def _calendar_page_changed(
        self,
        year,
        month,
    ):
        self._load_month_markers(
            year,
            month,
        )
        self._sync_nav(year, month)

    def _selected_date_changed(self):
        self._load_selected_date()

    def _load_month_markers(
        self,
        year,
        month,
    ):
        if self.user_id is None:
            self.calendar.set_saved_dates([])
            return

        date_strings = get_check_in_dates(
            self.user_id,
            year,
            month,
        )

        saved_dates = []

        for date_text in date_strings:
            saved_date = QDate.fromString(
                date_text,
                "yyyy-MM-dd",
            )

            if saved_date.isValid():
                saved_dates.append(saved_date)

        self.calendar.set_saved_dates(
            saved_dates
        )

    def _load_selected_date(self):
        selected_date = (
            self.calendar.selectedDate()
        )

        formatted_date = selected_date.toString(
            "dddd, d MMMM yyyy"
        )

        if self.user_id is None:
            self._show_empty(
                formatted_date,
                "No signed-in user was found.",
            )
            return

        check_in = get_check_in_for_date(
            self.user_id,
            selected_date.toString(
                "yyyy-MM-dd"
            ),
        )

        if check_in is None:
            self._show_empty(
                formatted_date,
                "No check-in was completed "
                "on this date.",
            )
            return

        self._show_check_in(
            formatted_date,
            check_in,
        )

    def _show_empty(
        self,
        date_text,
        message,
    ):
        self.empty_date_label.setText(
            date_text
        )
        self.empty_message.setText(message)
        self.summary_stack.setCurrentWidget(
            self.empty_state
        )

    def _show_check_in(
        self,
        formatted_date,
        check_in,
    ):
        self.selected_date_label.setText(
            formatted_date
        )

        time_text = str(
            check_in.get(
                "created_at_local",
                "",
            )
        )

        display_time = (
            time_text[11:16]
            if len(time_text) >= 16
            else ""
        )

        input_type = str(
            check_in.get(
                "input_type",
                "",
            )
        ).capitalize()

        self.selected_time_label.setText(
            f"Latest check-in at {display_time}"
        )

        score = int(
            round(
                float(
                    check_in.get(
                        "wellbeing_score",
                        0,
                    )
                )
            )
        )

        self.history_phrase.setText(
            check_in.get(
                "summary",
                "Wellbeing summary",
            )
        )

        self.history_explanation.setText(
            check_in.get(
                "explanation",
                "",
            )
            or "No explanation was saved."
        )

        self.history_progress.setValue(score)
        self.history_progress.setFormat(
            f"{score} / 100"
        )

        zone = self._score_zone(score)
        self.history_progress.setProperty(
            "zone",
            zone,
        )
        self._refresh_style(
            self.history_progress
        )

        self.history_input_type.setText(
            f"Input used: {input_type}"
        )

        self._set_result_image(
            check_in.get("image_name"),
            score,
            check_in.get("summary", ""),
        )

        self.history_transcript.setPlainText(
            check_in.get(
                "transcript",
                "",
            )
            or "No transcript was saved."
        )

        self._set_recommendations(
            check_in.get(
                "recommendation",
                "",
            )
        )

        self.summary_stack.setCurrentWidget(
            self.summary_state
        )

    def _set_result_image(
        self,
        image_name,
        score,
        phrase,
    ):
        selected_name = image_name

        if not selected_name:
            phrase_text = (
                phrase or ""
            ).lower()

            if (
                "forward" in phrase_text
                or "improv" in phrase_text
                or score >= 67
            ):
                selected_name = (
                    "wellbeing_high.png"
                )
            elif (
                "closer look" in phrase_text
                or "care" in phrase_text
                or score < 34
            ):
                selected_name = (
                    "wellbeing_low.png"
                )
            else:
                selected_name = (
                    "wellbeing_mid.png"
                )

        pixmap = QPixmap(
            str(IMAGES_FOLDER / selected_name)
        )

        if pixmap.isNull():
            self.history_image.clear()
            return

        self.history_image.setPixmap(
            pixmap.scaled(
                88,
                88,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def _set_recommendations(
        self,
        recommendation_text,
    ):
        while self.recommendation_layout.count():
            item = (
                self.recommendation_layout
                .takeAt(0)
            )

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

        lines = [
            line.strip()
            for line in (
                recommendation_text or ""
            ).splitlines()
            if line.strip()
        ]

        if not lines:
            lines = [
                "No recommendation was saved "
                "for this check-in."
            ]

        for line in lines:
            cleaned_line = re.sub(
                r"^\s*(?:\d+[\.\)]|[-•])\s*",
                "",
                line,
            )

            recommendation = QLabel(
                cleaned_line
            )
            recommendation.setObjectName(
                "historyRecommendationItem"
            )
            recommendation.setWordWrap(True)
            recommendation.setAlignment(
                Qt.AlignLeft
                | Qt.AlignVCenter
            )

            self.recommendation_layout.addWidget(
                recommendation
            )

    def _score_zone(self, score):
        if score >= 67:
            return "high"

        if score >= 34:
            return "mid"

        return "low"

    def _refresh_style(self, widget):
        widget.style().unpolish(widget)
        widget.style().polish(widget)