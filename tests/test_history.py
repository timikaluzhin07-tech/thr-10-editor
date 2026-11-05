from thr10editor.model.history import History


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_undo_redo_basic():
    h = History(clock=Clock())
    h.record({"a": (1, 2)}, "a")
    h.record({"b": (5, 6)}, "b")
    s = h.undo()
    assert s.values == {"b": 5} and s.label == "b"
    s = h.undo()
    assert s.values == {"a": 1}
    assert h.undo() is None
    assert h.redo().values == {"a": 2}
    assert h.redo().values == {"b": 6}
    assert h.redo() is None


def test_gesture_merges_into_one_step_until_sealed():
    c = Clock()
    h = History(clock=c)
    for v in range(1, 50):
        c.t += 0.05
        h.record({"gain": (v - 1, v)}, "Gain", merge_key="g1")
    h.seal()
    assert len(h) == 1
    assert h.undo().values == {"gain": 0}
    assert h.redo().values == {"gain": 49}


def test_merge_respects_window_and_key():
    c = Clock()
    h = History(clock=c, merge_window=0.5)
    h.record({"x": (0, 1)}, "x", merge_key="k:x")
    c.t = 0.3
    h.record({"x": (1, 2)}, "x", merge_key="k:x")
    c.t = 1.0
    h.record({"x": (2, 3)}, "x", merge_key="k:x")  # окно истекло
    c.t = 1.1
    h.record({"y": (0, 1)}, "y", merge_key="k:y")  # другой ключ
    assert len(h) == 3


def test_merge_back_to_original_drops_entry():
    c = Clock()
    h = History(clock=c)
    h.record({"x": (0, 5)}, "x", merge_key="g")
    h.record({"x": (5, 0)}, "x", merge_key="g")
    assert len(h) == 0 and not h.can_undo


def test_new_record_clears_redo():
    h = History(clock=Clock())
    h.record({"a": (1, 2)}, "a")
    h.undo()
    assert h.can_redo
    h.record({"b": (1, 2)}, "b")
    assert not h.can_redo


def test_limit():
    h = History(limit=10, clock=Clock())
    for i in range(30):
        h.record({"a": (i, i + 1)}, str(i))
    assert len(h) == 10
    assert h.undo().label == "29"


def test_name_changes():
    h = History(clock=Clock())
    h.record({"a": (1, 2)}, "load", name=("Old", "New"))
    s = h.undo()
    assert s.name == "Old" and s.values == {"a": 1}
    assert h.redo().name == "New"
    h.record({}, "noop", name=("X", "X"))
    assert len(h) == 1


def test_labels():
    h = History(clock=Clock())
    assert h.undo_label == "" and h.redo_label == ""
    h.record({"a": (1, 2)}, "Gain")
    assert h.undo_label == "Gain"
    h.undo()
    assert h.redo_label == "Gain"
