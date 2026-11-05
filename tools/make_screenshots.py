"""Скриншоты и анимированное демо для README (docs/img/).

    python tools/make_screenshots.py            # всё
    python tools/make_screenshots.py --no-gif   # только PNG

Запускает настоящее окно редактора в демо-режиме (без экрана, offscreen),
наполняет библиотеку примерами, рисует картинки для фона/обложки и снимает
экраны. Для GIF нужен Pillow (только для этого инструмента, в программу не
входит): pip install pillow.
"""

import math
import os
import random
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HOME = tempfile.mkdtemp(prefix="thr10shots_")
os.environ["THR10EDITOR_HOME"] = HOME

from PySide6.QtCore import Q_ARG, QMetaObject, QPointF, Qt, QTimer  # noqa: E402
from PySide6.QtGui import (QColor, QImage, QLinearGradient, QPainter, QPainterPath,  # noqa: E402
                           QPen, QRadialGradient)
from PySide6.QtTest import QTest  # noqa: E402

import thr10editor.ui.selftest as selftest  # noqa: E402

OUT = os.path.join(ROOT, "docs", "img")
MAKE_GIF = "--no-gif" not in sys.argv
W, H = 1440, 900


# ---- картинки-примеры (рисуются кодом, без чужих изображений) ----------------------

def night_city(path, w=1920, h=1080):
    img = QImage(w, h, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    sky = QLinearGradient(0, 0, 0, h)
    sky.setColorAt(0, QColor("#070B1E"))
    sky.setColorAt(0.6, QColor("#1B1840"))
    sky.setColorAt(1, QColor("#3A1F3D"))
    p.fillRect(0, 0, w, h, sky)
    rnd = random.Random(7)
    for _ in range(260):
        x, y = rnd.random() * w, rnd.random() * h * 0.6
        a = rnd.randint(60, 220)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, a))
        r = rnd.choice((1.0, 1.4, 2.0))
        p.drawEllipse(QPointF(x, y), r, r)
    glow = QRadialGradient(w * 0.78, h * 0.22, h * 0.25)
    glow.setColorAt(0, QColor(255, 230, 180, 120))
    glow.setColorAt(1, QColor(255, 230, 180, 0))
    p.setBrush(glow)
    p.drawEllipse(QPointF(w * 0.78, h * 0.22), h * 0.25, h * 0.25)
    p.setBrush(QColor("#F4E3C1"))
    p.drawEllipse(QPointF(w * 0.78, h * 0.22), h * 0.06, h * 0.06)
    for layer, (color, base, hmax) in enumerate((("#120F26", 0.62, 0.3), ("#0A0817", 0.72, 0.26))):
        x = 0
        while x < w:
            bw = rnd.randint(60, 150)
            bh = rnd.randint(int(h * 0.08), int(h * hmax))
            top = int(h * base) + int(h * 0.3) - bh
            p.setBrush(QColor(color))
            p.drawRect(x, top, bw, h - top)
            for wy in range(top + 14, h - 20, 22):
                for wx in range(x + 10, x + bw - 12, 18):
                    if rnd.random() < (0.18 if layer else 0.1):
                        p.setBrush(QColor(255, 196, 110, rnd.randint(120, 230)))
                        p.drawRect(wx, wy, 7, 10)
            p.setBrush(QColor(color))
            x += bw + rnd.randint(0, 10)
    p.end()
    img.save(path)
    return path


