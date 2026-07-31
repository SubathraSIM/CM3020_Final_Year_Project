from PySide6.QtCore import (
    Qt,
    QPointF,
    QRectF,
    QPropertyAnimation,
    QEasingCurve,
    QTimer
)

from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPen,
    QPolygonF,
    QPainterPath
)

from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget
)


class EcgMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._phase = 0.0

        self.setAttribute(
            Qt.WA_TransparentForMouseEvents,
            True
        )

        self._timer = QTimer(self)
        self._timer.timeout.connect(
            self._tick
        )
        self._timer.start(33)

    def _tick(self):
        self._phase += 0.006

        if self._phase > 1.0:
            self._phase -= 1.0

        self.update()

    def _beat(self, beat_position):
        points = [
            (0.00, 0.0),
            (0.10, 0.0),
            (0.16, 0.12),
            (0.22, 0.0),
            (0.30, 0.0),
            (0.33, -0.10),
            (0.37, 1.0),
            (0.41, -0.50),
            (0.45, 0.0),
            (0.58, 0.22),
            (0.66, 0.0),
            (1.00, 0.0)
        ]

        for index in range(
            len(points) - 1
        ):
            x0, y0 = points[index]
            x1, y1 = points[index + 1]

            if x0 <= beat_position <= x1:
                distance = x1 - x0

                if distance == 0:
                    return y0

                position = (
                    beat_position - x0
                ) / distance

                return (
                    y0
                    + (y1 - y0) * position
                )

        return 0.0

    def paintEvent(self, event):
        width = self.width()
        height = self.height()

        if width < 4 or height < 4:
            return

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.Antialiasing,
            True
        )

        radius = 24.0

        shape = QPainterPath()

        shape.addRoundedRect(
            QRectF(
                0,
                0,
                width,
                height
            ),
            radius,
            radius
        )

        square_right = QPainterPath()

        square_right.addRect(
            QRectF(
                width * 0.5,
                0,
                width * 0.5,
                height
            )
        )

        shape = shape.united(
            square_right
        )

        painter.setClipPath(shape)

        background = QColor("#05080B")
        painter.fillPath(
            shape,
            background
        )

        grid_colour = QColor(
            56,
            189,
            248
        )

        grid_colour.setAlpha(20)

        painter.setPen(
            QPen(
                grid_colour,
                1
            )
        )

        grid_step = 28

        grid_x = 0

        while grid_x <= width:
            painter.drawLine(
                grid_x,
                0,
                grid_x,
                height
            )

            grid_x += grid_step

        grid_y = 0

        while grid_y <= height:
            painter.drawLine(
                0,
                grid_y,
                width,
                grid_y
            )

            grid_y += grid_step

        middle = height * 0.5
        amplitude = height * 0.30
        beat_width = width / 3.0

        trace_points = []

        x_position = 0

        while x_position <= width:
            beat_position = (
                x_position / beat_width
            ) % 1.0

            y_position = (
                middle
                - self._beat(
                    beat_position
                ) * amplitude
            )

            trace_points.append(
                QPointF(
                    x_position,
                    y_position
                )
            )

            x_position += 3

        dim_pen = QPen(
            QColor(
                255,
                255,
                255,
                45
            )
        )

        dim_pen.setWidthF(1.6)
        dim_pen.setCapStyle(
            Qt.RoundCap
        )
        dim_pen.setJoinStyle(
            Qt.RoundJoin
        )

        painter.setPen(dim_pen)

        painter.drawPolyline(
            QPolygonF(trace_points)
        )

        head = self._phase * width

        painter.fillRect(
            QRectF(
                head,
                0,
                width * 0.045,
                height
            ),
            background
        )

        trail_length = width * 0.16

        bright_points = [
            point
            for point in trace_points
            if (
                head - trail_length
                <= point.x()
                <= head
            )
        ]

        if len(bright_points) < 2:
            return

        bright_line = QPolygonF(
            bright_points
        )

        glow_pen = QPen(
            QColor(
                56,
                189,
                248,
                90
            )
        )

        glow_pen.setWidthF(6.0)
        glow_pen.setCapStyle(
            Qt.RoundCap
        )
        glow_pen.setJoinStyle(
            Qt.RoundJoin
        )

        painter.setPen(glow_pen)
        painter.drawPolyline(
            bright_line
        )

        core_pen = QPen(
            QColor(
                255,
                255,
                255,
                240
            )
        )

        core_pen.setWidthF(2.2)
        core_pen.setCapStyle(
            Qt.RoundCap
        )
        core_pen.setJoinStyle(
            Qt.RoundJoin
        )

        painter.setPen(core_pen)
        painter.drawPolyline(
            bright_line
        )

        head_y = bright_points[-1].y()

        painter.setPen(Qt.NoPen)

        painter.setBrush(
            QColor(
                56,
                189,
                248,
                130
            )
        )

        painter.drawEllipse(
            QPointF(
                head,
                head_y
            ),
            7.0,
            7.0
        )

        painter.setBrush(
            QColor(
                255,
                255,
                255
            )
        )

        painter.drawEllipse(
            QPointF(
                head,
                head_y
            ),
            3.4,
            3.4
        )


