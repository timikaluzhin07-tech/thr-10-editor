"""Полный бэкенд: базовые функции (Backend) + новые инструменты этапа 6.

Библиотека → A/B → undo/redo → сет-лист → тап-темп → рандомайзер → морфинг →
автоматизация. Вся логика — в thr10editor.model; здесь только связь с QML.
"""

from __future__ import annotations

import logging
import os
import random
import time
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot

from ..model.history import History, Step
from ..model.library import Library
from ..model.preset import Preset, normalize_folder, normalize_tags
from ..model.state import Changes, Origin
from ..model.tools import (
    CURVES,
    SUBDIVISIONS,
    WAVEFORM_LABELS,
    WAVEFORMS,
    ABCompare,
    Automation,
    Lfo,
    Morph,
    RandomizerConfig,
    SetlistPlayer,
    TapTempo,
    delay_value_for,
    randomize,
)
from ..protocol.params import GROUPS_BY_KEY, PARAMS, Kind
from ..transport.base import TransportError
from ..transport.controller_input import Binding, ControllerInput, ControllerMapper
from ..transport.midi import list_ports
from .backend import Backend, url_to_path
from .library_model import PresetListModel, summary

log = logging.getLogger(__name__)

AB_TARGET = "__ab__"


def full_label(key: str) -> str:
    """Подпись параметра с типом эффекта, если он зависит от типа: «Output (Rack)»."""
    p = PARAMS[key]
    if p.depends_on and len(p.depends_values) == 1:
        return f"{p.label} ({PARAMS[p.depends_on].options[p.depends_values[0]]})"
    return p.label


def _label(changes: Changes) -> str:
    if len(changes) == 1:
        key = next(iter(changes))
        p = PARAMS[key]
        g = GROUPS_BY_KEY[p.group].title
        return f"{g}: {full_label(key)}" if p.group != "amp" else p.label
    return f"Изменено параметров: {len(changes)}"


