"""Отправка с ограничением частоты и склейкой изменений.

* Не больше одного сообщения за `min_interval` (по умолчанию 20 мс ≈ 50
  сообщений/с); после дампа — пауза `dump_interval`.
* Изменения одного ключа склеиваются: уходит последнее значение.
* Барьер (смена типа эффекта) не даёт склеивать изменения через себя —
  иначе значение для нового типа могло бы уйти раньше смены типа.
* Дамп заменяет всё, что ждёт в очереди: он содержит полное состояние.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class _Entry:
    key: str
    msg: bytes
    barrier: bool
    delay: float  # пауза после этого сообщения


class RateLimitedSender:
    def __init__(self, write: Callable[[bytes], None], *, min_interval: float = 0.02,
                 dump_interval: float | None = None,
                 clock: Callable[[], float] = time.monotonic):
        self._write = write
        self.min_interval = max(0.001, float(min_interval))
        self.dump_interval = (3 * self.min_interval if dump_interval is None
                              else max(self.min_interval, float(dump_interval)))
        self._clock = clock
        self._queue: list[_Entry] = []
        self._next = clock()
        self.sent = 0
        self.coalesced = 0
        self.dropped = 0

    # ---- очередь ---------------------------------------------------------------
    @property
    def pending(self) -> int:
        return len(self._queue)

    def pending_keys(self) -> list[str]:
        return [e.key for e in self._queue]

    def submit(self, key: str, msg: bytes, *, barrier: bool = False) -> None:
        if not barrier:
            for entry in reversed(self._queue):
                if entry.barrier:
                    break
                if entry.key == key:
                    entry.msg = msg
                    self.coalesced += 1
                    return
        self._queue.append(_Entry(key, msg, barrier, self.min_interval))

    def submit_dump(self, msg: bytes) -> None:
        self.dropped += len(self._queue)
        self._queue = [_Entry("dump", msg, True, self.dump_interval)]

    def clear(self) -> None:
        self.dropped += len(self._queue)
        self._queue.clear()

    # ---- отправка --------------------------------------------------------------
    def pump(self, now: float | None = None) -> int:
        """Отправить то, что разрешает лимит. Возвращает число отправленных.

        Сообщения идут не чаще одного за min_interval; если таймер опоздал,
        допускается догнать не больше одного интервала (короткая пачка из 2).
        """
        now = self._clock() if now is None else now
        count = 0
        while self._queue and now >= self._next:
            entry = self._queue.pop(0)
            self._write(entry.msg)
            self.sent += 1
            count += 1
            base = max(self._next, now - self.min_interval)
            self._next = base + entry.delay
        return count

    def flush(self) -> int:
        """Отправить всё немедленно, игнорируя лимит (для закрытия/тестов)."""
        count = 0
        while self._queue:
            entry = self._queue.pop(0)
            self._write(entry.msg)
            self.sent += 1
            count += 1
        return count
