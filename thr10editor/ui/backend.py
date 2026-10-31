"""Мост между QML и прикладным слоем (EditorSession, модель)."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from PySide6.QtCore import Property, QObject, Qt, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QGuiApplication

from .. import APP_NAME, __version__
from ..app.session import EditorSession, LinkStatus, LogEntry
from ..app.settings import AppSettings, atomic_write_json, load_overrides
from ..model.preset import Preset
from ..model.state import Changes, Origin, ToneState
from ..protocol.files import FileFormatError, read_any, write_syx, write_ydl
from ..protocol.params import (
    GROUPS,
    PARAMS,
    SYSTEM_SETTINGS,
    default_values,
    normalize_values,
)
from ..protocol.patch import DecodedPatch
from ..transport.base import TransportError
from ..transport.demo import DemoTransport
from ..transport.midi import MidiTransport, all_port_pairs, find_thr_ports, list_ports
from .params_bridge import GroupItem, ParamItem

log = logging.getLogger(__name__)

DEMO_LABEL = "Демо-комбик (без устройства)"


def url_to_path(url: Any) -> str:
    if isinstance(url, QUrl):
        return url.toLocalFile() or url.toString()
    s = str(url)
    if s.startswith("file:"):
        return QUrl(s).toLocalFile()
    return s


class Backend(QObject):
    toast = Signal(str, str)  # kind, text
    presetChanged = Signal()
    connectionChanged = Signal()
    portsChanged = Signal()
    slotsChanged = Signal()
    logChanged = Signal()
    systemChanged = Signal()
    importReady = Signal()
    captureChanged = Signal()

    def __init__(self, data_dir: str, *, settings: AppSettings | None = None,
                 parent: QObject | None = None):
        super().__init__(parent)
        self.data_dir = data_dir
        self.settings = settings or AppSettings(os.path.join(data_dir, "settings.json"))
        self.overrides = load_overrides(os.path.join(data_dir, "protocol_overrides.json"))
        self.state = ToneState(name="Новый звук")
        self.session = EditorSession(
            self.state, overrides=self.overrides,
            min_interval=max(5, int(self.settings.get("send_interval_ms", 20))) / 1000)
        self._clean: tuple[str, dict[str, int]] = (self.state.name, self.state.values)
        self._dirty = False
        self._ports: list[str] = []
        self._port_pairs: dict[str, Any] = {}
        self._selected_port = ""
        self._slots: list[dict[str, Any]] = self._load_slots()
        self._log_items: list[dict[str, str]] = []
        self._log_dirty = False
        self._imported: list[Preset] = []
        self._imported_source = ""
        self._gesture_key: str | None = None

        self._params = {k: ParamItem(self, p) for k, p in PARAMS.items()}
        self._groups = {g.key: GroupItem(self, g.key) for g in GROUPS}
        self._sync_all(self.state.values)

        self.state.subscribe(self._on_state)
        self.session.on_status.append(self._on_status)
        self.session.on_log.append(self._on_log)
        self.session.on_slot_captured.append(self._on_slot_captured)
        self.session.on_device_dump.append(self._on_device_dump)

        self._timer = QTimer(self)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.setInterval(5)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

        self._log_timer = QTimer(self)
        self._log_timer.setInterval(250)
        self._log_timer.timeout.connect(self._flush_log)
        self._log_timer.start()

    # =====================================================================
    # Такт и события сессии
    # =====================================================================
    def _tick(self) -> None:
        try:
            self.session.tick()
            self.on_tick(time.monotonic())
        except Exception:  # noqa: BLE001 — UI не должен падать от ошибки такта
            log.exception("ошибка в такте сессии")

    def on_tick(self, now: float) -> None:
        """Точка расширения для инструментов (морфинг, LFO)."""

    def _on_state(self, changes: Changes, origin: Origin) -> None:
        values = self.state.values
        for key in changes:
            self._params[key].sync(values[key])
        if any(PARAMS[k].is_type_selector or PARAMS[k].kind.value == "switch" for k in changes):
            self._sync_active(values)
        for g in self._groups.values():
            g.sync(values)
        self._update_dirty()
        self.after_state_change(changes, origin)

    def after_state_change(self, changes: Changes, origin: Origin) -> None:
        """Точка расширения (история, A/B)."""

    def after_rename(self, old: str, new: str) -> None:
        """Точка расширения (история)."""

    def _sync_active(self, values: dict[str, int]) -> None:
        for key, item in self._params.items():
            item.sync_active(PARAMS[key].is_active(values))

    def _sync_all(self, values: dict[str, int]) -> None:
        for key, item in self._params.items():
            item.sync(values[key])
        self._sync_active(values)
        for g in self._groups.values():
            g.sync(values)

    def _on_status(self, status: LinkStatus, text: str) -> None:
        self.connectionChanged.emit()
        if status is LinkStatus.ERROR:
            self.toast.emit("error", text)
        elif status is LinkStatus.NO_RESPONSE:
            self.toast.emit("warning", text)

    def _on_log(self, entry: LogEntry) -> None:
        t = time.strftime("%H:%M:%S", time.localtime(time.time()))
        self._log_items.append({"time": t, "dir": entry.direction, "text": entry.text,
                                "raw": entry.raw})
        if len(self._log_items) > 400:
            del self._log_items[:-400]
        self._log_dirty = True

    def _flush_log(self) -> None:
        if self._log_dirty:
            self._log_dirty = False
            self.logChanged.emit()

    def _on_device_dump(self, decoded: DecodedPatch) -> None:
        self._mark_clean()
        self.presetChanged.emit()

    def _on_slot_captured(self, index: int, decoded: DecodedPatch) -> None:
        self._slots[index] = {"name": decoded.name or f"Ячейка {index + 1}",
                              "values": decoded.values,
                              "time": time.strftime("%d.%m %H:%M")}
        self._save_slots()
        self.slotsChanged.emit()
        self.captureChanged.emit()
        self.toast.emit("success", f"Ячейка {index + 1} считана: «{decoded.name}»")

    # =====================================================================
    # Параметры
    # =====================================================================
    def is_confirmed(self, key: str) -> bool:
        return self.overrides.is_sendable_param(PARAMS[key])

    def set_param(self, key: str, value: int) -> None:
        self.state.set(key, value, Origin.USER)

    def begin_gesture(self, key: str) -> None:
        self._gesture_key = key

    def end_gesture(self) -> None:
        self._gesture_key = None

    def toggle_lock(self, key: str) -> None:
        """Переопределяется инструментами (рандомайзер)."""

    @Slot(str, result=QObject)
    def param(self, key: str) -> QObject:
        return self._params[key]

    @Slot(str, result=QObject)
    def group(self, key: str) -> QObject:
        return self._groups[key]

    @Property("QStringList", constant=True)
    def effectGroups(self) -> list[str]:  # noqa: N802
        return [g.key for g in GROUPS if g.key != "amp"]

    # =====================================================================
    # Пресет в редакторе
    # =====================================================================
    def _mark_clean(self) -> None:
        self._clean = (self.state.name, self.state.values)
        self._update_dirty()

    def _update_dirty(self) -> None:
        dirty = (self.state.name, self.state.values) != self._clean
        if dirty != self._dirty:
            self._dirty = dirty
            self.presetChanged.emit()

    @Property(str, notify=presetChanged)
    def presetName(self) -> str:  # noqa: N802
        return self.state.name

    @presetName.setter
    def presetName(self, name: str) -> None:  # noqa: N802
        name = name.strip() or "Без имени"
        if name != self.state.name:
            old = self.state.name
            self.state.name = name
            self.after_rename(old, name)
            self._update_dirty()
            self.presetChanged.emit()

    @Property(bool, notify=presetChanged)
    def dirty(self) -> bool:
        return self._dirty

    def load_preset(self, preset: Preset, *, origin: Origin = Origin.LOAD) -> None:
        self.state.replace(preset.values, name=preset.name, origin=origin)
        self._mark_clean()
        self.presetChanged.emit()

    @Slot()
    def newSound(self) -> None:  # noqa: N802
        self.load_preset(Preset("Новый звук", default_values()))
        self.toast.emit("info", "Новый звук: все параметры по умолчанию")

    @Slot()
    def sendToAmp(self) -> None:  # noqa: N802
        if self.session.transport is None:
            self.toast.emit("warning", "Комбик не подключён")
            return
        self.session.push_full_state()
        self.toast.emit("success", "Звук отправлен в текущее состояние комбика")

    # =====================================================================
    # Подключение
    # =====================================================================
    @Property(str, notify=connectionChanged)
    def connStatus(self) -> str:  # noqa: N802
        return self.session.status.value

    @Property(str, notify=connectionChanged)
    def connText(self) -> str:  # noqa: N802
        return self.session.status_text

    @Property(str, notify=connectionChanged)
    def deviceModel(self) -> str:  # noqa: N802
        return self.session.device_model

    @Property(bool, notify=connectionChanged)
    def isDemo(self) -> bool:  # noqa: N802
        return self.session.is_demo

    @Property(bool, notify=connectionChanged)
    def hasTransport(self) -> bool:  # noqa: N802
        return self.session.transport is not None

    @Property("QStringList", notify=portsChanged)
    def ports(self) -> list[str]:
        return [DEMO_LABEL, *self._ports]

    @Property(str, notify=connectionChanged)
    def selectedPort(self) -> str:  # noqa: N802
        return self._selected_port

    @Slot()
    def refreshPorts(self) -> None:  # noqa: N802
        try:
            ins, outs = list_ports()
        except TransportError as e:
            self._ports, self._port_pairs = [], {}
            self.portsChanged.emit()
            self.toast.emit("warning", f"MIDI недоступен: {e}")
            return
        pairs = all_port_pairs(ins, outs)
        best = find_thr_ports(ins, outs)
        if best is not None and best not in pairs:
            pairs.insert(0, best)
        self._port_pairs = {p.label: p for p in pairs}
        self._ports = list(self._port_pairs)
        self.portsChanged.emit()

    @Slot()
    def connectDemo(self) -> None:  # noqa: N802
        self.session.reconnect_factory = None
        self._selected_port = DEMO_LABEL
        self.session.attach(DemoTransport())
        self.settings.set("last_port", DEMO_LABEL)
        self.connectionChanged.emit()

    @Slot(str)
    def connectPort(self, label: str) -> None:  # noqa: N802
        if label == DEMO_LABEL:
            self.connectDemo()
            return
        pair = self._port_pairs.get(label)
        if pair is None:
            self.toast.emit("error", f"Порт «{label}» не найден — обновите список")
            return
        self._selected_port = label

        def factory() -> MidiTransport:
            ins, outs = list_ports()
            if pair.input not in ins or pair.output not in outs:
                raise TransportError("порт пока не появился")
            return MidiTransport(pair, self.overrides)

        self.session.reconnect_factory = factory
        ok = self.session.attach(MidiTransport(pair, self.overrides))
        if ok:
            self.settings.set("last_port", label)
        self.connectionChanged.emit()

    @Slot()
    def autoConnect(self) -> None:  # noqa: N802
        """При старте: последний порт → найденный THR → демо (если разрешено)."""
        self.refreshPorts()
        last = self.settings.get("last_port", "")
        if last and last in self._port_pairs:
            self.connectPort(last)
            return
        try:
            ins, outs = list_ports()
            best = find_thr_ports(ins, outs)
        except TransportError:
            best = None
        if best is not None:
            self._port_pairs.setdefault(best.label, best)
            self.connectPort(best.label)
            return
        if self.settings.get("start_demo_if_no_device", True):
            self.connectDemo()
            self.toast.emit("info", "Комбик не найден — включён демо-режим")

    @Slot()
    def disconnectDevice(self) -> None:  # noqa: N802
        self.session.reconnect_factory = None
        self.session.detach()
        self._selected_port = ""
        self.connectionChanged.emit()

    @Slot()
    def requestState(self) -> None:  # noqa: N802
        if self.session.transport is None:
            self.toast.emit("warning", "Комбик не подключён")
            return
        self.session.request_state()

    # ---- демо-симуляция ------------------------------------------------------------
    def _demo_amp(self):
        t = self.session.transport
        return t.amp if isinstance(t, DemoTransport) else None

    @Slot(str, int)
    def demoTurnKnob(self, key: str, value: int) -> None:  # noqa: N802
        amp = self._demo_amp()
        if amp is not None:
            amp.turn_knob(key, value)

    @Slot(int)
    def demoPressSlot(self, index: int) -> None:  # noqa: N802
        amp = self._demo_amp()
        if amp is not None:
            amp.press_slot(index)

    @Slot(int)
    def demoStoreSlot(self, index: int) -> None:  # noqa: N802
        amp = self._demo_amp()
        if amp is not None:
            amp.store_slot(index)
            self.toast.emit("success", f"Демо: ячейка {index + 1} сохранена на «комбике»")

    @Slot(bool)
    def demoPower(self, on: bool) -> None:  # noqa: N802
        amp = self._demo_amp()
        if amp is not None:
            amp.powered = on

    @Slot()
    def demoRandomKnob(self) -> None:  # noqa: N802
        import random

        amp = self._demo_amp()
        if amp is None:
            return
        key = random.choice(["amp.gain", "amp.master", "amp.bass", "amp.middle", "amp.treble"])
        amp.turn_knob(key, random.randint(0, 100))

    # =====================================================================
    # Ячейки комбика 1–5
    # =====================================================================
    def _slots_path(self) -> str:
        return os.path.join(self.data_dir, "slots.json")

    def _load_slots(self) -> list[dict[str, Any]]:
        empty = [{"name": "", "values": None, "time": ""} for _ in range(5)]
        try:
            with open(self._slots_path(), encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) == 5:
                out = []
                for d in data:
                    vals = d.get("values")
                    out.append({"name": str(d.get("name", "")),
                                "values": normalize_values(vals) if vals else None,
                                "time": str(d.get("time", ""))})
                return out
        except (OSError, ValueError, AttributeError):
            pass
        return empty

    def _save_slots(self) -> None:
        try:
            atomic_write_json(self._slots_path(), self._slots)
        except OSError as e:
            log.error("не удалось сохранить ячейки: %s", e)

    @Property("QVariantList", notify=slotsChanged)
    def slots(self) -> list[dict[str, Any]]:
        return [{"index": i, "name": s["name"], "known": s["values"] is not None,
                 "time": s["time"],
                 "summary": self._summary(s["values"]) if s["values"] else ""}
                for i, s in enumerate(self._slots)]

    @staticmethod
    def _summary(values: dict[str, int]) -> str:
        amp = PARAMS["amp.model"].format(values["amp.model"])
        fx = [g.title for g in GROUPS if g.switch_key and values.get(g.switch_key)]
        return amp + (" · " + ", ".join(fx) if fx else "")

    @Property(int, notify=captureChanged)
    def captureSlot(self) -> int:  # noqa: N802
        c = self.session.capture_slot
        return -1 if c is None else c

    @Slot(int)
    def readSlot(self, index: int) -> None:  # noqa: N802
        if self.session.transport is None:
            self.toast.emit("warning", "Комбик не подключён")
            return
        self.session.arm_slot_capture(index)
        self.captureChanged.emit()

    @Slot()
    def cancelSlotCapture(self) -> None:  # noqa: N802
        self.session.cancel_slot_capture()
        self.captureChanged.emit()

    @Slot(int)
    def loadSlot(self, index: int) -> None:  # noqa: N802
        s = self._slots[index]
        if s["values"] is None:
            self.toast.emit("warning", "Содержимое ячейки неизвестно — сначала считайте её")
            return
        self.load_preset(Preset(s["name"] or f"Ячейка {index + 1}", s["values"]))

    @Slot(int)
    def writeSlot(self, index: int) -> None:  # noqa: N802
        """Отправить звук в текущее состояние; сохраняет пользователь на комбике."""
        if self.session.transport is None:
            self.toast.emit("warning", "Комбик не подключён")
            return
        self.session.push_full_state()
        self._slots[index] = {"name": self.state.name, "values": self.state.values,
                              "time": time.strftime("%d.%m %H:%M") + " (отправлено)"}
        self._save_slots()
        self.slotsChanged.emit()

    # =====================================================================
    # Системные настройки комбика (lamp / wide) — UNCONFIRMED
    # =====================================================================
    @Property(bool, notify=systemChanged)
    def lamp(self) -> bool:
        return self.session.system["system.lamp"]

    @Property(bool, notify=systemChanged)
    def wide(self) -> bool:
        return self.session.system["system.wide"]

    @Property(bool, constant=True)
    def systemConfirmed(self) -> bool:  # noqa: N802
        return all(self.overrides.is_sendable_system(d) for d in SYSTEM_SETTINGS.values())

    @Slot(str, bool)
    def setSystem(self, key: str, on: bool) -> None:  # noqa: N802
        sent = self.session.set_system(key, on)
        self.systemChanged.emit()
        if not sent and self.session.transport is not None and not self.session.is_demo:
            self.toast.emit("warning", "Команда не подтверждена — изменено только в редакторе")

    # =====================================================================
    # Импорт / экспорт
    # =====================================================================
    def read_presets_from_file(self, path: str) -> list[Preset]:
        with open(path, "rb") as f:
            data = f.read()
        base = os.path.basename(path)
        if path.lower().endswith((".json", ".thrpreset")):
            doc = json.loads(data.decode("utf-8"))
            if isinstance(doc, dict) and doc.get("format") == "thr10editor.preset":
                p = Preset.from_file_dict(doc)
                p.source = f"файл {base}"
                return [p.copy(new_identity=True)]
            if isinstance(doc, dict) and doc.get("format") == "thr10editor.library":
                out = [Preset.from_dict(d).copy(new_identity=True) for d in doc.get("presets", [])]
                for p in out:
                    p.source = f"файл {base}"
                return out
            raise FileFormatError("JSON не похож на пресет THR10 Editor")
        fmt, raw = read_any(data)
        return [Preset.from_patch(r.patch, source=f"{fmt.upper()} {base}") for r in raw]

    @Slot("QVariant")
    def openFile(self, url: Any) -> None:  # noqa: N802
        path = url_to_path(url)
        try:
            presets = self.read_presets_from_file(path)
        except (OSError, ValueError, FileFormatError) as e:
            self.toast.emit("error", f"Не удалось открыть файл: {e}")
            return
        if not presets:
            self.toast.emit("warning", "В файле нет пресетов")
            return
        self._imported = presets
        self._imported_source = os.path.basename(path)
        if len(presets) == 1:
            self.loadImported(0)
        else:
            self.importReady.emit()

    @Property("QVariantList", notify=importReady)
    def importedPresets(self) -> list[dict[str, Any]]:  # noqa: N802
        return [{"index": i, "name": p.name, "summary": self._summary(p.values)}
                for i, p in enumerate(self._imported)]

    @Property(str, notify=importReady)
    def importedSource(self) -> str:  # noqa: N802
        return self._imported_source

    @Slot(int)
    def loadImported(self, index: int) -> None:  # noqa: N802
        if 0 <= index < len(self._imported):
            p = self._imported[index]
            self.load_preset(p)
            self.toast.emit("success", f"Загружен «{p.name}»")

    def current_preset(self) -> Preset:
        return Preset(self.state.name, self.state.values)

    @Slot("QVariant", str)
    def exportCurrent(self, url: Any, fmt: str) -> None:  # noqa: N802
        path = url_to_path(url)
        try:
            self.write_presets(path, [self.current_preset()], fmt)
        except (OSError, ValueError) as e:
            self.toast.emit("error", f"Не удалось сохранить: {e}")
            return
        self.toast.emit("success", f"Сохранено: {os.path.basename(path)}")

    @staticmethod
    def write_presets(path: str, presets: list[Preset], fmt: str = "") -> None:
        fmt = (fmt or os.path.splitext(path)[1].lstrip(".")).lower()
        if fmt in ("json", "thrpreset"):
            if len(presets) == 1:
                atomic_write_json(path, presets[0].to_file_dict())
            else:
                atomic_write_json(path, {"format": "thr10editor.library", "version": 1,
                                         "presets": [p.to_dict() for p in presets]})
        elif fmt == "syx":
            with open(path, "wb") as f:
                f.write(write_syx([p.to_patch() for p in presets]))
        elif fmt == "ydl":
            if len(presets) > 100:
                raise ValueError("в .YDL помещается не больше 100 пресетов")
            with open(path, "wb") as f:
                f.write(write_ydl([p.to_patch() for p in presets]))
        else:
            raise ValueError(f"неизвестный формат «{fmt}»")

    # =====================================================================
    # Журнал MIDI
    # =====================================================================
    @Property("QVariantList", notify=logChanged)
    def logItems(self) -> list[dict[str, str]]:  # noqa: N802
        return list(reversed(self._log_items[-200:]))

    @Slot()
    def copyLog(self) -> None:  # noqa: N802
        text = "\n".join(f"{e['time']} {e['dir']:5s} {e['text']} {e['raw']}"
                         for e in self._log_items)
        QGuiApplication.clipboard().setText(text)
        self.toast.emit("success", "Журнал скопирован в буфер обмена")

    @Slot()
    def clearLog(self) -> None:  # noqa: N802
        self._log_items.clear()
        self.logChanged.emit()

    # =====================================================================
    # Прочее
    # =====================================================================
    @Property(str, constant=True)
    def appName(self) -> str:  # noqa: N802
        return APP_NAME

    @Property(str, constant=True)
    def version(self) -> str:
        return __version__

    @Property(str, constant=True)
    def dataDir(self) -> str:  # noqa: N802
        return self.data_dir

    @Slot(str, "QVariant")
    def setSetting(self, key: str, value: Any) -> None:  # noqa: N802
        if hasattr(value, "toVariant"):
            value = value.toVariant()
        self.settings.set(key, value)

    @Slot(str, result="QVariant")
    def getSetting(self, key: str) -> Any:  # noqa: N802
        return self.settings.get(key)

    def shutdown(self) -> None:
        self._timer.stop()
        try:
            self.session.detach()
        except Exception:  # noqa: BLE001
            log.exception("ошибка при отключении")
        self.settings.save()
