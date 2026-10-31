"""Список пресетов библиотеки для QML ListView."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, Qt

from ..model.preset import Preset
from ..protocol.params import GROUPS, PARAMS

ROLES = ("presetId", "name", "folder", "tags", "favorite", "summary", "isCurrent", "modified")


def summary(values: dict[str, int]) -> str:
    amp = PARAMS["amp.model"].format(values["amp.model"])
    fx = [g.title for g in GROUPS if g.switch_key and values.get(g.switch_key)]
    return amp + (" · " + ", ".join(fx) if fx else "")


class PresetListModel(QAbstractListModel):
    def __init__(self, parent: Any = None):
        super().__init__(parent)
        self._items: list[Preset] = []
        self._current = ""

    def roleNames(self) -> dict[int, QByteArray]:  # noqa: N802
        return {Qt.ItemDataRole.UserRole + i: QByteArray(r.encode()) for i, r in enumerate(ROLES)}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: N802, B008
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or not 0 <= index.row() < len(self._items):
            return None
        p = self._items[index.row()]
        r = role - Qt.ItemDataRole.UserRole
        if role == Qt.ItemDataRole.DisplayRole:
            return p.name
        if r == 0:
            return p.id
        if r == 1:
            return p.name
        if r == 2:
            return p.folder
        if r == 3:
            return ", ".join(p.tags)
        if r == 4:
            return p.favorite
        if r == 5:
            return summary(p.values)
        if r == 6:
            return p.id == self._current
        if r == 7:
            return p.modified[:16].replace("T", " ")
        return None

    def set_items(self, items: list[Preset], current: str) -> None:
        same_ids = [p.id for p in items] == [p.id for p in self._items]
        self._current = current
        if same_ids:
            self._items = list(items)
            if items:
                self.dataChanged.emit(self.index(0), self.index(len(items) - 1))
            return
        self.beginResetModel()
        self._items = list(items)
        self.endResetModel()

    def ids(self) -> list[str]:
        return [p.id for p in self._items]