class FullBackend(Backend):
    libraryChanged = Signal()
    historyChanged = Signal()
    abChanged = Signal()
    setlistChanged = Signal()
    stageChanged = Signal()
    tapChanged = Signal()
    randomChanged = Signal()
    morphChanged = Signal()
    lfoChanged = Signal()
    controllerChanged = Signal()

    def __init__(self, data_dir: str, **kw: Any):
        super().__init__(data_dir, **kw)
        s = self.settings
        # ---- библиотека
        self.library = Library(os.path.join(data_dir, "library.json"))
        self._model = PresetListModel(self)
        self._query = ""
        self._folder = ""
        self._tag = ""
        self._favorites_only = False
        self.current_preset_id = ""
        # ---- A/B и история (своя у каждого слота)
        self.ab = ABCompare()
        self.histories = {"A": History(), "B": History()}
        self._slot_preset = {"A": "", "B": ""}
        self._ab_clean: dict[str, tuple[str, dict[str, int]]] = {}
        self._applying = False
        self._known_name = self.state.name
        self._initial_sync = True
        # ---- сет-лист
        self._setlist_id = self.library.setlists[0].id if self.library.setlists else ""
        self.player = SetlistPlayer()
        self._stage = False
        cs = s.get("midi_controller") or {}
        self.mapper = ControllerMapper(Binding.from_dict(cs.get("next")),
                                       Binding.from_dict(cs.get("prev")),
                                       pc_selects=bool(cs.get("pc_selects", False)))
        self.ctrl: ControllerInput | None = None
        self._ctrl_ports: list[str] = []
        # ---- тап-темп
        self.tap = TapTempo()
        self._tap_sub = s.get("tap_subdivision", "1/4")
        if self._tap_sub not in SUBDIVISIONS:
            self._tap_sub = "1/4"
        self._tap_ms = 0.0
        # ---- рандомайзер
        rc = s.get("randomizer") or {}
        self.rand = RandomizerConfig(
            amount=max(0.0, min(1.0, float(rc.get("amount", 100)) / 100)),
            locked=set(rc.get("locked", ["amp.master"])) & set(PARAMS),
            bounds={k: (float(v[0]), float(v[1])) for k, v in (rc.get("bounds") or {}).items()
                    if k in PARAMS and isinstance(v, (list, tuple)) and len(v) == 2})
        self._rng = random.Random()
        # ---- морфинг
        ms = s.get("morph") or {}
        self.morph: Morph | None = None
        self._morph_target = AB_TARGET
        self._morph_target_name = ""
        self._morph_duration = float(ms.get("duration", 4.0))
        self._morph_curve = ms.get("curve", "smooth") if ms.get("curve") in CURVES else "smooth"
        self._morph_progress = 0.0
        # ---- автоматизация
        self.automation = Automation(max_rate_hz=float(s.get("lfo_rate_limit_hz", 20)))
        for d in s.get("lfos", []) or []:
            try:
                lfo = Lfo.from_dict(d)
                if lfo.key in PARAMS and PARAMS[lfo.key].kind is Kind.RANGE:
                    self.automation.lfos.append(lfo)
            except (KeyError, ValueError, TypeError):
                pass

        self._refresh_flags()
        self._refilter()

    # =====================================================================
    # Такт: морфинг, LFO, MIDI-контроллер
    # =====================================================================
    def on_tick(self, now: float) -> None:
        if self.morph is not None:
            values, done = self.morph.values(now)
            self._applying = True
            try:
                self.state.update(values, Origin.MORPH)
            finally:
                self._applying = False
            self._morph_progress = self.morph.progress(now)
            self.morphChanged.emit()
            if done:
                self._finish_morph()
        if self.automation.running:
            vals = self.automation.tick(now)
            if vals:
                self._applying = True
                try:
                    self.state.update(vals, Origin.AUTOMATION)
                finally:
                    self._applying = False
        if self.ctrl is not None:
            try:
                events = self.ctrl.poll()
            except TransportError as e:
                self.ctrl.close()
                self.ctrl = None
                self.toast.emit("error", str(e))
                self.controllerChanged.emit()
                return
            for e in events:
                self._on_controller_event(e)

    # =====================================================================
    # История (undo/redo) — записывается здесь
    # =====================================================================
    @property
    def history(self) -> History:
        return self.histories[self.ab.active]

    def after_state_change(self, changes: Changes, origin: Origin) -> None:
        name = (self._known_name, self.state.name) if self._known_name != self.state.name else None
        self._known_name = self.state.name
        if origin in (Origin.USER, Origin.LOAD) and self.morph is not None:
            self.stopMorph()
        if self.automation.running:
            if origin is Origin.USER:
                for k, (_, new) in changes.items():
                    self.automation.rebase(k, new)
            elif origin is Origin.LOAD:
                for k in self.automation.keys():
                    self.automation.rebase(k, self.state[k])
        if self._applying or origin in (Origin.HISTORY, Origin.AUTOMATION, Origin.MORPH):
            return
        h = self.history
        if origin is Origin.USER:
            key = next(iter(changes)) if len(changes) == 1 else None
            h.record(changes, _label(changes), merge_key=f"u:{key}" if key else None, name=name)
        elif origin is Origin.DEVICE:
            if len(changes) == 1 and name is None:
                key = next(iter(changes))
                h.record(changes, "Ручка на комбике", merge_key=f"d:{key}")
            elif self._initial_sync:
                self._initial_sync = False  # первое чтение состояния — не шаг истории
            else:
                h.record(changes, "Загрузка с комбика", name=name)
        elif origin is Origin.RANDOM:
            h.record(changes, "Рандомайзер", name=name)
        else:
            h.record(changes, f"Загрузка «{self.state.name}»", name=name)
        self.historyChanged.emit()

    def after_rename(self, old: str, new: str) -> None:
        self._known_name = new
        self.history.record({}, "Переименование", name=(old, new), merge_key="rename")
        self.historyChanged.emit()

    def _apply_step(self, step: Step) -> None:
        self._applying = True
        try:
            if step.name is not None:
                self.state.name = step.name
                self._known_name = step.name
            if step.values:
                self.state.update(step.values, Origin.HISTORY)
        finally:
            self._applying = False
        self._update_dirty()
        self.presetChanged.emit()
        self.historyChanged.emit()

    @Slot()
    def undo(self) -> None:
        step = self.history.undo()
        if step is None:
            self.toast.emit("info", "Нечего отменять")
            return
        self._apply_step(step)

    @Slot()
    def redo(self) -> None:
        step = self.history.redo()
        if step is None:
            self.toast.emit("info", "Нечего повторять")
            return
        self._apply_step(step)

    @Property(bool, notify=historyChanged)
    def canUndo(self) -> bool:  # noqa: N802
        return self.history.can_undo

    @Property(bool, notify=historyChanged)
    def canRedo(self) -> bool:  # noqa: N802
        return self.history.can_redo

    @Property(str, notify=historyChanged)
    def undoText(self) -> str:  # noqa: N802
        return self.history.undo_label

    @Property(str, notify=historyChanged)
    def redoText(self) -> str:  # noqa: N802
        return self.history.redo_label

    @Slot()
    def connectDemo(self) -> None:  # noqa: N802
        self._initial_sync = True
        super().connectDemo()

    @Slot(str)
    def connectPort(self, label: str) -> None:  # noqa: N802
        self._initial_sync = True
        super().connectPort(label)

    # =====================================================================
    # Загрузка пресета в редактор
    # =====================================================================
    def load_preset(self, preset: Preset, *, origin: Origin = Origin.LOAD) -> None:
        old_name = self.state.name
        values_same = preset.values == self.state.values
        super().load_preset(preset, origin=origin)
        if values_same and old_name != preset.name and not self._applying:
            self.history.record({}, f"Загрузка «{preset.name}»", name=(old_name, preset.name))
            self._known_name = preset.name
            self.historyChanged.emit()
        lib = self.library.get(preset.id)
        self.current_preset_id = preset.id if lib is not None else ""
        self._refilter()

    # =====================================================================
    # Библиотека
    # =====================================================================
    def _save_library(self) -> None:
        try:
            self.library.save()
        except OSError as e:
            self.toast.emit("error", f"Не удалось сохранить библиотеку: {e}")

    def _refilter(self) -> None:
        folder = self._folder if self._folder else None
        items = self.library.search(self._query, folder=folder,
                                    tags=[self._tag] if self._tag else (),
                                    favorites_only=self._favorites_only)
        self._model.set_items(items, self.current_preset_id)
        self.libraryChanged.emit()

    def _lib_changed(self) -> None:
        self._save_library()
        self._refilter()
        self.setlistChanged.emit()

    @Property(QObject, constant=True)
    def libraryModel(self) -> QObject:  # noqa: N802
        return self._model

    @Property(int, notify=libraryChanged)
    def libraryCount(self) -> int:  # noqa: N802
        return self._model.rowCount()

    @Property(int, notify=libraryChanged)
    def libraryTotal(self) -> int:  # noqa: N802
        return len(self.library)

    @Property(str, notify=libraryChanged)
    def currentPresetId(self) -> str:  # noqa: N802
        return self.current_preset_id

    @Property(str, notify=libraryChanged)
    def libSearch(self) -> str:  # noqa: N802
        return self._query

    @libSearch.setter
    def libSearch(self, q: str) -> None:  # noqa: N802
        if q != self._query:
            self._query = q
            self._refilter()

    @Property(str, notify=libraryChanged)
    def libFolder(self) -> str:  # noqa: N802
        return self._folder

    @libFolder.setter
    def libFolder(self, f: str) -> None:  # noqa: N802
        if f != self._folder:
            self._folder = f
            self._refilter()

    @Property(str, notify=libraryChanged)
    def libTag(self) -> str:  # noqa: N802
        return self._tag

    @libTag.setter
    def libTag(self, t: str) -> None:  # noqa: N802
        t = "" if t == self._tag else t  # повторный клик снимает фильтр
        self._tag = t
        self._refilter()

    @Property(bool, notify=libraryChanged)
    def libFavoritesOnly(self) -> bool:  # noqa: N802
        return self._favorites_only

    @libFavoritesOnly.setter
    def libFavoritesOnly(self, v: bool) -> None:  # noqa: N802
        if v != self._favorites_only:
            self._favorites_only = v
            self._refilter()

    @Property("QVariantList", notify=libraryChanged)
    def folders(self) -> list[dict[str, Any]]:
        counts = self.library.folder_counts()
        return [{"path": f, "name": f.rsplit("/", 1)[-1], "depth": f.count("/"),
                 "count": counts.get(f, 0)} for f in self.library.all_folders()]

    @Property("QStringList", notify=libraryChanged)
    def folderPaths(self) -> list[str]:  # noqa: N802
        return self.library.all_folders()

    @Property("QVariantList", notify=libraryChanged)
    def tags(self) -> list[dict[str, Any]]:
        return [{"tag": t, "count": c} for t, c in self.library.all_tags()]

    @Slot(str, result="QVariant")
    def presetInfo(self, preset_id: str) -> dict[str, Any]:  # noqa: N802
        p = self.library.get(preset_id)
        if p is None:
            return {}
        return {"id": p.id, "name": p.name, "folder": p.folder, "tags": ", ".join(p.tags),
                "favorite": p.favorite, "notes": p.notes, "summary": summary(p.values),
                "source": p.source}

    @Slot(str)
    def loadPreset(self, preset_id: str) -> None:  # noqa: N802
        p = self.library.get(preset_id)
        if p is None:
            self.toast.emit("error", "Пресет не найден")
            return
        self.load_preset(p.copy())

    @Slot(str, result=bool)
    def overwritePreset(self, preset_id: str) -> bool:  # noqa: N802
        """Явная перезапись пресета библиотеки текущим звуком (после подтверждения в UI).

        Имя, папка, теги и заметки пресета сохраняются; меняются только значения.
        """
        p = self.library.get(preset_id)
        if p is None:
            self.toast.emit("error", "Пресет не найден")
            return False
        p.values = dict(self.state.values)
        self.library.update(p)
        self.current_preset_id = p.id
        if self.state.name != p.name:
            self.presetName = p.name
        self._mark_clean()
        self._lib_changed()
        self.toast.emit("success", f"Перезаписан «{p.name}»")
        return True

    @Slot(str, str, str, bool, str)
    def saveCurrentAs(self, name: str, folder: str, tags: str, favorite: bool,  # noqa: N802
                      notes: str) -> None:
        """«Сохранить»: всегда новый пресет из текущих фактических значений.

        Существующие пресеты не перезаписываются; звук в редакторе не меняется
        (меняется только имя, если его ввели в диалоге). Новый пресет становится
        активным.
        """
        values = dict(self.state.values)  # снимок того, что звучит сейчас
        name = name.strip() or self.state.name
        p = Preset(name, values, folder=folder, tags=normalize_tags(tags),
                   favorite=favorite, notes=notes, source="редактор")
        p = self.library.add(p)
        if name != self.state.name:
            self.presetName = name
        self.current_preset_id = p.id
        self._mark_clean()
        self._lib_changed()
        self.toast.emit("success", f"Сохранён новый пресет «{p.name}»")

    @Slot(str, str, str, str, bool, str)
    def updatePresetMeta(self, preset_id: str, name: str, folder: str, tags: str,  # noqa: N802
                         favorite: bool, notes: str) -> None:
        p = self.library.get(preset_id)
        if p is None:
            return
        p.name = name.strip() or p.name
        p.folder = normalize_folder(folder)
        p.tags = normalize_tags(tags)
        p.favorite = bool(favorite)
        p.notes = notes
        self.library.update(p)
        if preset_id == self.current_preset_id and self.state.name != p.name:
            self.presetName = p.name
            self._mark_clean()
        self._lib_changed()

    @Slot(str)
    def deletePreset(self, preset_id: str) -> None:  # noqa: N802
        p = self.library.get(preset_id)
        if p and self.library.remove(preset_id):
            if self.current_preset_id == preset_id:
                self.current_preset_id = ""
            self._lib_changed()
            self.toast.emit("info", f"Удалён «{p.name}»")

    @Slot(str)
    def duplicatePreset(self, preset_id: str) -> None:  # noqa: N802
        if self.library.get(preset_id):
            self.library.duplicate(preset_id)
            self._lib_changed()

    @Slot(str)
    def toggleFavorite(self, preset_id: str) -> None:  # noqa: N802
        if self.library.get(preset_id):
            self.library.toggle_favorite(preset_id)
            self._lib_changed()

    @Slot(str, str)
    def movePreset(self, preset_id: str, folder: str) -> None:  # noqa: N802
        if self.library.get(preset_id):
            self.library.set_folder(preset_id, folder)
            self._lib_changed()

    @Slot(str)
    def newFolder(self, path: str) -> None:  # noqa: N802
        if self.library.add_folder(path):
            self._lib_changed()

    @Slot(str, str)
    def renameFolder(self, old: str, new: str) -> None:  # noqa: N802
        self.library.rename_folder(old, new)
        if self._folder == old:
            self._folder = new
        self._lib_changed()

    @Slot(str)
    def deleteFolder(self, path: str) -> None:  # noqa: N802
        n = self.library.remove_folder(path)
        if self._folder == path or self._folder.startswith(path + "/"):
            self._folder = ""
        self._lib_changed()
        self.toast.emit("info", f"Папка удалена, пресетов перемещено: {n}")

    def _add_presets(self, presets: list[Preset], source: str) -> int:
        for p in presets:
            if not p.source:
                p.source = source
        self.library.add_many(presets)
        self._lib_changed()
        return len(presets)

    @Slot()
    def addImportedToLibrary(self) -> None:  # noqa: N802
        folder = os.path.splitext(self._imported_source)[0]
        for p in self._imported:
            p.folder = p.folder or f"Импорт/{folder}"
        n = self._add_presets([p.copy(new_identity=True) for p in self._imported],
                              self._imported_source)
        self.toast.emit("success", f"В библиотеку добавлено пресетов: {n}")

    @Slot("QVariantList")
    def importFilesToLibrary(self, urls: list[Any]) -> None:  # noqa: N802
        total = 0
        errors = []
        for url in urls:
            path = url_to_path(url)
            try:
                presets = self.read_presets_from_file(path)
            except (OSError, ValueError) as e:
                errors.append(f"{os.path.basename(path)}: {e}")
                continue
            folder = f"Импорт/{os.path.splitext(os.path.basename(path))[0]}"
            for p in presets:
                p.folder = p.folder or folder
            total += self._add_presets(presets, os.path.basename(path))
        if total:
            self.toast.emit("success", f"В библиотеку добавлено пресетов: {total}")
        for e in errors:
            self.toast.emit("error", f"Не удалось импортировать {e}")

    @Slot("QVariant", str, bool)
    def exportLibrary(self, url: Any, fmt: str, filtered_only: bool) -> None:  # noqa: N802
        path = url_to_path(url)
        ids = self._model.ids() if filtered_only else list(self.library.presets)
        presets = [self.library.presets[i] for i in ids]
        if not presets:
            self.toast.emit("warning", "Нет пресетов для экспорта")
            return
        try:
            if (fmt or "").lower() in ("json", "thrpreset", "thrlib"):
                fmt = "json"
            self.write_presets(path, presets, fmt)
        except (OSError, ValueError) as e:
            self.toast.emit("error", f"Экспорт не удался: {e}")
            return
        self.toast.emit("success", f"Экспортировано пресетов: {len(presets)}")

    # =====================================================================
    # A/B
    # =====================================================================
    @Property(str, notify=abChanged)
    def abActive(self) -> str:  # noqa: N802
        return self.ab.active

    @Property(str, notify=abChanged)
    def abOtherName(self) -> str:  # noqa: N802
        o = self.ab.peek_other()
        return o.name if o else "(копия текущего)"

    @Slot()
    def toggleAB(self) -> None:  # noqa: N802
        if self.morph is not None:
            self.stopMorph()
        self._slot_preset[self.ab.active] = self.current_preset_id
        self._ab_clean[self.ab.active] = self._clean
        other = self.ab.switch(self.state.name, self.state.values)
        self._applying = True
        try:
            self.state.replace(other.values, name=other.name, origin=Origin.LOAD)
        finally:
            self._applying = False
        self._known_name = self.state.name
        self.current_preset_id = self._slot_preset.get(self.ab.active, "")
        self._clean = self._ab_clean.get(self.ab.active, (self.state.name, self.state.values))
        self._update_dirty()
        self.presetChanged.emit()
        self.abChanged.emit()
        self.historyChanged.emit()
        self._refilter()

    @Slot(str)
    def selectAB(self, slot: str) -> None:  # noqa: N802
        if slot in ("A", "B") and slot != self.ab.active:
            self.toggleAB()

    @Slot()
    def copyToOtherSlot(self) -> None:  # noqa: N802
        self.ab.copy_to_other(self.state.name, self.state.values)
        self.abChanged.emit()
        self.toast.emit("success", f"Текущий звук скопирован в слот {self.ab.other}")

    # =====================================================================
    # Сет-лист и режим «сцена»
    # =====================================================================
    @Property("QVariantList", notify=setlistChanged)
    def setlists(self) -> list[dict[str, Any]]:
        return [{"id": s.id, "name": s.name, "count": len(s.items)} for s in self.library.setlists]

    @Property(str, notify=setlistChanged)
    def currentSetlistId(self) -> str:  # noqa: N802
        if not self.library.get_setlist(self._setlist_id):
            self._setlist_id = self.library.setlists[0].id if self.library.setlists else ""
        return self._setlist_id

    @currentSetlistId.setter
    def currentSetlistId(self, sid: str) -> None:  # noqa: N802
        if sid != self._setlist_id:
            self._setlist_id = sid
            self.setlistChanged.emit()

    @Property(str, notify=setlistChanged)
    def currentSetlistName(self) -> str:  # noqa: N802
        s = self.library.get_setlist(self.currentSetlistId)
        return s.name if s else ""

    @Property("QVariantList", notify=setlistChanged)
    def setlistItems(self) -> list[dict[str, Any]]:  # noqa: N802
        s = self.library.get_setlist(self.currentSetlistId)
        if not s:
            return []
        out = []
        for i, pid in enumerate(s.items):
            p = self.library.get(pid)
            out.append({"index": i, "id": pid, "name": p.name if p else "(удалён)",
                        "summary": summary(p.values) if p else "", "missing": p is None})
        return out

    @Slot(str)
    def newSetlist(self, name: str) -> None:  # noqa: N802
        s = self.library.add_setlist(name or f"Сет-лист {len(self.library.setlists) + 1}")
        self._setlist_id = s.id
        self._lib_changed()

    @Slot(str, str)
    def renameSetlist(self, sid: str, name: str) -> None:  # noqa: N802
        s = self.library.get_setlist(sid)
        if s and name.strip():
            s.name = name.strip()
            self._lib_changed()

    @Slot(str)
    def deleteSetlist(self, sid: str) -> None:  # noqa: N802
        self.library.remove_setlist(sid)
        self._lib_changed()

    def _ensure_setlist(self):
        s = self.library.get_setlist(self.currentSetlistId)
        if s is None:
            s = self.library.add_setlist("Сет-лист 1")
            self._setlist_id = s.id
        return s

    @Slot(str)
    def addToSetlist(self, preset_id: str) -> None:  # noqa: N802
        if not self.library.get(preset_id):
            return
        s = self._ensure_setlist()
        s.items.append(preset_id)
        self._lib_changed()
        self.toast.emit("success", f"Добавлено в «{s.name}»")

    @Slot()
    def addCurrentToSetlist(self) -> None:  # noqa: N802
        # звук ещё не в библиотеке или изменён — сохраняем как новый, ничего не перезаписывая
        if not self.library.get(self.current_preset_id) or self.dirty:
            self.saveCurrentAs(self.state.name, "Сет-листы", "", False, "")
        self.addToSetlist(self.current_preset_id)

    @Slot(int)
    def removeSetlistItem(self, index: int) -> None:  # noqa: N802
        s = self.library.get_setlist(self.currentSetlistId)
        if s and 0 <= index < len(s.items):
            del s.items[index]
            self._lib_changed()

    @Slot(int, int)
    def moveSetlistItem(self, src: int, dst: int) -> None:  # noqa: N802
        s = self.library.get_setlist(self.currentSetlistId)
        if s and 0 <= src < len(s.items) and 0 <= dst < len(s.items) and src != dst:
            s.items.insert(dst, s.items.pop(src))
            self._lib_changed()

    def _stage_load(self, pid: str | None) -> None:
        if pid is None:
            return
        p = self.library.get(pid)
        if p is not None:
            self.load_preset(p.copy())
        self.stageChanged.emit()

    @Property(bool, notify=stageChanged)
    def stageActive(self) -> bool:  # noqa: N802
        return self._stage

    @Property(int, notify=stageChanged)
    def stageIndex(self) -> int:  # noqa: N802
        return self.player.index

    @Property(int, notify=stageChanged)
    def stageCount(self) -> int:  # noqa: N802
        return len(self.player.items)

    def _stage_name(self, offset: int) -> str:
        pid = self.player.peek(offset)
        p = self.library.get(pid) if pid else None
        return p.name if p else ""

    @Property(str, notify=stageChanged)
    def stagePrevName(self) -> str:  # noqa: N802
        return self._stage_name(-1)

    @Property(str, notify=stageChanged)
    def stageNextName(self) -> str:  # noqa: N802
        return self._stage_name(1)

    @Property(str, notify=stageChanged)
    def stageSummary(self) -> str:  # noqa: N802
        return summary(self.state.values)

    @Slot(int)
    def startStage(self, index: int) -> None:  # noqa: N802
        s = self.library.get_setlist(self.currentSetlistId)
        items = [i for i in (s.items if s else []) if self.library.get(i)]
        if not items:
            self.toast.emit("warning", "Сет-лист пуст — добавьте в него пресеты из библиотеки")
            return
        self.player = SetlistPlayer(items)
        self._stage = True
        self._stage_load(self.player.goto(max(0, index)))
        self.stageChanged.emit()

    @Slot()
    def stopStage(self) -> None:  # noqa: N802
        self._stage = False
        self.stageChanged.emit()

    @Slot()
    def stageNext(self) -> None:  # noqa: N802
        if self._stage:
            before = self.player.index
            pid = self.player.next()
            if self.player.index != before:
                self._stage_load(pid)

    @Slot()
    def stagePrev(self) -> None:  # noqa: N802
        if self._stage:
            before = self.player.index
            pid = self.player.prev()
            if self.player.index != before:
                self._stage_load(pid)

    @Slot(int)
    def stageGoto(self, index: int) -> None:  # noqa: N802
        if self._stage:
            self._stage_load(self.player.goto(index))

    # ---- MIDI-контроллер / педаль --------------------------------------------------
    def _save_controller(self) -> None:
        self.settings.set("midi_controller", {
            "port": self.ctrl.port_name if self.ctrl else "",
            "next": self.mapper.next.to_dict() if self.mapper.next else None,
            "prev": self.mapper.prev.to_dict() if self.mapper.prev else None,
            "pc_selects": self.mapper.pc_selects,
        })

    def _on_controller_event(self, e: Any) -> None:
        res = self.mapper.handle(e)
        if res is None:
            return
        action, arg = res
        if action == "learned":
            which, b = arg
            self._save_controller()
            self.controllerChanged.emit()
            self.toast.emit("success", f"{'Следующий' if which == 'next' else 'Предыдущий'}: {b.label}")
        elif action == "next":
            self.stageNext()
        elif action == "prev":
            self.stagePrev()
        elif action == "goto":
            self.stageGoto(int(arg))

    @Property("QStringList", notify=controllerChanged)
    def controllerPorts(self) -> list[str]:  # noqa: N802
        return ["(нет)", *self._ctrl_ports]

    @Property(str, notify=controllerChanged)
    def controllerPort(self) -> str:  # noqa: N802
        return self.ctrl.port_name if self.ctrl else "(нет)"

    @Slot()
    def refreshControllerPorts(self) -> None:  # noqa: N802
        try:
            ins, _ = list_ports()
        except TransportError as e:
            ins = []
            self.toast.emit("warning", f"MIDI недоступен: {e}")
        thr = {n for n in ins if "thr" in n.lower()}
        self._ctrl_ports = [n for n in ins if n not in thr]
        self.controllerChanged.emit()

    @Slot(str)
    def setControllerPort(self, name: str) -> None:  # noqa: N802
        if self.ctrl is not None:
            self.ctrl.close()
            self.ctrl = None
        if name and name != "(нет)":
            c = ControllerInput(name)
            try:
                c.open()
            except TransportError as e:
                self.toast.emit("error", str(e))
            else:
                self.ctrl = c
                self.toast.emit("success", f"Контроллер: {name}")
        self._save_controller()
        self.controllerChanged.emit()

    @Slot(str)
    def learnController(self, which: str) -> None:  # noqa: N802
        self.mapper.learn(which)
        self.controllerChanged.emit()

    @Property(str, notify=controllerChanged)
    def controllerLearning(self) -> str:  # noqa: N802
        return self.mapper.learning or ""

    @Property(str, notify=controllerChanged)
    def nextBinding(self) -> str:  # noqa: N802
        return self.mapper.next.label if self.mapper.next else "не задано"

    @Property(str, notify=controllerChanged)
    def prevBinding(self) -> str:  # noqa: N802
        return self.mapper.prev.label if self.mapper.prev else "не задано"

    @Property(bool, notify=controllerChanged)
    def pcSelects(self) -> bool:  # noqa: N802
        return self.mapper.pc_selects

    @pcSelects.setter
    def pcSelects(self, v: bool) -> None:  # noqa: N802
        self.mapper.pc_selects = bool(v)
        self._save_controller()
        self.controllerChanged.emit()

    @Slot()
    def clearControllerBindings(self) -> None:  # noqa: N802
        self.mapper.next = self.mapper.prev = None
        self._save_controller()
        self.controllerChanged.emit()

    # =====================================================================
    # Тап-темп
    # =====================================================================
    @Slot()
    def tapTempo(self) -> None:  # noqa: N802
        ms = self.tap.tap()
        self.tapChanged.emit()
        if ms is None:
            return
        self._tap_ms = ms
        value, clamped = delay_value_for(ms, self._tap_sub)
        self.state.set("delay.time", value, Origin.USER)
        if clamped:
            self.toast.emit("warning", "Темп слишком медленный: время дилея ограничено максимумом")
        self.tapChanged.emit()

    @Property(float, notify=tapChanged)
    def tapBpm(self) -> float:  # noqa: N802
        return round(self.tap.bpm or 0.0, 1)

    @Property(int, notify=tapChanged)
    def tapCount(self) -> int:  # noqa: N802
        return self.tap.taps

    @Property("QStringList", constant=True)
    def tapSubdivisions(self) -> list[str]:  # noqa: N802
        return list(SUBDIVISIONS)

    @Property(str, notify=tapChanged)
    def tapSubdivision(self) -> str:  # noqa: N802
        return self._tap_sub

    @tapSubdivision.setter
    def tapSubdivision(self, sub: str) -> None:  # noqa: N802
        if sub in SUBDIVISIONS and sub != self._tap_sub:
            self._tap_sub = sub
            self.settings.set("tap_subdivision", sub)
            if self._tap_ms:
                value, _ = delay_value_for(self._tap_ms, sub)
                self.state.set("delay.time", value, Origin.USER)
            self.tapChanged.emit()

    # =====================================================================
    # Рандомайзер
    # =====================================================================
    def _save_random(self, emit: bool = True) -> None:
        self.settings.set("randomizer", {
            "amount": round(self.rand.amount * 100), "locked": sorted(self.rand.locked),
            "bounds": {k: list(v) for k, v in self.rand.bounds.items()}})
        if emit:
            self.randomChanged.emit()

    def _refresh_flags(self) -> None:
        automated = self.automation.keys()
        for k, item in self._params.items():
            item.sync_flags(k in self.rand.locked, k in automated)

    def toggle_lock(self, key: str) -> None:
        if key in self.rand.locked:
            self.rand.locked.discard(key)
        else:
            self.rand.locked.add(key)
        self._refresh_flags()
        self._save_random()

    @Slot()
    def randomize(self) -> None:
        new = randomize(self.state.values, self.rand, self._rng)
        changes = self.state.update(new, Origin.RANDOM)
        if changes:
            self.toast.emit("info", f"Рандомайзер: изменено параметров — {len(changes)} (Ctrl+Z — отменить)")

    @Property(int, notify=randomChanged)
    def randomAmount(self) -> int:  # noqa: N802
        return round(self.rand.amount * 100)

    @randomAmount.setter
    def randomAmount(self, v: int) -> None:  # noqa: N802
        self.rand.amount = max(0, min(100, int(v))) / 100
        self._save_random()

    @Property("QVariantList", notify=randomChanged)
    def randomParams(self) -> list[dict[str, Any]]:  # noqa: N802
        """Все параметры для панели рандомайзера: ручки (с границами), вкл/выкл и списки."""
        out = []
        prev_group = ""
        for k, p in PARAMS.items():
            lo, hi = self.rand.bounds_for(k)
            g = GROUPS_BY_KEY[p.group].title
            first, prev_group = g != prev_group, g
            if p.kind is Kind.SWITCH:
                label = "Вкл/выкл блока"
            elif k == "amp.model":
                label = "Модель"
            elif k == "amp.cab":
                label = "Кабинет"
            elif p.is_type_selector:
                label = "Тип эффекта"
            else:
                label = full_label(k)
            out.append({"key": k, "label": label, "group": g, "groupFirst": first,
                        "kind": p.kind.value,
                        "accent": GROUPS_BY_KEY[p.group].accent, "lo": lo, "hi": hi,
                        "locked": k in self.rand.locked})
        return out

    @Slot(str, float, float)
    def setRandomBounds(self, key: str, lo: float, hi: float) -> None:  # noqa: N802
        lo, hi = max(0.0, min(1.0, lo)), max(0.0, min(1.0, hi))
        if lo <= 0.0 and hi >= 1.0:
            self.rand.bounds.pop(key, None)
        else:
            self.rand.bounds[key] = (min(lo, hi), max(lo, hi))
        self._save_random(emit=False)

    @Slot()
    def resetRandomBounds(self) -> None:  # noqa: N802
        self.rand.bounds.clear()
        self._save_random()

    @Slot(bool)
    def lockAll(self, locked: bool) -> None:  # noqa: N802
        if locked:
            self.rand.locked = set(PARAMS)
        else:
            self.rand.locked = {"amp.master"}
        self._refresh_flags()
        self._save_random()

    # =====================================================================
    # Морфинг
    # =====================================================================
    def _save_morph(self) -> None:
        self.settings.set("morph", {"duration": self._morph_duration, "curve": self._morph_curve})
        self.morphChanged.emit()

    @Property("QVariantList", notify=libraryChanged)
    def morphTargets(self) -> list[dict[str, str]]:  # noqa: N802
        out = [{"id": AB_TARGET, "name": "Другой слот A/B"}]
        presets = sorted(self.library.presets.values(), key=lambda p: (not p.favorite, p.name.lower()))
        out += [{"id": p.id, "name": ("★ " if p.favorite else "") + p.name} for p in presets[:800]]
        return out

    @Property(str, notify=morphChanged)
    def morphTarget(self) -> str:  # noqa: N802
        return self._morph_target

    @morphTarget.setter
    def morphTarget(self, tid: str) -> None:  # noqa: N802
        self._morph_target = tid or AB_TARGET
        self.morphChanged.emit()

    @Property(float, notify=morphChanged)
    def morphDuration(self) -> float:  # noqa: N802
        return self._morph_duration

    @morphDuration.setter
    def morphDuration(self, sec: float) -> None:  # noqa: N802
        self._morph_duration = max(0.2, min(120.0, float(sec)))
        self._save_morph()

    @Property("QStringList", constant=True)
    def morphCurves(self) -> list[str]:  # noqa: N802
        return list(CURVES)

    @Property(str, notify=morphChanged)
    def morphCurve(self) -> str:  # noqa: N802
        return self._morph_curve

    @morphCurve.setter
    def morphCurve(self, c: str) -> None:  # noqa: N802
        if c in CURVES:
            self._morph_curve = c
            self._save_morph()

    @Property(bool, notify=morphChanged)
    def morphRunning(self) -> bool:  # noqa: N802
        return self.morph is not None

    @Property(float, notify=morphChanged)
    def morphProgress(self) -> float:  # noqa: N802
        return self._morph_progress

    @Slot(str)
    def morphTo(self, preset_id: str) -> None:  # noqa: N802
        self.morphTarget = preset_id
        self.startMorph()

    @Slot()
    def startMorph(self) -> None:  # noqa: N802
        if self.morph is not None:
            self.stopMorph()
        if self._morph_target == AB_TARGET:
            other = self.ab.peek_other()
            if other is None:
                self.toast.emit("warning", "Слот B пуст: переключитесь на B и настройте звук")
                return
            target_vals, self._morph_target_name = other.values, other.name
        else:
            p = self.library.get(self._morph_target)
            if p is None:
                self.toast.emit("warning", "Выберите пресет для морфинга")
                return
            target_vals, self._morph_target_name = p.values, p.name
        if self.automation.running:
            self.stopAutomation()
        self.morph = Morph(self.state.values, target_vals, self._morph_duration, self._morph_curve)
        self._morph_progress = 0.0
        self.morphChanged.emit()

    def _finish_morph(self, *, completed: bool = True) -> None:
        m, self.morph = self.morph, None
        if m is None:
            return
        old_name = self.state.name
        if completed and self._morph_target_name:
            self.state.name = self._morph_target_name
            self._known_name = self.state.name
        changes = {k: (m.start_values[k], self.state[k]) for k in PARAMS
                   if m.start_values[k] != self.state[k]}
        self.history.record(changes, "Морфинг", name=(old_name, self.state.name))
        self._update_dirty()
        self.presetChanged.emit()
        self.historyChanged.emit()
        self.morphChanged.emit()

    @Slot()
    def stopMorph(self) -> None:  # noqa: N802
        if self.morph is not None:
            self._finish_morph(completed=False)

    # =====================================================================
    # Автоматизация (LFO)
    # =====================================================================
    def _save_lfos(self, emit: bool = True) -> None:
        self.settings.set("lfos", [l.to_dict() for l in self.automation.lfos])
        self._refresh_flags()
        if emit:
            self.lfoChanged.emit()

    @Property("QVariantList", notify=lfoChanged)
    def lfos(self) -> list[dict[str, Any]]:
        out = []
        for l in self.automation.lfos:
            p = PARAMS[l.key]
            g = GROUPS_BY_KEY[p.group]
            out.append({"id": l.id, "key": l.key, "label": full_label(l.key), "group": g.title,
                        "accent": g.accent, "waveform": l.waveform,
                        "waveformIndex": WAVEFORMS.index(l.waveform),
                        "rate": l.rate_hz, "depth": l.depth, "enabled": l.enabled,
                        "active": p.is_active(self.state.values)})
        return out

    @Property("QStringList", constant=True)
    def waveforms(self) -> list[str]:
        return [WAVEFORM_LABELS[w] for w in WAVEFORMS]

    @Property("QVariantList", constant=True)
    def automatableParams(self) -> list[dict[str, str]]:  # noqa: N802
        return [{"key": k, "name": f"{GROUPS_BY_KEY[p.group].title}: {full_label(k)}"}
                for k, p in PARAMS.items() if p.kind is Kind.RANGE]

    @Slot(str)
    def addLfo(self, key: str) -> None:  # noqa: N802
        if key not in PARAMS or PARAMS[key].kind is not Kind.RANGE:
            return
        self.automation.add(key)
        if self.automation.running:
            self.automation.base[key] = self.state[key]
        self._save_lfos()

    @Slot(str)
    def removeLfo(self, lfo_id: str) -> None:  # noqa: N802
        lfo = self.automation.remove(lfo_id)
        if lfo and self.automation.running and lfo.key in self.automation.base:
            self.state.update({lfo.key: self.automation.base.pop(lfo.key)}, Origin.AUTOMATION)
        self._save_lfos()

    @Slot(str)
    def toggleLfoForKey(self, key: str) -> None:  # noqa: N802
        lfo = next((l for l in self.automation.lfos if l.key == key), None)
        if lfo:
            self.removeLfo(lfo.id)
        else:
            self.addLfo(key)
            self.toast.emit("info", f"LFO добавлен: {PARAMS[key].label}. Запуск — на панели «LFO» (Ctrl+L)")

    @Slot(str, str, "QVariant")
    def setLfoField(self, lfo_id: str, field: str, value: Any) -> None:  # noqa: N802
        lfo = self.automation.get(lfo_id)
        if lfo is None:
            return
        if field == "waveform":
            lfo.waveform = WAVEFORMS[int(value)] if isinstance(value, (int, float)) else str(value)
        elif field == "rate":
            lfo.rate_hz = float(value)
        elif field == "depth":
            lfo.depth = float(value)
        elif field == "enabled":
            lfo.enabled = bool(value)
            if not lfo.enabled and self.automation.running and lfo.key in self.automation.base:
                self.state.update({lfo.key: self.automation.base[lfo.key]}, Origin.AUTOMATION)
        lfo.clamp()
        self._save_lfos(emit=False)

    @Property(bool, notify=lfoChanged)
    def automationRunning(self) -> bool:  # noqa: N802
        return self.automation.running

    @Slot()
    def startAutomation(self) -> None:  # noqa: N802
        if not self.automation.lfos:
            self.toast.emit("warning", "Добавьте LFO: правый клик по ручке → «Автоматизация (LFO)»")
            return
        if self.morph is not None:
            self.stopMorph()
        self.automation.start(self.state.values, time.monotonic())
        self.lfoChanged.emit()

    @Slot()
    def stopAutomation(self) -> None:  # noqa: N802
        base = self.automation.stop()
        if base:
            self.state.update(base, Origin.AUTOMATION)
        self.lfoChanged.emit()

    @Slot()
    def toggleAutomation(self) -> None:  # noqa: N802
        if self.automation.running:
            self.stopAutomation()
        else:
            self.startAutomation()

    @Property(float, notify=lfoChanged)
    def lfoRateLimit(self) -> float:  # noqa: N802
        return self.automation.max_rate_hz

    def shutdown(self) -> None:
        if self.automation.running:
            self.stopAutomation()
        if self.ctrl is not None:
            self.ctrl.close()
        try:
            self.library.save()
        except OSError:
            log.exception("не удалось сохранить библиотеку")
        super().shutdown()
