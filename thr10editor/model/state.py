"""Модель состояния звука: значения всех параметров + уведомления.

Не зависит ни от UI, ни от транспорта. Изменения помечаются источником
(Origin), чтобы контроллер решал, что отправлять на комбик и что писать в
историю undo.
"""

from __future__ import annotations

from enum import Enum
from typing import Callable, Mapping

from ..protocol.params import PARAMS, active_keys, normalize_values

Changes = dict[str, tuple[int, int]]  # ключ → (старое, новое)


class Origin(str, Enum):
    USER = "user"  # правка в интерфейсе
    DEVICE = "device"  # ручка на комбике или дамп с комбика
    LOAD = "load"  # загрузка пресета, A/B, сет-лист
    HISTORY = "history"  # undo/redo
    AUTOMATION = "automation"  # LFO
    MORPH = "morph"
    RANDOM = "random"


Listener = Callable[[Changes, Origin], None]


class ToneState:
    def __init__(self, values: Mapping[str, int] | None = None, name: str = "Новый звук"):
        self._values = normalize_values(values)
        self.name = name
        self._listeners: list[Listener] = []

    # ---- чтение ------------------------------------------------------------
    def get(self, key: str) -> int:
        return self._values[key]

    def __getitem__(self, key: str) -> int:
        return self._values[key]

    @property
    def values(self) -> dict[str, int]:
        return dict(self._values)

    def is_active(self, key: str) -> bool:
        return PARAMS[key].is_active(self._values)

    def active_keys(self) -> list[str]:
        return active_keys(self._values)

    # ---- подписка ------------------------------------------------------------
    def subscribe(self, listener: Listener) -> Callable[[], None]:
        self._listeners.append(listener)

        def unsubscribe() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return unsubscribe

    def _notify(self, changes: Changes, origin: Origin) -> None:
        if not changes:
            return
        for cb in list(self._listeners):
            cb(changes, origin)

    # ---- запись --------------------------------------------------------------
    def set(self, key: str, value: int, origin: Origin = Origin.USER) -> bool:
        """Изменить один параметр. Возвращает True, если значение поменялось."""
        p = PARAMS[key]
        new = p.clamp(value)
        old = self._values[key]
        if new == old:
            return False
        self._values[key] = new
        self._notify({key: (old, new)}, origin)
        return True

    def update(self, values: Mapping[str, int], origin: Origin = Origin.LOAD) -> Changes:
        """Изменить несколько параметров разом (одно уведомление)."""
        changes: Changes = {}
        for key, value in values.items():
            p = PARAMS.get(key)
            if p is None:
                continue
            new = p.clamp(value)
            old = self._values[key]
            if new != old:
                self._values[key] = new
                changes[key] = (old, new)
        self._notify(changes, origin)
        return changes

    def replace(self, values: Mapping[str, int], name: str | None = None,
                origin: Origin = Origin.LOAD) -> Changes:
        """Полностью заменить состояние (недостающие ключи — по умолчанию)."""
        if name is not None:
            self.name = name
        return self.update(normalize_values(values), origin)
