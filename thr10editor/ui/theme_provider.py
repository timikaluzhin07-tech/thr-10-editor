"""Qt-обёртка над дизайн-токенами: синглтон Theme для QML.

QML обращается к токенам так:
    Theme.c.surface         — цвет текущей темы
    Theme.space.md          — отступ (уже умножен на масштаб)
    Theme.radius.lg, Theme.fontSize.md, Theme.size.knob
    Theme.motion.normal     — длительность анимации, мс
Масштаб = автоматический (по размеру окна) × пользовательский зум.
"""

from __future__ import annotations

import os
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QColor, QFontDatabase

from .theme import auto_scale, load_tokens

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def load_fonts() -> list[str]:
    """Зарегистрировать встроенные шрифты. Возвращает список семейств."""
    families: list[str] = []
    if not os.path.isdir(FONTS_DIR):
        return families
    for name in sorted(os.listdir(FONTS_DIR)):
        if name.lower().endswith((".ttf", ".otf")):
            fid = QFontDatabase.addApplicationFont(os.path.join(FONTS_DIR, name))
            if fid >= 0:
                families += QFontDatabase.applicationFontFamilies(fid)
    return families


class ThemeProvider(QObject):
    changed = Signal()
    metricsChanged = Signal()

    ZOOM_STEPS = (0.8, 0.9, 1.0, 1.1, 1.25, 1.4, 1.6)

    def __init__(self, tokens: dict[str, Any] | None = None, mode: str = "dark",
                 parent: QObject | None = None):
        super().__init__(parent)
        self._tokens = tokens or load_tokens()
        self._mode = mode if mode in self._tokens["themes"] else "dark"
        self._auto = 1.0
        self._zoom = 1.0
        self._family = self._resolve_family()
        self._colors: dict[str, QColor] = {}
        self._rebuild_colors()

    # ---- служебное -------------------------------------------------------------
    def _resolve_family(self) -> str:
        font = self._tokens["font"]
        available = set(QFontDatabase.families())
        for fam in [font["family"], *font.get("fallback", [])]:
            if fam in available:
                return fam
        return font["family"]

    def _rebuild_colors(self) -> None:
        self._colors = {k: QColor(v) for k, v in self._tokens["themes"][self._mode].items()}

    def _scaled(self, section: dict[str, float]) -> dict[str, float]:
        s = self.scale
        return {k: round(v * s, 2) for k, v in section.items()}

    # ---- свойства --------------------------------------------------------------
    @Property(str, notify=changed)
    def mode(self) -> str:
        return self._mode

    @Property(bool, notify=changed)
    def dark(self) -> bool:
        return self._mode == "dark"

    @Property("QVariantMap", notify=changed)
    def c(self) -> dict[str, QColor]:
        return self._colors

    @Property(str, constant=True)
    def name(self) -> str:
        return self._tokens.get("name", "")

    @Property(str, constant=True)
    def fontFamily(self) -> str:  # noqa: N802 — имя для QML
        return self._family

    @Property(float, notify=metricsChanged)
    def scale(self) -> float:
        return round(self._auto * self._zoom, 4)

    @Property(float, notify=metricsChanged)
    def zoom(self) -> float:
        return self._zoom

    @Property("QVariantMap", notify=metricsChanged)
    def space(self) -> dict[str, float]:
        return self._scaled(self._tokens["space"])

    @Property("QVariantMap", notify=metricsChanged)
    def radius(self) -> dict[str, float]:
        r = self._scaled(self._tokens["radius"])
        r["pill"] = 9999.0
        return r

    @Property("QVariantMap", notify=metricsChanged)
    def size(self) -> dict[str, float]:
        return self._scaled(self._tokens["size"])

    @Property("QVariantMap", notify=metricsChanged)
    def fontSize(self) -> dict[str, float]:  # noqa: N802
        return self._scaled(self._tokens["font"]["size"])

    @Property("QVariantMap", constant=True)
    def weight(self) -> dict[str, int]:
        return dict(self._tokens["font"]["weight"])

    @Property("QVariantMap", constant=True)
    def letterSpacing(self) -> dict[str, float]:  # noqa: N802
        return dict(self._tokens["font"].get("letterSpacing", {}))

    @Property("QVariantMap", constant=True)
    def motion(self) -> dict[str, int]:
        return dict(self._tokens["motion"])

    # ---- действия --------------------------------------------------------------
    @Slot()
    def toggle(self) -> None:
        self.setMode("light" if self._mode == "dark" else "dark")

    @Slot(str)
    def setMode(self, mode: str) -> None:  # noqa: N802
        if mode in self._tokens["themes"] and mode != self._mode:
            self._mode = mode
            self._rebuild_colors()
            self.changed.emit()

    @Slot(float, float)
    def updateWindowSize(self, width: float, height: float) -> None:  # noqa: N802
        new = auto_scale(width, height, self._tokens)
        if abs(new - self._auto) > 1e-6:
            self._auto = new
            self.metricsChanged.emit()

    def _set_zoom(self, z: float) -> None:
        if abs(z - self._zoom) > 1e-6:
            self._zoom = z
            self.metricsChanged.emit()

    @Slot()
    def zoomIn(self) -> None:  # noqa: N802
        bigger = [z for z in self.ZOOM_STEPS if z > self._zoom + 1e-6]
        if bigger:
            self._set_zoom(bigger[0])

    @Slot()
    def zoomOut(self) -> None:  # noqa: N802
        smaller = [z for z in self.ZOOM_STEPS if z < self._zoom - 1e-6]
        if smaller:
            self._set_zoom(smaller[-1])

    @Slot()
    def zoomReset(self) -> None:  # noqa: N802
        self._set_zoom(1.0)

    @Slot(float)
    def setZoom(self, z: float) -> None:  # noqa: N802
        self._set_zoom(max(self.ZOOM_STEPS[0], min(self.ZOOM_STEPS[-1], float(z))))

    @Slot(str, float, result=QColor)
    def alpha(self, name: str, a: float) -> QColor:
        """Цвет темы с другой прозрачностью: Theme.alpha("accent", 0.2)."""
        col = QColor(self._colors.get(name, QColor(name)))
        col.setAlphaF(max(0.0, min(1.0, a)))
        return col
