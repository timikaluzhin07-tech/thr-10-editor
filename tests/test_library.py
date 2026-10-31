import json

import pytest

from thr10editor.model.library import Library
from thr10editor.model.preset import Preset
from thr10editor.protocol.params import default_values


def P(name, folder="", tags=(), fav=False, **vals):
    v = default_values()
    v.update({k.replace("__", "."): x for k, x in vals.items()})
    return Preset(name, v, folder=folder, tags=list(tags), favorite=fav)


@pytest.fixture
def lib(tmp_path):
    lib = Library(str(tmp_path / "library.json"))
    lib.add(P("Clean Funk", "Live/Funk", ["clean", "funk"], amp__model=0))
    lib.add(P("Lead Solo", "Live/Rock", ["lead"], True, amp__model=2, delay__on=1))
    lib.add(P("Bass DI", "Studio", ["bass"], amp__model=5))
    lib.add(P("Crunch Rhythm", "Live", ["crunch", "rhythm"], amp__model=1))
    return lib


def test_unlimited_and_persist(tmp_path):
    lib = Library(str(tmp_path / "l.json"))
    for i in range(1500):
        lib.add(P(f"P{i}"))
    lib.save()
    again = Library(str(tmp_path / "l.json"))
    assert len(again) == 1500


def test_search_words_and_fields(lib):
    names = lambda ps: [p.name for p in ps]  # noqa: E731
    assert names(lib.search("lead")) == ["Lead Solo"]
    assert names(lib.search("live funk")) == ["Clean Funk"]
    assert names(lib.search("дилей")) == ["Lead Solo"]  # по включённым блокам
    assert names(lib.search("brit")) == []
    assert names(lib.search("CRUNCH")) == ["Crunch Rhythm"]  # модель усилителя/имя, регистр


def test_search_folder_recursive(lib):
    assert {p.name for p in lib.search(folder="Live")} == {"Clean Funk", "Lead Solo", "Crunch Rhythm"}
    assert [p.name for p in lib.search(folder="Live", recursive=False)] == ["Crunch Rhythm"]
    assert len(lib.search(folder="")) == 4


def test_search_tags_and_favorites(lib):
    assert [p.name for p in lib.search(tags=["lead"])] == ["Lead Solo"]
    assert [p.name for p in lib.search(favorites_only=True)] == ["Lead Solo"]
    assert lib.search(tags=["clean", "lead"]) == []
    # избранное — первым при сортировке по имени
    assert lib.search()[0].name == "Lead Solo"


def test_folders(lib):
    assert lib.all_folders() == ["Live", "Live/Funk", "Live/Rock", "Studio"]
    lib.add_folder("Empty/Sub")
    assert "Empty" in lib.all_folders() and "Empty/Sub" in lib.all_folders()
    lib.rename_folder("Live", "Stage")
    assert {p.folder for p in lib.presets.values()} == {"Stage/Funk", "Stage/Rock", "Studio", "Stage"}
    moved = lib.remove_folder("Stage/Funk")
    assert moved == 1
    assert next(p for p in lib.presets.values() if p.name == "Clean Funk").folder == "Stage"
    lib.remove_folder("Stage")
    assert next(p for p in lib.presets.values() if p.name == "Lead Solo").folder == "Rock"
    assert lib.folder_counts()["Rock"] == 1


def test_tags_counts(lib):
    tags = dict(lib.all_tags())
    assert tags["lead"] == 1 and tags["clean"] == 1


def test_crud(lib):
    p = next(iter(lib.presets.values()))
    lib.rename(p.id, "Renamed")
    lib.set_tags(p.id, "a, b")
    lib.set_folder(p.id, "X/Y")
    assert lib.toggle_favorite(p.id) is True
    q = lib.get(p.id)
    assert (q.name, q.tags, q.folder, q.favorite) == ("Renamed", ["a", "b"], "X/Y", True)
    d = lib.duplicate(p.id)
    assert d.id != p.id and d.name.endswith("(копия)")
    assert lib.remove(p.id) and not lib.remove(p.id)


def test_setlists_follow_deletions(lib):
    ids = list(lib.presets)
    s = lib.add_setlist("Гиг")
    s.items = [ids[0], ids[1], ids[0]]
    lib.remove(ids[0])
    assert s.items == [ids[1]]
    assert [p.name for p in lib.setlist_presets(s.id)] == ["Lead Solo"]
    lib.remove_setlist(s.id)
    assert lib.setlists == []


def test_load_corrupt_file(tmp_path):
    path = tmp_path / "library.json"
    path.write_text("{broken")
    lib = Library(str(path))
    assert len(lib) == 0
    assert (tmp_path / "library.json.broken").exists()


def test_roundtrip_with_setlists(lib, tmp_path):
    s = lib.add_setlist("A")
    s.items = list(lib.presets)[:2]
    lib.save()
    again = Library(lib.path)
    assert [x.name for x in again.setlists] == ["A"]
    assert again.setlists[0].items == s.items
    doc = json.loads(open(lib.path, encoding="utf-8").read())
    assert doc["format"] == "thr10editor.library"


def test_add_existing_id_copies(lib):
    p = next(iter(lib.presets.values()))
    q = lib.add(p)
    assert q.id != p.id and len(lib) == 5
