"""Пресет редактора: значения + метаданные библиотеки (папка, теги, избранное)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping

from ..protocol.params import normalize_values
from ..protocol.patch import decode_patch, encode_patch

PRESET_FORMAT = "thr10editor.preset"
PRESET_FORMAT_VERSION = 1


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id() -> str:
    return uuid.uuid4().hex


def normalize_folder(folder: str) -> str:
    parts = [p.strip() for p in str(folder).replace("\\", "/").split("/")]
    return "/".join(p for p in parts if p)


def normalize_tags(tags: Any) -> list[str]:
    if isinstance(tags, str):
        tags = tags.split(",")
    out: list[str] = []
    for t in tags or []:
        t = str(t).strip().lower()
        if t and t not in out:
            out.append(t)
    return out


@dataclass
class Preset:
    name: str
    values: dict[str, int]
    id: str = field(default_factory=new_id)
    folder: str = ""
    tags: list[str] = field(default_factory=list)
    favorite: bool = False
    notes: str = ""
    created: str = field(default_factory=now_iso)
    modified: str = field(default_factory=now_iso)
    source: str = ""

    def __post_init__(self) -> None:
        self.values = normalize_values(self.values)
        self.folder = normalize_folder(self.folder)
        self.tags = normalize_tags(self.tags)
        self.name = str(self.name).strip() or "Без имени"

    # ---- сериализация --------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "folder": self.folder,
            "tags": list(self.tags),
            "favorite": self.favorite,
            "notes": self.notes,
            "created": self.created,
            "modified": self.modified,
            "source": self.source,
            "values": dict(self.values),
        }

    @classmethod
    def from_dict(cls, d: Mapping[str, Any]) -> "Preset":
        if not isinstance(d, Mapping):
            raise ValueError("пресет должен быть объектом")
        values = d.get("values")
        if not isinstance(values, Mapping):
            raise ValueError("в пресете нет значений")
        clean = {}
        for k, v in values.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                clean[str(k)] = int(v)
            elif isinstance(v, bool):
                clean[str(k)] = int(v)
        return cls(
            name=str(d.get("name", "")),
            values=clean,
            id=str(d.get("id") or new_id()),
            folder=str(d.get("folder", "")),
            tags=normalize_tags(d.get("tags", [])),
            favorite=bool(d.get("favorite", False)),
            notes=str(d.get("notes", "")),
            created=str(d.get("created") or now_iso()),
            modified=str(d.get("modified") or now_iso()),
            source=str(d.get("source", "")),
        )

    def to_file_dict(self) -> dict[str, Any]:
        return {"format": PRESET_FORMAT, "version": PRESET_FORMAT_VERSION, "preset": self.to_dict()}

    @classmethod
    def from_file_dict(cls, d: Mapping[str, Any]) -> "Preset":
        if d.get("format") != PRESET_FORMAT:
            raise ValueError("это не файл пресета THR10 Editor")
        return cls.from_dict(d.get("preset", {}))

    # ---- THR -----------------------------------------------------------------
    def to_patch(self) -> bytes:
        return encode_patch(self.name, self.values)

    @classmethod
    def from_patch(cls, patch: bytes, *, name: str | None = None, source: str = "",
                   base: Mapping[str, int] | None = None) -> "Preset":
        decoded = decode_patch(patch, base)
        return cls(name=name or decoded.name or "Без имени", values=decoded.values, source=source)

    def copy(self, *, new_identity: bool = False) -> "Preset":
        p = Preset.from_dict(self.to_dict())
        if new_identity:
            p.id = new_id()
            p.created = p.modified = now_iso()
        return p

    def touch(self) -> None:
        self.modified = now_iso()
