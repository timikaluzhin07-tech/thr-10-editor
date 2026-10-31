"""Библиотека пресетов: без ограничения количества, папки, теги, поиск,
избранное. Здесь же хранятся сет-листы. Формат — один JSON-файл."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Iterable

from ..protocol.params import GROUPS, PARAMS
from .preset import Preset, new_id, normalize_folder, normalize_tags, now_iso

log = logging.getLogger(__name__)

LIBRARY_FORMAT = "thr10editor.library"
LIBRARY_VERSION = 1


@dataclass
class Setlist:
    name: str
    items: list[str] = field(default_factory=list)  # id пресетов по порядку
    id: str = field(default_factory=new_id)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "items": list(self.items), "notes": self.notes}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Setlist":
        return cls(name=str(d.get("name") or "Сет-лист"),
                   items=[str(x) for x in d.get("items", []) if x],
                   id=str(d.get("id") or new_id()), notes=str(d.get("notes", "")))


def preset_search_text(p: Preset) -> str:
    amp = PARAMS["amp.model"].format(p.values["amp.model"])
    fx = [g.title for g in GROUPS if g.switch_key and p.values.get(g.switch_key)]
    return " ".join([p.name, p.folder, " ".join(p.tags), p.notes, amp, *fx]).lower()


class Library:
    def __init__(self, path: str | None = None):
        self.path = path
        self.presets: dict[str, Preset] = {}
        self.folders: set[str] = set()
        self.setlists: list[Setlist] = []
        if path:
            self.load()

    # ---- файл ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "format": LIBRARY_FORMAT,
            "version": LIBRARY_VERSION,
            "presets": [p.to_dict() for p in self.presets.values()],
            "folders": sorted(self.folders),
            "setlists": [s.to_dict() for s in self.setlists],
        }

    def load(self) -> None:
        if not self.path or not os.path.exists(self.path):
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                doc = json.load(f)
        except (OSError, ValueError) as e:
            backup = self.path + ".broken"
            log.error("библиотека повреждена (%s), копия: %s", e, backup)
            try:
                os.replace(self.path, backup)
            except OSError:
                pass
            return
        self.load_dict(doc)

    def load_dict(self, doc: dict[str, Any]) -> None:
        if not isinstance(doc, dict) or doc.get("format") != LIBRARY_FORMAT:
            raise ValueError("это не библиотека THR10 Editor")
        self.presets.clear()
        for d in doc.get("presets", []):
            try:
                p = Preset.from_dict(d)
            except ValueError as e:
                log.warning("пропущен пресет: %s", e)
                continue
            self.presets[p.id] = p
        self.folders = {normalize_folder(f) for f in doc.get("folders", []) if normalize_folder(f)}
        self.setlists = [Setlist.from_dict(s) for s in doc.get("setlists", []) if isinstance(s, dict)]

    def save(self) -> None:
        if not self.path:
            return
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    # ---- пресеты -----------------------------------------------------------------
    def __len__(self) -> int:
        return len(self.presets)

    def get(self, preset_id: str) -> Preset | None:
        return self.presets.get(preset_id)

    def add(self, preset: Preset) -> Preset:
        p = preset if preset.id not in self.presets else preset.copy(new_identity=True)
        self.presets[p.id] = p
        if p.folder:
            self.folders.add(p.folder)
        return p

    def add_many(self, presets: Iterable[Preset]) -> list[Preset]:
        return [self.add(p) for p in presets]

    def update(self, preset: Preset) -> None:
        if preset.id not in self.presets:
            raise KeyError(preset.id)
        preset.touch()
        self.presets[preset.id] = preset
        if preset.folder:
            self.folders.add(preset.folder)

    def remove(self, preset_id: str) -> bool:
        if self.presets.pop(preset_id, None) is None:
            return False
        for s in self.setlists:
            s.items = [i for i in s.items if i != preset_id]
        return True

    def duplicate(self, preset_id: str) -> Preset:
        src = self.presets[preset_id]
        p = src.copy(new_identity=True)
        p.name = f"{src.name} (копия)"
        return self.add(p)

    def rename(self, preset_id: str, name: str) -> None:
        p = self.presets[preset_id]
        p.name = name.strip() or p.name
        p.touch()

    def set_folder(self, preset_id: str, folder: str) -> None:
        p = self.presets[preset_id]
        p.folder = normalize_folder(folder)
        if p.folder:
            self.folders.add(p.folder)
        p.touch()

    def set_tags(self, preset_id: str, tags: Any) -> None:
        p = self.presets[preset_id]
        p.tags = normalize_tags(tags)
        p.touch()

    def toggle_favorite(self, preset_id: str) -> bool:
        p = self.presets[preset_id]
        p.favorite = not p.favorite
        p.touch()
        return p.favorite

    # ---- папки -------------------------------------------------------------------
    def all_folders(self) -> list[str]:
        """Все папки (явные и из пресетов) вместе с родительскими, по алфавиту."""
        out: set[str] = set()
        for f in list(self.folders) + [p.folder for p in self.presets.values()]:
            parts = f.split("/") if f else []
            for i in range(1, len(parts) + 1):
                out.add("/".join(parts[:i]))
        return sorted(out, key=lambda s: s.lower())

    def add_folder(self, folder: str) -> str:
        f = normalize_folder(folder)
        if f:
            self.folders.add(f)
        return f

    def rename_folder(self, old: str, new: str) -> None:
        old, new = normalize_folder(old), normalize_folder(new)
        if not old or not new or old == new:
            return

        def move(f: str) -> str:
            if f == old:
                return new
            if f.startswith(old + "/"):
                return new + f[len(old):]
            return f

        self.folders = {move(f) for f in self.folders}
        for p in self.presets.values():
            nf = move(p.folder)
            if nf != p.folder:
                p.folder = nf
                p.touch()

    def remove_folder(self, folder: str) -> int:
        """Удалить папку; её содержимое поднимается на уровень выше.

        Возвращает число перемещённых пресетов.
        """
        folder = normalize_folder(folder)
        if not folder:
            return 0
        parent = folder.rsplit("/", 1)[0] if "/" in folder else ""

        def lift(f: str) -> str:
            if f == folder:
                return parent
            if f.startswith(folder + "/"):
                rest = f[len(folder) + 1:]
                return f"{parent}/{rest}" if parent else rest
            return f

        moved = 0
        for p in self.presets.values():
            nf = lift(p.folder)
            if nf != p.folder:
                p.folder = nf
                p.touch()
                moved += 1
        self.folders = {lift(f) for f in self.folders if f != folder}
        self.folders.discard("")
        return moved

    def folder_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for p in self.presets.values():
            parts = p.folder.split("/") if p.folder else []
            for i in range(1, len(parts) + 1):
                key = "/".join(parts[:i])
                counts[key] = counts.get(key, 0) + 1
        return counts

    # ---- теги ----------------------------------------------------------------------
    def all_tags(self) -> list[tuple[str, int]]:
        counts: dict[str, int] = {}
        for p in self.presets.values():
            for t in p.tags:
                counts[t] = counts.get(t, 0) + 1
        return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))

    # ---- поиск -----------------------------------------------------------------------
    def search(self, query: str = "", *, folder: str | None = None, recursive: bool = True,
               tags: Iterable[str] = (), favorites_only: bool = False,
               sort: str = "name") -> list[Preset]:
        words = [w for w in query.lower().split() if w]
        need_tags = set(normalize_tags(list(tags)))
        folder_n = normalize_folder(folder) if folder is not None else None
        out = []
        for p in self.presets.values():
            if favorites_only and not p.favorite:
                continue
            if folder_n is not None:
                if recursive:
                    if folder_n and not (p.folder == folder_n or p.folder.startswith(folder_n + "/")):
                        continue
                elif p.folder != folder_n:
                    continue
            if need_tags and not need_tags.issubset(p.tags):
                continue
            if words:
                text = preset_search_text(p)
                if not all(w in text for w in words):
                    continue
            out.append(p)
        if sort == "modified":
            out.sort(key=lambda p: p.modified, reverse=True)
        elif sort == "folder":
            out.sort(key=lambda p: (p.folder.lower(), p.name.lower()))
        else:
            out.sort(key=lambda p: (not p.favorite, p.name.lower()))
        return out

    # ---- сет-листы ---------------------------------------------------------------------
    def get_setlist(self, setlist_id: str) -> Setlist | None:
        return next((s for s in self.setlists if s.id == setlist_id), None)

    def add_setlist(self, name: str) -> Setlist:
        s = Setlist(name=name.strip() or "Сет-лист")
        self.setlists.append(s)
        return s

    def remove_setlist(self, setlist_id: str) -> None:
        self.setlists = [s for s in self.setlists if s.id != setlist_id]

    def setlist_presets(self, setlist_id: str) -> list[Preset | None]:
        s = self.get_setlist(setlist_id)
        return [self.presets.get(i) for i in s.items] if s else []


def touch_all(presets: Iterable[Preset]) -> None:
    ts = now_iso()
    for p in presets:
        p.modified = ts
