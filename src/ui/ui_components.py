"""Shared presentation components. No account, recording or analysis logic."""
import os
import math
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QRectF,
    QPoint,
    QPropertyAnimation,
    QParallelAnimationGroup,
    QEasingCurve,
    QTimer,
    QElapsedTimer,
)
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import QWidget, QScrollArea, QFrame, QGraphicsOpacityEffect, QGraphicsDropShadowEffect

IMAGES = Path(__file__).resolve().parents[1] / 'images'


def _load_pixmap(*names):
    """Load the first image that exists from the given names (raster: png/jpg)."""
    for name in names:
        path = IMAGES / name
        if path.exists():
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap
    return QPixmap()


class GardenArtwork(QWidget):
    """Scale a bundled raster image to fill the available space without distortion."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Accept either spelling of the file name.
        self.pixmap = _load_pixmap('quite_garden.png', 'quiet_garden.png')
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setMinimumSize(0, 0)

    def paintEvent(self, event):
        # Nothing to draw if the image is missing; stay silent, no errors.
        if self.pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        # Round only the left corners so the artwork matches the card edge;
        # the right side stays flush against the form panel.
        radius = 16
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.moveTo(rect.right(), rect.top())
        path.lineTo(rect.left() + radius, rect.top())
        path.quadTo(rect.left(), rect.top(), rect.left(), rect.top() + radius)
        path.lineTo(rect.left(), rect.bottom() - radius)
        path.quadTo(rect.left(), rect.bottom(), rect.left() + radius, rect.bottom())
        path.lineTo(rect.right(), rect.bottom())
        path.closeSubpath()
        painter.setClipPath(path)

        # Cover the widget while preserving aspect ratio.
        scaled = self.pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)


def scroll_page(content):
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setWidget(content)
    return scroll


def reveal(widget):
    """Short, finite entrance; opt out with SOLACE_REDUCED_MOTION=1."""
    if os.environ.get('SOLACE_REDUCED_MOTION') == '1':
        return
    old = getattr(widget, "_reveal_animation", None)
    if old is not None:
        old.stop()
        old.deleteLater()
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)
    animation = QPropertyAnimation(effect, b'opacity', widget)
    animation.setDuration(340)
    animation.setStartValue(0.3)
    animation.setEndValue(1.0)
    animation.setEasingCurve(QEasingCurve.OutCubic)
    widget._reveal_animation = animation
    animation.start()

def float_in(widget, rise=28, duration=560):
    """Login-style entrance: fade in while rising slightly into place.
    Opt out with SOLACE_REDUCED_MOTION=1. Uses one opacity effect plus a
    temporary top margin that animates back to zero (so no layout fight)."""
    if os.environ.get('SOLACE_REDUCED_MOTION') == '1':
        return

    old = getattr(widget, "_float_group", None)
    if old is not None:
        old.stop()

    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    fade = QPropertyAnimation(effect, b'opacity', widget)
    fade.setDuration(duration)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QEasingCurve.OutCubic)

    pos = widget.pos()
    slide = QPropertyAnimation(widget, b'pos', widget)
    slide.setDuration(duration)
    slide.setStartValue(QPoint(pos.x(), pos.y() + rise))
    slide.setEndValue(pos)
    slide.setEasingCurve(QEasingCurve.OutCubic)

    group = QParallelAnimationGroup(widget)
    group.addAnimation(fade)
    group.addAnimation(slide)
    widget._float_group = group
    group.start()

class FloatCard(QWidget):
    """Wraps a fixed-size card with a soft drop shadow and a gentle
    fade-and-rise entrance. The card is positioned manually inside (no
    layout here), so the slide can't be snapped back by a parent layout.

    Only ONE graphics effect is used — opacity, on this wrapper. The shadow
    is painted here in paintEvent instead of via QGraphicsDropShadowEffect,
    because an effect inside another effect makes Qt's offscreen render fail
    ('painter not active') and the card paints blank."""

    PAD = 44

    def __init__(self, card, rise=34, parent=None):
        super().__init__(parent)
        self._card = card
        self._rise = rise
        self._radius = 16

        card.setParent(self)
        self.setFixedSize(
            card.width() + self.PAD * 2,
            card.height() + self.PAD * 2,
        )
        self._rest = QPoint(self.PAD, self.PAD)
        card.move(self._rest)

        self._opacity = QGraphicsOpacityEffect(self)
        self._opacity.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity)

    def paintEvent(self, event):
        # Soft shadow as stacked translucent rounded rects behind the card.
        # Denser near the card edge, fading outward, pushed slightly down.
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)

        x = self._rest.x()
        y = self._rest.y()
        w = self._card.width()
        h = self._card.height()

        layers = 16
        drop = 2  # bias the shadow downward
        for i in range(layers, 0, -1):
            spread = i * 2
            alpha = int(12 * (1 - i / layers) ** 2)
            if alpha <= 0:
                continue
            painter.setBrush(QColor(26, 44, 77, alpha))
            rect = QRectF(
                x - spread,
                y - spread + drop,
                w + spread * 2,
                h + spread * 2,
            )
            painter.drawRoundedRect(
                rect, self._radius + spread, self._radius + spread
            )

    def play(self):
        """Replay the entrance; opt out with SOLACE_REDUCED_MOTION=1."""
        if os.environ.get('SOLACE_REDUCED_MOTION') == '1':
            return

        old = getattr(self, '_entrance', None)
        if old is not None:
            old.stop()

        start = QPoint(self._rest.x(), self._rest.y() + self._rise)
        self._card.move(start)
        self._opacity.setOpacity(0.0)

        fade = QPropertyAnimation(self._opacity, b'opacity', self)
        fade.setDuration(560)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QEasingCurve.OutCubic)

        slide = QPropertyAnimation(self._card, b'pos', self)
        slide.setDuration(560)
        slide.setStartValue(start)
        slide.setEndValue(self._rest)
        slide.setEasingCurve(QEasingCurve.OutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        self._entrance = group
        group.start()

class AnimatedIllustration(QWidget):
    """Bundled raster artwork with slow, subtle breathing motion; no network calls."""

    def __init__(self, filename, parent=None, fit=False):
        super().__init__(parent)
        self.pixmap = _load_pixmap(filename)
        self._fit = fit
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self._clock = QElapsedTimer()
        self._clock.start()
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self.update)
        self._reduced = os.environ.get('SOLACE_REDUCED_MOTION') == '1'

    def showEvent(self, event):
        super().showEvent(event)

    def hideEvent(self, event):
        self._timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        if self.pixmap.isNull():
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        pw = self.pixmap.width()
        ph = self.pixmap.height()
        if pw == 0 or ph == 0:
            return

        # Cover the widget (fill+crop) by default, or fit the whole image
        # inside the widget when fit=True, with a very subtle breathing zoom.
        phase = 0 if self._reduced else math.sin(self._clock.elapsed() / 1500.0)
        base = min(self.width() / pw, self.height() / ph) if self._fit \
            else max(self.width() / pw, self.height() / ph)
        scale = base * (1 + phase * 0.012)
        w = pw * scale
        h = ph * scale
        x = (self.width() - w) / 2
        y = (self.height() - h) / 2 - phase * 1.3

        painter.drawPixmap(QRectF(x, y, w, h), self.pixmap, QRectF(0, 0, pw, ph))