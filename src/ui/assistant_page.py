from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QFontMetrics, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ai.solace_agent import SolaceAgent
from src.ui.home_page import HoverSidebar
from src.ui.translations import (
    ENGLISH_TEXT,
    get_text,
)


# --------------------------------------------------
# Translation text
# --------------------------------------------------

ASSISTANT_TEXT = {
    "assistant": "Assistant",

    "assistant_title":
        "Solace Assistant",

    "assistant_subtitle":
        "Ask about Solace or your saved wellbeing history.",

    "assistant_private":
        "Private by design — the Assistant only reads your locally saved Solace information.",

    "assistant_welcome":
        "Hi! I can explain how Solace works or help you understand "
        "your saved wellbeing history.",

    "assistant_disclaimer":
        "Solace is an experimental wellbeing support tool and does not "
        "provide medical diagnoses.",

    "assistant_placeholder":
        "Ask Solace a question...",

    "assistant_send":
        "Send",

    "assistant_clear":
        "Clear chat",

    "assistant_thinking":
        "Solace AI is thinking...",

    "assistant_error":
        "I could not answer that question. Please try again.",

    "assistant_suggestions":
        "Suggested questions",

    "assistant_suggestion_help":
        "How does Solace work?",

    "assistant_suggestion_latest":
        "What was my latest wellbeing score?",

    "assistant_suggestion_trend":
        "How have my recent scores changed?",

    "assistant_information_used":
        "Information used",

    "assistant_tool_solace_help":
        "Solace help",

    "assistant_tool_latest_check_in":
        "Latest check-in",

    "assistant_tool_recent_scores":
        "Recent scores",

    "assistant_tool_wellbeing_context":
        "Wellbeing context",

    "assistant_tool_recent_history":
        "Recent history",

    "assistant_tool_date_check_in":
        "Dated check-in",

    "assistant_tool_check_in_count":
        "Check-in count",

    "assistant_tool_safety_support":
        "Safety support",

    "assistant_tool_general":
        "General conversation",
}

ENGLISH_TEXT.update(
    ASSISTANT_TEXT
)


TOOL_TEXT_KEYS = {
    "solace_help":
        "assistant_tool_solace_help",

    "latest_check_in":
        "assistant_tool_latest_check_in",

    "recent_scores":
        "assistant_tool_recent_scores",

    "wellbeing_context":
        "assistant_tool_wellbeing_context",

    "recent_history":
        "assistant_tool_recent_history",

    "date_check_in":
        "assistant_tool_date_check_in",

    "check_in_count":
        "assistant_tool_check_in_count",

    "safety_support":
        "assistant_tool_safety_support",

    "general":
        "assistant_tool_general",
}


# --------------------------------------------------
# Background worker
# --------------------------------------------------

