"""Общий интерфейс транспорта: реальный MIDI и демо-режим."""

from __future__ import annotations

from abc import ABC, abstractmethod


class TransportError(Exception):
    """Ошибка связи (порт не найден, отключён, ошибка драйвера)."""


class Transport(ABC):
    #: короткое имя типа: "demo" или "midi"
    kind: str = "base"
    #: демо-транспорт принимает и неподтверждённые команды (это симуляция)
    accepts_unconfirmed: bool = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Человекочитаемое имя (порт или «Демо»)."""

    @property
    @abstractmethod
    def is_open(self) -> bool: ...

    @abstractmethod
    def open(self) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def send(self, msg: bytes) -> None:
        """Отправить одно полное SysEx-сообщение F0…F7."""

    @abstractmethod
    def poll(self) -> list[bytes]:
        """Забрать пришедшие SysEx-сообщения (неблокирующе)."""