def cover_art(path, s=800):
    img = QImage(s, s, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QLinearGradient(0, 0, 0, s)
    bg.setColorAt(0, QColor("#16161C"))
    bg.setColorAt(1, QColor("#050507"))
    p.fillRect(0, 0, s, s, bg)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#C8402F"))
    p.drawEllipse(QPointF(s * 0.5, s * 0.42), s * 0.22, s * 0.22)
    pen = QPen(QColor("#E9E2D0"))
    pen.setWidthF(s * 0.006)
    p.setPen(pen)
    for i in range(14):
        y = s * 0.62 + i * s * 0.022
        amp = s * 0.05 * math.exp(-((i - 6) ** 2) / 18)
        line = QPainterPath(QPointF(s * 0.12, y))
        for k in range(1, 61):
            x = s * 0.12 + k * s * 0.76 / 60
            line.lineTo(x, y - amp * math.sin(k / 60 * math.pi) ** 6 * (1 + 0.5 * math.sin(k * 1.7 + i)))
        p.drawPath(line)
    p.end()
    img.save(path)
    return path


def module_art(path, w=900, h=450):
    img = QImage(w, h, QImage.Format.Format_RGB32)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    bg = QLinearGradient(0, 0, w, h)
    bg.setColorAt(0, QColor("#10202A"))
    bg.setColorAt(1, QColor("#1E1030"))
    p.fillRect(0, 0, w, h, bg)
    for j, color in enumerate(("#4FB3BF", "#9B7BE0", "#E9A23B")):
        pen = QPen(QColor(color))
        pen.setWidthF(5)
        p.setPen(pen)
        line = QPainterPath(QPointF(0, h / 2))
        for x in range(0, w + 1, 6):
            y = h / 2 + math.sin(x / (55 + j * 14) + j) * h * (0.28 - j * 0.06) * math.sin(x / w * math.pi)
            line.lineTo(x, y)
        p.drawPath(line)
    p.end()
    img.save(path)
    return path


# ---- сценарий ---------------------------------------------------------------------

PRESETS = [
    # имя, папка, теги, избранное, значения
    ("Glass Chorus", "Чистые", "clean, хорус", True,
     {"amp.model": 0, "amp.gain": 30, "amp.master": 65, "amp.bass": 40, "amp.middle": 52,
      "amp.treble": 66, "amp.cab": 1, "comp.on": 1, "mod.on": 1, "mod.type": 0,
      "mod.chorus.speed": 30, "mod.chorus.depth": 55, "mod.chorus.mix": 45, "delay.on": 1,
      "delay.time": 3800, "delay.feedback": 22, "delay.level": 22, "reverb.on": 1,
      "reverb.type": 2, "reverb.time": 24, "reverb.level": 28, "gate.on": 1}),
    ("Warm Jazz", "Чистые", "clean, джаз", False,
     {"amp.model": 0, "amp.gain": 22, "amp.master": 60, "amp.bass": 62, "amp.middle": 55,
      "amp.treble": 38, "amp.cab": 4, "reverb.on": 1, "reverb.type": 1, "reverb.level": 22}),
    ("Spring Surf", "Чистые", "clean, спринг", False,
     {"amp.model": 0, "amp.gain": 40, "amp.master": 70, "amp.bass": 45, "amp.middle": 40,
      "amp.treble": 75, "amp.cab": 1, "mod.on": 1, "mod.type": 2, "mod.tremolo.freq": 55,
      "mod.tremolo.depth": 50, "reverb.on": 1, "reverb.type": 3, "reverb.spring.reverb": 70}),
    ("Crunch Rhythm", "Перегруз", "crunch, ритм", True,
     {"amp.model": 1, "amp.gain": 58, "amp.master": 62, "amp.bass": 55, "amp.middle": 60,
      "amp.treble": 58, "amp.cab": 3, "reverb.on": 1, "reverb.type": 1, "reverb.level": 18}),
    ("Brit Lead", "Перегруз", "lead, соло", False,
     {"amp.model": 3, "amp.gain": 78, "amp.master": 60, "amp.bass": 50, "amp.middle": 70,
      "amp.treble": 62, "amp.cab": 2, "delay.on": 1, "delay.time": 4200, "delay.level": 30,
      "reverb.on": 1, "reverb.type": 0, "gate.on": 1, "gate.threshold": 40}),
    ("Modern Chug", "Перегруз", "metal, ритм", False,
     {"amp.model": 4, "amp.gain": 85, "amp.master": 55, "amp.bass": 65, "amp.middle": 35,
      "amp.treble": 60, "amp.cab": 0, "gate.on": 1, "gate.threshold": 55, "reverb.on": 0}),
    ("Ambient Swell", "Эмбиент", "эмбиент, дилей", True,
     {"amp.model": 0, "amp.gain": 35, "amp.master": 58, "amp.bass": 45, "amp.middle": 45,
      "amp.treble": 60, "amp.cab": 1, "comp.on": 1, "mod.on": 1, "mod.type": 3,
      "delay.on": 1, "delay.time": 6200, "delay.feedback": 55, "delay.level": 40,
      "reverb.on": 1, "reverb.type": 0, "reverb.time": 80, "reverb.level": 55}),
    ("Acoustic Strum", "Акустика", "aco", False,
     {"amp.model": 6, "amp.gain": 50, "amp.master": 60, "amp.bass": 48, "amp.middle": 50,
      "amp.treble": 58, "comp.on": 1, "reverb.on": 1, "reverb.type": 1, "reverb.level": 25}),
]


def items(window):
    out, stack = [], [window.contentItem()]
    while stack:
        it = stack.pop()
        out.append(it)
        stack.extend(it.childItems())
    return out


def by_class(window, prefix):
    return [o for o in items(window) if o.metaObject().className().startswith(prefix)]


def stage(window, on=True):
    if on:
        QMetaObject.invokeMethod(window, "startStage", Q_ARG("QVariant", 0))
    else:
        QMetaObject.invokeMethod(window, "stopStage")
    # без настоящего экрана «во весь экран» = 800×800; держим размер окна
    QTest.qWait(50)
    window.showNormal()
    window.resize(W, H)


def run(app, backend, theme, window, seconds, screenshot, warnings, exit_code):
    from thr10editor.model.preset import Preset
    from thr10editor.protocol.params import default_values

    os.makedirs(OUT, exist_ok=True)
    art = os.path.join(HOME, "art")
    os.makedirs(art, exist_ok=True)

    def shot(name):
        QTest.qWait(450)
        window.grabWindow().save(os.path.join(OUT, name))
        print("  ", name)

    def go():
        ids = {}
        for name, folder, tags, fav, vals in PRESETS:
            backend.load_preset(Preset(name, dict(default_values(), **vals)))
            backend.saveCurrentAs(name, folder, tags, fav, "")
            ids[name] = backend.currentPresetId
        for name in ("Glass Chorus", "Crunch Rhythm", "Brit Lead", "Ambient Swell"):
            backend.addToSetlist(ids[name])
        backend.setTrackText(0, "tuning", "Standard E")
        backend.setTrackText(0, "chords", "Куплет:  Am – F – C – G\nПрипев:  F – G – Am")
        backend.setTrackMedia(0, "background", night_city(os.path.join(art, "night.png")))
        backend.setTrackMedia(0, "cover", cover_art(os.path.join(art, "cover.png")))
        backend.setTrackText(1, "tuning", "Drop D")
        backend.setModuleMedia("mod", module_art(os.path.join(art, "waves.png")))
        backend.loadPreset(ids["Glass Chorus"])
        for t in by_class(window, "Toasts"):  # без всплывающих сообщений на снимках
            t.setVisible(False)
        sidebar = by_class(window, "Sidebar")[0]
        tools = by_class(window, "ToolsPanel")[0]

        # главное окно — тёмная и светлая темы
        shot("main.png")
        theme.setMode("light")
        shot("light.png")
        theme.setMode("dark")

        # сет-лист и морфинг
        sidebar.setProperty("currentIndex", 2)
        tools.setProperty("currentIndex", 1)
        shot("setlist.png")
        # LFO
        backend.addLfo("amp.treble")
        tools.setProperty("currentIndex", 2)
        shot("lfo.png")
        sidebar.setProperty("currentIndex", 0)
        tools.setProperty("currentIndex", 0)

        # сцена: фон, обложка, строй, аккорды
        stage(window)
        shot("stage.png")
        stage(window, False)
        QTest.qWait(400)

        if MAKE_GIF:
            make_gif(app, backend, window, ids, sidebar)

    def safe():
        try:
            go()
        except Exception:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            exit_code["value"] = 1
        app.quit()

    QTimer.singleShot(1200, safe)


def make_gif(app, backend, window, ids, sidebar):
    from PIL import Image

    frames: list[tuple[Image.Image, int]] = []

    def grab(ms):
        img = window.grabWindow().convertToFormat(QImage.Format.Format_RGB888)
        img = img.scaled(960, 600, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation)
        ptr = img.constBits()
        pil = Image.frombuffer("RGB", (img.width(), img.height()), bytes(ptr), "raw", "RGB",
                               img.bytesPerLine(), 1)
        frames.append((pil.copy(), ms))

    def record(seconds, step=60):
        t = 0
        while t < seconds * 1000:
            QTest.qWait(step)
            grab(step)
            t += step

    print("   demo.gif …")
    grab(1400)
    for name in ("Crunch Rhythm", "Brit Lead", "Ambient Swell", "Glass Chorus"):
        backend.loadPreset(ids[name])
        record(0.5)
        frames[-1] = (frames[-1][0], 700)
    for _ in range(2):  # рандомайзер
        backend.randomize()
        record(0.4)
        frames[-1] = (frames[-1][0], 600)
    backend.undo()
    backend.undo()
    record(0.4)
    sidebar.setProperty("currentIndex", 2)
    record(0.4)
    frames[-1] = (frames[-1][0], 900)
    stage(window)
    record(0.6)
    frames[-1] = (frames[-1][0], 1800)
    backend.stageNext()
    record(0.4)
    frames[-1] = (frames[-1][0], 1000)
    stage(window, False)
    record(0.5)
    frames[-1] = (frames[-1][0], 1200)

    # одинаковые кадры подряд склеиваются, общая палитра — меньше размер
    merged: list[list] = []
    for img, ms in frames:
        if merged and img.tobytes() == merged[-1][0].tobytes():
            merged[-1][1] += ms
        else:
            merged.append([img, ms])
    palette = merged[0][0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    images = [m[0].quantize(palette=palette, dither=Image.Dither.NONE) for m in merged]
    images[0].save(os.path.join(OUT, "demo.gif"), save_all=True, append_images=images[1:],
                   duration=[m[1] for m in merged], loop=0, optimize=True, disposal=1)
    print(f"   demo.gif: {len(images)} кадров, "
          f"{os.path.getsize(os.path.join(OUT, 'demo.gif')) / 1e6:.1f} МБ")


selftest.run_selftest = run
from thr10editor.ui.app import main  # noqa: E402

try:
    code = main(["--selftest", "1", "--size", f"{W}x{H}"])
finally:
    shutil.rmtree(HOME, ignore_errors=True)
sys.exit(code)