class AssistantWorker(QThread):
    completed = Signal(dict)
    failed = Signal(str)

    def __init__(
        self,
        question,
        user_id,
        language_name,
        history,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.question = question
        self.user_id = user_id
        self.language_name = (
            language_name
        )

        self.history = list(
            history
        )

    def run(self):
        try:
            agent = SolaceAgent(
                user_id=self.user_id,
                language_name=(
                    self.language_name
                ),
            )

            result = agent.answer(
                self.question,
                self.history,
            )

            self.completed.emit(
                result
            )

        except Exception as error:
            self.failed.emit(
                str(error)
            )


# --------------------------------------------------
# Assistant page
# --------------------------------------------------

class AssistantPage(QWidget):
    home_requested = Signal()
    check_in_requested = Signal()
    trends_requested = Signal()
    settings_requested = Signal()
    logout_requested = Signal()

    def __init__(self):
        super().__init__()

        self.current_language = (
            "English"
        )

        self.user_id = None
        self.first_name = ""

        # Short conversation memory only.
        # Chat messages are not stored in SQLite.
        self.history = []

        self.worker = None

        self.sidebar = HoverSidebar()

        self.sidebar.home_requested.connect(
            self.home_requested.emit
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

        self.sidebar.logout_requested.connect(
            self.logout_requested.emit
        )

        self.set_active_sidebar()

        content = self.build_content()

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        layout.setSpacing(
            0
        )

        layout.addWidget(
            self.sidebar
        )

        layout.addWidget(
            content,
            1,
        )

        self.set_language(
            "English"
        )

        self.clear_chat()

    # --------------------------------------------------
    # Translation
    # --------------------------------------------------

    def t(
        self,
        key,
    ):
        return get_text(
            self.current_language,
            key,
        )

    def set_language(
        self,
        language,
    ):
        previous_language = (
            self.current_language
        )

        self.current_language = (
            language
        )

        self.sidebar.set_language(
            language
        )

        self.title.setText(
            self.t(
                "assistant_title"
            )
        )

        self.subtitle.setText(
            self.t(
                "assistant_subtitle"
            )
        )

        self.private_note.setText(
            self.t(
                "assistant_private"
            )
        )

        self.suggestions_title.setText(
            self.t(
                "assistant_suggestions"
            )
        )

        self.help_button.setText(
            self.t(
                "assistant_suggestion_help"
            )
        )

        self.latest_button.setText(
            self.t(
                "assistant_suggestion_latest"
            )
        )

        self.trend_button.setText(
            self.t(
                "assistant_suggestion_trend"
            )
        )

        self.question_input.setPlaceholderText(
            self.t(
                "assistant_placeholder"
            )
        )

        self.send_button.setText(
            self.t(
                "assistant_send"
            )
        )

        self.clear_button.setText(
            self.t(
                "assistant_clear"
            )
        )

        self.disclaimer.setText(
            self.t(
                "assistant_disclaimer"
            )
        )

        # If the user changes language,
        # start a fresh short chat so old and
        # new language messages are not mixed.
        if (
            previous_language
            != language
            and self.history
            and not self.worker_running()
        ):
            self.clear_chat()

        self.tamil_fonts()

    def tamil_fonts(self):
        tamil = (
            self.current_language
            == "Tamil"
        )

        widgets = [
            (
                self.title,
                19,
            ),
            (
                self.subtitle,
                10,
            ),
            (
                self.private_note,
                9,
            ),
            (
                self.suggestions_title,
                10,
            ),
            (
                self.help_button,
                9,
            ),
            (
                self.latest_button,
                9,
            ),
            (
                self.trend_button,
                9,
            ),
            (
                self.question_input,
                10,
            ),
            (
                self.send_button,
                10,
            ),
            (
                self.clear_button,
                9,
            ),
            (
                self.disclaimer,
                9,
            ),
        ]

        for widget, size in widgets:
            widget.setStyleSheet(
                f"font-size:{size}px;"
                if tamil
                else ""
            )

    # --------------------------------------------------
    # User
    # --------------------------------------------------

    def set_user(
        self,
        full_name,
        user_id=None,
    ):
        changed_user = (
            self.user_id
            is not None
            and self.user_id
            != user_id
        )

        self.user_id = user_id

        self.first_name = (
            full_name.split()[0]
            if full_name
            else ""
        )

        # Keep the top header identical to the rest of Solace.
        if hasattr(self, "user_label"):
            self.user_label.setText(
                self.first_name
            )

        if (
            changed_user
            and not self.worker_running()
        ):
            self.clear_chat()

    # --------------------------------------------------
    # Active sidebar
    # --------------------------------------------------

    def set_active_sidebar(self):
        buttons = [
            self.sidebar.home_button,
            self.sidebar.check_in_button,
            self.sidebar.trends_button,
            self.sidebar.settings_button,
        ]

        assistant_button = getattr(
            self.sidebar,
            "assistant_button",
            None,
        )

        if assistant_button:
            buttons.append(
                assistant_button
            )

        for button in buttons:
            button.setProperty(
                "active",
                False,
            )

        if assistant_button:
            assistant_button.setProperty(
                "active",
                True,
            )

        for button in buttons:
            button.style().unpolish(
                button
            )

            button.style().polish(
                button
            )

    # --------------------------------------------------
    # Main content
    # --------------------------------------------------

    def build_content(self):
        content = QWidget()
        content.setObjectName(
            "assistantContent"
        )
        content.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        self.title = QLabel(
            "Solace Assistant"
        )
        self.title.setObjectName(
            "assistantTitle"
        )

        self.subtitle = QLabel(
            "Ask about Solace or your saved wellbeing history."
        )
        self.subtitle.setObjectName(
            "assistantSubtitle"
        )
        self.subtitle.setWordWrap(
            True
        )

        self.private_note = QLabel(
            "Private by design — the Assistant only reads your locally saved Solace information."
        )
        self.private_note.setObjectName(
            "assistantPrivateNote"
        )
        self.private_note.setWordWrap(
            True
        )

        self.clear_button = QPushButton(
            "Clear chat"
        )
        self.clear_button.setObjectName(
            "assistantClearButton"
        )
        self.clear_button.setCursor(
            Qt.PointingHandCursor
        )
        self.clear_button.setFixedHeight(
            38
        )
        self.clear_button.clicked.connect(
            self.clear_chat
        )

        hero = QFrame()
        hero.setObjectName(
            "assistantHeroCard"
        )
        hero.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )
        hero.setMinimumHeight(
            124
        )

        hero_text = QVBoxLayout()
        hero_text.setContentsMargins(
            0, 0, 0, 0
        )
        hero_text.setSpacing(
            5
        )
        hero_text.addWidget(
            self.title
        )
        hero_text.addWidget(
            self.subtitle
        )
        hero_text.addWidget(
            self.private_note
        )

        hero_layout = QHBoxLayout(
            hero
        )
        hero_layout.setContentsMargins(
            28,
            20,
            24,
            20,
        )
        hero_layout.setSpacing(
            20
        )
        hero_layout.addLayout(
            hero_text,
            1,
        )
        hero_layout.addWidget(
            self.clear_button,
            0,
            Qt.AlignTop,
        )

        self.disclaimer = QLabel(
            "Solace is an experimental wellbeing support tool and does not "
            "provide medical diagnoses."
        )
        self.disclaimer.setObjectName(
            "assistantDisclaimer"
        )
        self.disclaimer.setAlignment(
            Qt.AlignCenter
        )
        self.disclaimer.setWordWrap(
            True
        )

        self.status_label = QLabel(
            ""
        )
        self.status_label.setObjectName(
            "assistantStatus"
        )
        self.status_label.setAlignment(
            Qt.AlignCenter
        )
        self.status_label.hide()

        layout = QVBoxLayout(
            content
        )
        layout.setContentsMargins(
            38,
            22,
            38,
            22,
        )
        layout.setSpacing(
            12
        )

        layout.addLayout(
            self.build_header()
        )
        layout.addSpacing(
            2
        )
        layout.addWidget(
            hero
        )
        layout.addWidget(
            self.build_chat_area(),
            1,
        )
        layout.addLayout(
            self.build_suggestions()
        )
        layout.addWidget(
            self.build_input()
        )
        # Thinking feedback is shown inside the chat instead of as a
        # separate status strip below the composer.
        layout.addWidget(
            self.disclaimer
        )

        return content

    # --------------------------------------------------
    # Header
    # --------------------------------------------------

    def build_header(self):
        heart = QLabel()
        heart.setFixedSize(
            30,
            30,
        )
        heart.setAlignment(
            Qt.AlignCenter
        )

        from pathlib import Path

        root = (
            Path(__file__)
            .resolve()
            .parents[2]
        )

        image_path = (
            root
            / "src"
            / "images"
            / "heart.png"
        )

        heart.setPixmap(
            QPixmap(
                str(image_path)
            ).scaled(
                28,
                28,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

        brand = QLabel(
            "Solace"
        )
        # Re-use the exact same style as Home, Trends and Settings.
        brand.setObjectName(
            "homeBrand"
        )

        self.user_label = QLabel(
            self.first_name
        )
        self.user_label.setObjectName(
            "welcomeLabel"
        )
        self.user_label.setAlignment(
            Qt.AlignRight
            | Qt.AlignVCenter
        )

        row = QHBoxLayout()
        row.setSpacing(
            7
        )
        row.addWidget(
            heart
        )
        row.addWidget(
            brand
        )
        row.addStretch()
        row.addWidget(
            self.user_label
        )

        return row

    # --------------------------------------------------
    # Chat area
    # --------------------------------------------------

    def build_chat_area(self):
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setObjectName(
            "assistantChatScroll"
        )
        self.chat_scroll.setWidgetResizable(
            True
        )
        self.chat_scroll.setFrameShape(
            QFrame.NoFrame
        )
        self.chat_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )

        self.chat_container = QWidget()
        self.chat_container.setObjectName(
            "assistantChatContainer"
        )

        self.chat_layout = QVBoxLayout(
            self.chat_container
        )
        self.chat_layout.setContentsMargins(
            20,
            20,
            20,
            20,
        )
        self.chat_layout.setSpacing(
            12
        )
        self.chat_layout.addStretch()

        self.chat_scroll.setWidget(
            self.chat_container
        )
        self.chat_scroll.setMinimumHeight(
            320
        )

        return self.chat_scroll

    # --------------------------------------------------
    # Suggested questions
    # --------------------------------------------------

    def build_suggestions(self):
        layout = QVBoxLayout()

        layout.setSpacing(
            7
        )

        self.suggestions_title = QLabel(
            "Suggested questions"
        )

        self.suggestions_title.setObjectName(
            "assistantSuggestionsTitle"
        )

        layout.addWidget(
            self.suggestions_title
        )

        buttons = QHBoxLayout()

        buttons.setSpacing(
            8
        )

        self.help_button = (
            self.make_suggestion_button(
                "How does Solace work?"
            )
        )

        self.latest_button = (
            self.make_suggestion_button(
                "What was my latest wellbeing score?"
            )
        )

        self.trend_button = (
            self.make_suggestion_button(
                "How have my recent scores changed?"
            )
        )

        self.help_button.clicked.connect(
            lambda:
            self.ask_suggestion(
                self.t(
                    "assistant_suggestion_help"
                )
            )
        )

        self.latest_button.clicked.connect(
            lambda:
            self.ask_suggestion(
                self.t(
                    "assistant_suggestion_latest"
                )
            )
        )

        self.trend_button.clicked.connect(
            lambda:
            self.ask_suggestion(
                self.t(
                    "assistant_suggestion_trend"
                )
            )
        )

        buttons.addWidget(
            self.help_button
        )

        buttons.addWidget(
            self.latest_button
        )

        buttons.addWidget(
            self.trend_button
        )

        layout.addLayout(
            buttons
        )

        return layout

    def make_suggestion_button(
        self,
        text,
    ):
        button = QPushButton(
            text
        )

        button.setObjectName(
            "assistantSuggestionButton"
        )

        button.setCursor(
            Qt.PointingHandCursor
        )

        button.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        return button

    # --------------------------------------------------
    # Question input
    # --------------------------------------------------

    def build_input(self):
        composer = QFrame()
        composer.setObjectName(
            "assistantComposer"
        )
        composer.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )

        layout = QHBoxLayout(
            composer
        )
        layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )
        layout.setSpacing(
            9
        )

        self.question_input = QLineEdit()
        self.question_input.setObjectName(
            "assistantQuestionInput"
        )
        self.question_input.setPlaceholderText(
            "Ask Solace a question..."
        )
        self.question_input.setClearButtonEnabled(
            True
        )
        self.question_input.setFixedHeight(
            44
        )
        self.question_input.returnPressed.connect(
            self.send_question
        )

        self.send_button = QPushButton(
            "Send"
        )
        self.send_button.setObjectName(
            "assistantSendButton"
        )
        self.send_button.setCursor(
            Qt.PointingHandCursor
        )
        self.send_button.setFixedSize(
            112,
            44,
        )
        self.send_button.clicked.connect(
            self.send_question
        )

        layout.addWidget(
            self.question_input,
            1,
        )
        layout.addWidget(
            self.send_button
        )

        return composer

    # --------------------------------------------------
    # Chat messages
    # --------------------------------------------------

    def add_message(
        self,
        text,
        role,
        tool=None,
    ):
        frame = QFrame()
        frame.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )
        frame.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Maximum,
        )

        if role == "user":
            frame.setObjectName(
                "assistantUserMessage"
            )
        else:
            frame.setObjectName(
                "assistantBotMessage"
            )

        message = QLabel(
            str(text)
        )
        # Keep user input literal, but render the assistant's Markdown
        # so bold text and lists look clean instead of showing ** markers.
        message.setTextFormat(
            Qt.PlainText
            if role == "user"
            else Qt.MarkdownText
        )
        message.setWordWrap(
            True
        )
        message.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        message.setObjectName(
            "assistantUserMessageText"
            if role == "user"
            else "assistantBotMessageText"
        )
        message.setMaximumWidth(
            620
            if role == "user"
            else 720
        )
        message.setSizePolicy(
            QSizePolicy.Preferred,
            QSizePolicy.Preferred,
        )

        bubble_layout = QVBoxLayout(
            frame
        )
        bubble_layout.setContentsMargins(
            16,
            11,
            16,
            11,
        )
        bubble_layout.setSpacing(
            7
        )
        bubble_layout.addWidget(
            message
        )

        if (
            role == "assistant"
            and tool
            and tool in TOOL_TEXT_KEYS
        ):
            tool_label = QLabel(
                (
                    f"{self.t('assistant_information_used')}: "
                    f"{self.t(TOOL_TEXT_KEYS[tool])}"
                )
            )
            tool_label.setObjectName(
                "assistantToolLabel"
            )
            bubble_layout.addWidget(
                tool_label
            )

        row_widget = QWidget()
        row_widget.setObjectName(
            "assistantMessageRow"
        )
        row_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum,
        )

        row = QHBoxLayout(
            row_widget
        )
        row.setContentsMargins(
            2,
            0,
            2,
            0,
        )
        row.setSpacing(
            0
        )

        if role == "user":
            row.addStretch(
                1
            )
            row.addWidget(
                frame,
                0,
                Qt.AlignRight
                | Qt.AlignTop,
            )
            # Size user bubbles to the message instead of forcing every
            # short message into the same wide pill. This keeps questions
            # such as "How does Solace work?" on one line, while a tiny
            # message such as "hi" stays compact.
            metrics = QFontMetrics(
                message.font()
            )
            longest_line = max(
                (
                    metrics.horizontalAdvance(line)
                    for line in str(text).splitlines()
                ),
                default=0,
            )
            bubble_width = min(
                max(longest_line + 44, 72),
                660,
            )
            frame.setFixedWidth(
                bubble_width
            )
        else:
            row.addWidget(
                frame,
                0,
                Qt.AlignLeft
                | Qt.AlignTop,
            )
            row.addStretch(
                1
            )
            # Assistant bubbles also start wider for easier reading while
            # still expanding naturally for longer answers.
            frame.setMinimumWidth(
                390
            )
            frame.setMaximumWidth(
                760
            )

        # Insert immediately before the bottom stretch.
        self.chat_layout.insertWidget(
            self.chat_layout.count() - 1,
            row_widget,
        )

        QTimer.singleShot(
            0,
            self.scroll_to_bottom,
        )

        return row_widget

    def add_thinking_message(self):
        # Remove any stale indicator first.
        self.remove_thinking_message()

        frame = QFrame()
        frame.setObjectName(
            "assistantThinkingMessage"
        )
        frame.setAttribute(
            Qt.WA_StyledBackground,
            True,
        )
        frame.setMinimumWidth(
            230
        )
        frame.setMaximumWidth(
            320
        )

        text = QLabel(
            self.t(
                "assistant_thinking"
            )
        )
        text.setObjectName(
            "assistantThinkingText"
        )
        text.setWordWrap(
            False
        )

        bubble_layout = QVBoxLayout(
            frame
        )
        bubble_layout.setContentsMargins(
            16,
            10,
            16,
            10,
        )
        bubble_layout.addWidget(
            text
        )

        row_widget = QWidget()
        row_widget.setObjectName(
            "assistantMessageRow"
        )
        row_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum,
        )

        row = QHBoxLayout(
            row_widget
        )
        row.setContentsMargins(
            2,
            0,
            2,
            0,
        )
        row.addWidget(
            frame,
            0,
            Qt.AlignLeft
            | Qt.AlignTop,
        )
        row.addStretch(
            1
        )

        self.chat_layout.insertWidget(
            self.chat_layout.count() - 1,
            row_widget,
        )
        self.thinking_row = row_widget

        QTimer.singleShot(
            0,
            self.scroll_to_bottom,
        )

    def remove_thinking_message(self):
        row_widget = getattr(
            self,
            "thinking_row",
            None,
        )

        if row_widget is None:
            return

        self.chat_layout.removeWidget(
            row_widget
        )
        row_widget.setParent(
            None
        )
        row_widget.deleteLater()
        self.thinking_row = None

    def add_welcome_message(self):
        return self.add_message(
            self.t(
                "assistant_welcome"
            ),
            "assistant",
        )

    # --------------------------------------------------
    # Clear chat
    # --------------------------------------------------

    def clear_chat(self):
        if self.worker_running():
            return

        self.history = []

        while (
            self.chat_layout.count()
            > 1
        ):
            item = (
                self.chat_layout
                .takeAt(0)
            )

            widget = (
                item.widget()
            )

            if widget:
                widget.deleteLater()

        self.add_welcome_message()

        self.status_message(
            ""
        )

    # --------------------------------------------------
    # Suggested question
    # --------------------------------------------------

    def ask_suggestion(
        self,
        question,
    ):
        if self.worker_running():
            return

        self.question_input.setText(
            question
        )

        self.send_question()

    # --------------------------------------------------
    # Send
    # --------------------------------------------------

    def send_question(self):
        if self.worker_running():
            return

        question = (
            self.question_input
            .text()
            .strip()
        )

        if not question:
            return

        # History passed to the agent contains
        # only the conversation before this question.
        previous_history = list(
            self.history
        )

        self.add_message(
            question,
            "user",
        )

        self.history.append(
            {
                "role": "user",
                "content": question,
            }
        )

        self.trim_history()

        self.question_input.clear()

        self.set_busy(
            True
        )

        self.add_thinking_message()

        self.worker = AssistantWorker(
            question,
            self.user_id,
            self.current_language,
            previous_history,
            self,
        )

        self.worker.completed.connect(
            self.answer_ready
        )

        self.worker.failed.connect(
            self.answer_failed
        )

        self.worker.finished.connect(
            self.worker_finished
        )

        self.worker.start()

    # --------------------------------------------------
    # Agent completed
    # --------------------------------------------------

    def answer_ready(
        self,
        result,
    ):
        answer = str(
            result.get(
                "answer",
                "",
            )
        ).strip()

        tool = result.get(
            "tool"
        )

        if not answer:
            answer = self.t(
                "assistant_error"
            )

        self.remove_thinking_message()

        self.add_message(
            answer,
            "assistant",
            tool,
        )

        self.history.append(
            {
                "role": "assistant",
                "content": answer,
            }
        )

        self.trim_history()

        self.status_message(
            ""
        )

    # --------------------------------------------------
    # Agent failed
    # --------------------------------------------------

    def answer_failed(
        self,
        message,
    ):
        print(
            "ASSISTANT ERROR:",
            message,
        )

        error_text = self.t(
            "assistant_error"
        )

        self.remove_thinking_message()

        self.add_message(
            error_text,
            "assistant",
        )

        self.history.append(
            {
                "role": "assistant",
                "content": error_text,
            }
        )

        self.trim_history()

        self.status_message(
            ""
        )

    # --------------------------------------------------
    # Worker finished
    # --------------------------------------------------

    def worker_finished(self):
        self.set_busy(
            False
        )

        worker = (
            self.worker
        )

        self.worker = None

        if worker:
            worker.deleteLater()

        self.question_input.setFocus()

    # --------------------------------------------------
    # Busy state
    # --------------------------------------------------

    def worker_running(self):
        return (
            self.worker is not None
            and self.worker.isRunning()
        )

    def set_busy(
        self,
        busy,
    ):
        enabled = not busy

        self.sidebar.setEnabled(enabled)

        self.question_input.setEnabled(
            enabled
        )

        self.send_button.setEnabled(
            enabled
        )

        self.clear_button.setEnabled(
            enabled
        )

        self.help_button.setEnabled(
            enabled
        )

        self.latest_button.setEnabled(
            enabled
        )

        self.trend_button.setEnabled(
            enabled
        )

        # Suggested questions are useful when idle, but hiding them while
        # the agent is working keeps the focus on the active conversation.
        suggestions_visible = not busy
        self.suggestions_title.setVisible(
            suggestions_visible
        )
        self.help_button.setVisible(
            suggestions_visible
        )
        self.latest_button.setVisible(
            suggestions_visible
        )
        self.trend_button.setVisible(
            suggestions_visible
        )

    # --------------------------------------------------
    # Short memory
    # --------------------------------------------------

    def trim_history(self):
        self.history = (
            self.history[-10:]
        )

    # --------------------------------------------------
    # Status
    # --------------------------------------------------

    def status_message(
        self,
        text,
    ):
        # Kept for existing calls such as clear_chat(), but status feedback
        # is now presented in the chat itself.
        self.status_label.setText(
            text
        )
        self.status_label.hide()

    # --------------------------------------------------
    # Scroll
    # --------------------------------------------------

    def scroll_to_bottom(self):
        bar = (
            self.chat_scroll
            .verticalScrollBar()
        )

        bar.setValue(
            bar.maximum()
        )

    # --------------------------------------------------
    # Show / refresh
    # --------------------------------------------------

    def refresh_page(self):
        self.set_active_sidebar()

        if not self.worker_running():
            self.question_input.setFocus()