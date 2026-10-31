import pytest

from fixtures import s3_patch, s3_ydl
from thr10editor.protocol import constants as C
from thr10editor.protocol.files import (
    FileFormatError,
    read_any,
    read_single,
    read_syx,
    read_ydl,
    write_syx,
    write_ydl,
)
from thr10editor.protocol.params import default_values
from thr10editor.protocol.patch import encode_patch


def test_read_real_s3_ydl():
    data = s3_ydl()
    assert len(data) == 535  # как в patches.h
    patches = read_ydl(data)
    assert [p.name for p in patches] == ["model1", "model2"]
    assert patches[0].patch == s3_patch("model1")


def test_ydl_roundtrip_and_padding():
    a = encode_patch("A", default_values())
    b = encode_patch("B", dict(default_values(), **{"amp.model": 4}))
    data = write_ydl([a, b])
    assert len(data) == 13 + 100 * 261
    assert data.startswith(b"DTAB01d")
    back = read_ydl(data)
    assert [p.patch for p in back] == [a, b]
    assert len(read_ydl(data, skip_empty=False)) == 100


def test_ydl_no_padding():
    a = encode_patch("A", default_values())
    assert len(write_ydl([a], pad_to=None)) == 13 + 261


def test_ydl_too_many():
    with pytest.raises(FileFormatError):
        write_ydl([bytes(256)] * 101)


def test_ydl_bad_magic():
    with pytest.raises(FileFormatError):
        read_ydl(b"XXXX" + bytes(300))


def test_syx_roundtrip():
    a = encode_patch("One", default_values())
    data = write_syx([a, a])
    assert len(data) == 2 * 276
    out = read_syx(data)
    assert len(out) == 2 and out[0].name == "One" and out[0].patch == a


def test_syx_bad_checksum():
    data = bytearray(write_syx([bytes(256)]))
    data[-2] ^= 1
    with pytest.raises(FileFormatError):
        read_syx(bytes(data))


def test_syx_without_dumps():
    with pytest.raises(FileFormatError):
        read_syx(b"\xf0\x43\x7d\x60\x44\x54\x41\x31\xf7")


def test_single_file():
    patch = s3_patch("model2")
    data = b"DTA" + bytes(6) + patch
    assert len(data) == C.SINGLE_FILE_SIZE
    assert read_single(data)[0].name == "model2"
    fmt, items = read_any(data)
    assert fmt == "single" and items[0].patch == patch


def test_read_any():
    assert read_any(s3_ydl())[0] == "ydl"
    assert read_any(write_syx([bytes(256)]))[0] == "syx"
    with pytest.raises(FileFormatError):
        read_any(b"hello")
