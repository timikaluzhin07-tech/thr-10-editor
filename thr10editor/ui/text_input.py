"""Общий механизм завершения ввода во всех текстовых полях окна.

Один фильтр событий на окне вместо правок в каждом поле:

* клик в любую область окна вне поля ввода завершает ввод — фокус уходит,
  поле получает editingFinished и сохраняет текст;
* Enter в однострочном поле завершает ввод так же (в многострочном Enter —
  перевод строки, завершение — Ctrl+Enter или клик вне поля);
* свойство `editing` = в фокусе редактируемое текстовое поле. Горячие
  клавиши приложения отключаются, пока оно true, — пробел, стрелки, буквы
  вводятся как текст.

Поле может отказаться от завершения по Enter свойством
`finishOnEnter: false` (например, ввод значения ручки при ошибке).
"""

from __future__ import annotations

from PySide6.QtCore import Property, QEvent, QObject, Qt, QTimer, Signal
from PySide6.QtQuick import QQuickItem, QQuickWindow


def is_text_editor(item: QQuickItem | None) -> bool:
    """Редактируемое текстовое поле (TextInput/TextField/TextEdit/TextArea)."""
    if item is None:
        return False
    if not (item.inherits("QQuickTextInput") or item.inherits("QQuickTextEdit")):
        return False
    if item.property("readOnly") is True or not item.isEnabled():
        return False
    return True


class TextInputGuard(QObject):
    editingChanged = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._window: QQuickWindow | None = None
        self._editing = False
        self._pending: QQuickItem | None = None

    def attach(self, window: QQuickWindow) -> None:
        self._window = window
        window.installEventFilter(self)
        window.activeFocusItemChanged.connect(self._update)
        self._update()

    # ---- состояние -----------------------------------------------------------
    def _focused_editor(self) -> QQuickItem | None:
        if self._window is None:
            return None
        item = self._window.activeFocusItem()
        return item if is_text_editor(item) else None

    def _update(self) -> None:
        editing = self._focused_editor() is not None
        if editing != self._editing:
            self._editing = editing
            self.editingChanged.emit()

    @Property(bool, notify=editingChanged)
    def editing(self) -> bool:
        return self._editing

    # ---- завершение ввода ---------------------------------------------------------
    def finish(self, item: QQuickItem | None = None) -> None:
        """Завершить ввод: убрать фокус с поля (оно отправит editingFinished)."""
        if self._window is None:
            return
        current = self._window.activeFocusItem()
        if item is not None and current is not item:
            return  # фокус уже ушёл сам (кнопка, ручка, другое поле)
        if is_text_editor(current):
            # фокус переходит к ближайшей области фокуса; поле шлёт editingFinished
            current.setFocus(False, Qt.FocusReason.OtherFocusReason)
        self._update()

    def _finish_pending(self) -> None:
        item, self._pending = self._pending, None
        if item is not None:
            self.finish(item)

    def _schedule(self, item: QQuickItem) -> None:
        """Завершить после доставки события: если оно само не увело фокус."""
        self._pending = item
        QTimer.singleShot(0, self._finish_pending)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        t = event.type()
        if t == QEvent.Type.MouseButtonPress:
            item = self._focused_editor()
            if item is not None:
                local = item.mapFromScene(event.scenePosition())
                if not item.contains(local):
                    self._schedule(item)
        elif t == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            item = self._focused_editor()
            if item is not None:
                multiline = item.inherits("QQuickTextEdit")
                ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
                if (not multiline or ctrl) and item.property("finishOnEnter") is not False:
                    self._schedule(item)
                    if multiline:
                        return True  # Ctrl+Enter в многострочном поле — не вставлять строку
        return False