class BrandPanel(QFrame):
    def __init__(self):
        super().__init__()

        self.setObjectName(
            "brandPanel"
        )

        self.setAttribute(
            Qt.WA_StyledBackground,
            True
        )

        self.ecg = EcgMonitor(self)

        self.heart = QLabel("♥")

        self.heart.setObjectName(
            "heartMark"
        )

        self.heart.setAlignment(
            Qt.AlignCenter
        )

        self._heart_opacity = (
            QGraphicsOpacityEffect(
                self.heart
            )
        )

        self._heart_opacity.setOpacity(
            1.0
        )

        self.heart.setGraphicsEffect(
            self._heart_opacity
        )

        name = QLabel("Solace")

        name.setObjectName(
            "brandName"
        )

        name.setAlignment(
            Qt.AlignCenter
        )

        tagline = QLabel(
            "WELLBEING, WITH CARE"
        )

        tagline.setObjectName(
            "brandTagline"
        )

        tagline.setAlignment(
            Qt.AlignCenter
        )

        tagline_font = tagline.font()

        tagline_font.setLetterSpacing(
            QFont.AbsoluteSpacing,
            2.0
        )

        tagline.setFont(
            tagline_font
        )

        overlay = QVBoxLayout(self)

        overlay.setContentsMargins(
            40,
            40,
            40,
            40
        )

        overlay.addStretch()

        overlay.addWidget(
            self.heart,
            0,
            Qt.AlignHCenter
        )

        overlay.addSpacing(10)

        overlay.addWidget(
            name,
            0,
            Qt.AlignHCenter
        )

        overlay.addSpacing(6)

        overlay.addWidget(
            tagline,
            0,
            Qt.AlignHCenter
        )

        overlay.addStretch()

        self._blink = QPropertyAnimation(
            self._heart_opacity,
            b"opacity"
        )

        self._blink.setDuration(1500)

        self._blink.setKeyValueAt(
            0.00,
            1.0
        )

        self._blink.setKeyValueAt(
            0.12,
            0.25
        )

        self._blink.setKeyValueAt(
            0.24,
            1.0
        )

        self._blink.setKeyValueAt(
            0.40,
            0.25
        )

        self._blink.setKeyValueAt(
            0.55,
            1.0
        )

        self._blink.setKeyValueAt(
            1.00,
            1.0
        )

        self._blink.setEasingCurve(
            QEasingCurve.InOutSine
        )

        self._blink.setLoopCount(-1)
        self._blink.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        self.ecg.setGeometry(
            0,
            0,
            self.width(),
            self.height()
        )

        self.ecg.lower()


class LoginPage(QWidget):
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
            "Welcome back"
        )

        heading.setObjectName(
            "formTitle"
        )

        subtitle = QLabel(
            "Sign in to your dashboard."
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
            42
        )

        self.status_label.hide()

        username_label = QLabel(
            "Username"
        )

        username_label.setObjectName(
            "fieldLabel"
        )

        self.username_input = QLineEdit()

        self.username_input.setPlaceholderText(
            "Enter your username"
        )

        self.username_input.setFixedHeight(
            50
        )

        password_label = QLabel(
            "Password"
        )

        password_label.setObjectName(
            "fieldLabel"
        )

        self.password_input = QLineEdit()

        self.password_input.setPlaceholderText(
            "Enter your password"
        )

        self.password_input.setEchoMode(
            QLineEdit.Password
        )

        self.password_input.setFixedHeight(
            50
        )

        self.login_button = QPushButton(
            "Log in"
        )

        self.login_button.setObjectName(
            "primaryButton"
        )

        self.login_button.setCursor(
            Qt.PointingHandCursor
        )

        self.login_button.setFixedHeight(
            48
        )

        self.register_button = QPushButton(
            "Create account"
        )

        self.register_button.setObjectName(
            "secondaryButton"
        )

        self.register_button.setCursor(
            Qt.PointingHandCursor
        )

        self.register_button.setFixedHeight(
            48
        )

        self.password_input.returnPressed.connect(
            self.login_button.click
        )

        divider = self._divider(
            "New here?"
        )

        layout = QVBoxLayout(panel)

        layout.setContentsMargins(
            56,
            38,
            56,
            38
        )

        layout.addStretch()

        layout.addWidget(heading)
        layout.addSpacing(6)
        layout.addWidget(subtitle)
        layout.addSpacing(8)

        layout.addWidget(
            self.status_label
        )

        layout.addSpacing(14)
        layout.addWidget(username_label)
        layout.addSpacing(5)
        layout.addWidget(
            self.username_input
        )

        layout.addSpacing(14)
        layout.addWidget(password_label)
        layout.addSpacing(5)
        layout.addWidget(
            self.password_input
        )

        layout.addSpacing(20)
        layout.addWidget(
            self.login_button
        )

        layout.addSpacing(16)
        layout.addWidget(divider)
        layout.addSpacing(16)

        layout.addWidget(
            self.register_button
        )

        layout.addStretch()

        return panel

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

    def clear_password(self):
        self.password_input.clear()

    def _divider(self, text):
        container = QWidget()

        left_line = QFrame()

        left_line.setObjectName(
            "dividerLine"
        )

        left_line.setFixedHeight(1)

        right_line = QFrame()

        right_line.setObjectName(
            "dividerLine"
        )

        right_line.setFixedHeight(1)

        label = QLabel(text)

        label.setObjectName(
            "dividerLabel"
        )

        label.setAlignment(
            Qt.AlignCenter
        )

        layout = QHBoxLayout(
            container
        )

        layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        layout.setSpacing(12)

        layout.addWidget(
            left_line,
            1,
            Qt.AlignVCenter
        )

        layout.addWidget(
            label,
            0
        )

        layout.addWidget(
            right_line,
            1,
            Qt.AlignVCenter
        )

        return container
