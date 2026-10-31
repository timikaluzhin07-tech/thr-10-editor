"""История изменений для undo/redo.

* Каждая запись — набор изменений {ключ: (было, стало)} и, при необходимости,
  смена имени звука.
* Изменения внутри одного жеста (перетаскивание ручки) склеиваются в одну
  запись; отдельные шаги колеса/клавиш по одному параметру склеиваются, если
  идут чаще merge_window секунд.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

Changes = dict[str, tuple[int, int]]


@dataclass
class Entry:
    label: str
    changes: Changes
    name: tuple[str, str] | None = None
    merge_key: str | None = None
    time: float = 0.0
    sealed: bool = False

    def is_empty(self) -> bool:
        return not self.changes and (self.name is None or self.name[0] == self.name[1])


@dataclass
class Step:
    """Что применить при undo/redo."""

    values: dict[str, int]
    name: str | None
    label: str


@dataclass
class History:
    limit: int = 300
    merge_window: float = 0.8
    clock: Callable[[], float] = time.monotonic
    _undo: list[Entry] = field(default_factory=list)
    _redo: list[Entry] = field(default_factory=list)

    def record(self, changes: Changes, label: str, *, merge_key: str | None = None,
               name: tuple[str, str] | None = None) -> None:
        if not changes and (name is None or name[0] == name[1]):
            return
        now = self.clock()
        last = self._undo[-1] if self._undo else None
        if (merge_key is not None and last is not None and not last.sealed
                and last.merge_key == merge_key and now - last.time <= self.merge_window):
            for k, (old, new) in changes.items():
                if k in last.changes:
                    last.changes[k] = (last.changes[k][0], new)
                else:
                    last.changes[k] = (old, new)
            last.changes = {k: v for k, v in last.changes.items() if v[0] != v[1]}
            if name is not None:
                last.name = (last.name[0] if last.name else name[0], name[1])
            last.time = now
            if last.is_empty():
                self._undo.pop()
            self._redo.clear()
            return
        self._undo.append(Entry(label, dict(changes), name, merge_key, now))
        if len(self._undo) > self.limit:
            del self._undo[: len(self._undo) - self.limit]
        self._redo.clear()

    def seal(self) -> None:
        """Закончить жест: следующая запись не склеится с последней."""
        if self._undo:
            self._undo[-1].sealed = True

    def undo(self) -> Step | None:
        if not self._undo:
            return None
        e = self._undo.pop()
        e.sealed = True
        self._redo.append(e)
        return Step({k: old for k, (old, _) in e.changes.items()},
                    e.name[0] if e.name else None, e.label)

    def redo(self) -> Step | None:
        if not self._redo:
            return None
        e = self._redo.pop()
        self._undo.append(e)
        return Step({k: new for k, (_, new) in e.changes.items()},
                    e.name[1] if e.name else None, e.label)

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str:
        return self._undo[-1].label if self._undo else ""

    @property
    def redo_label(self) -> str:
        return self._redo[-1].label if self._redo else ""

    def clear(self) -> None:
        self._undo.clear()
        self._redo.clear()

    def __len__(self) -> int:
        return len(self._undo)
