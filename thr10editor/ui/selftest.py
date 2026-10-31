"""Самопроверка интерфейса: загрузить QML, погонять демо, снять скриншот, выйти.

Используется в CI/тестах и после сборки .exe: `THR10Editor.exe --selftest 3`.
Код выхода 0 — интерфейс загрузился без ошибок QML и сессия дошла до
состояния «подключено» в демо-режиме.
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6.QtCore import QTimer

log = logging.getLogger(__name__)


def run_selftest(app: Any, backend: Any, theme: Any, window: Any, seconds: float,
                 screenshot: str, warnings: list[str], exit_code: dict[str, int]) -> None:
    steps: list[tuple[float, Any]] = [
        (0.6, lambda: backend.param("amp.gain").setValue(80)),
        (0.8, lambda: backend.group("mod").setEnabled(True)),
        (1.0, lambda: backend.demoTurnKnob("amp.treble", 12)),
    ]
    for t, fn in steps:
        if t < seconds:
            QTimer.singleShot(int(t * 1000), fn)

    def finish() -> None:
        problems = []
        if warnings:
            problems.append("предупреждения QML:\n  " + "\n  ".join(warnings))
        if backend.connStatus != "connected":
            problems.append(f"демо не подключилось: {backend.connText}")
        if seconds > 1.2 and backend.param("amp.treble").value != 12:
            problems.append("синхронизация «ручка на комбике → интерфейс» не сработала")
        if screenshot:
            img = window.grabWindow()
            if not img.save(screenshot):
                problems.append(f"не удалось сохранить снимок {screenshot}")
        if problems:
            for p in problems:
                log.error("selftest: %s", p)
                print("SELFTEST FAIL:", p)
            exit_code["value"] = 1
        else:
            print("SELFTEST OK")
        app.quit()

    QTimer.singleShot(int(seconds * 1000), finish)
