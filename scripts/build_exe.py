#!/usr/bin/env python3
"""Сборка Windows-приложения через PyInstaller.

Результат (папка dist/):
    THR10Editor.exe  — редактор (один файл, без консоли);
    THR10Probe.exe   — консольная диагностика комбика (tools/thr_probe.py).

Запуск (из корня проекта, в окружении с зависимостями из requirements.txt):
    python scripts/build_exe.py            # обе программы
    python scripts/build_exe.py --editor   # только редактор
    python scripts/build_exe.py --probe    # только диагностика
    python scripts/build_exe.py --onedir   # папка вместо одного файла (быстрее запуск)

После сборки редактор проходит самопроверку (--selftest), если не указан --no-test.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UI = os.path.join(ROOT, "thr10editor", "ui")

# Модули Qt, которые редактору не нужны: без них .exe заметно меньше.
QT_EXCLUDES = [
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtWebChannel", "PySide6.QtWebSockets", "PySide6.Qt3DCore", "PySide6.Qt3DRender",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets", "PySide6.QtPdf",
    "PySide6.QtPdfWidgets", "PySide6.QtQuick3D", "PySide6.QtSql", "PySide6.QtTest",
    "PySide6.QtBluetooth", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtTextToSpeech", "PySide6.QtDesigner", "PySide6.QtHelp",
    "PySide6.QtWidgets", "PySide6.QtPrintSupport", "PySide6.QtSvgWidgets",
    "PySide6.QtOpenGLWidgets", "tkinter", "unittest", "pytest",
]


def run_pyinstaller(args: list[str]) -> None:
    import PyInstaller.__main__

    print("pyinstaller", " ".join(args))
    PyInstaller.__main__.run(args)


# Части Qt, которые не используются (стиль Controls — только Basic): вырезаются
# из сборки, чтобы .exe был меньше и быстрее распаковывался при запуске.
PRUNE_PATTERNS = [
    r"qml[/\\]QtQuick[/\\]Controls[/\\](Material|Universal|Imagine|FluentWinUI3|Fusion|Windows|macOS|iOS)",
    r"qml[/\\]QtQuick[/\\]Dialogs[/\\]quickimpl[/\\]qml[/\\](\+Material|\+Universal|\+Imagine|\+Fusion|\+FluentWinUI3)",
    r"qml[/\\](QtQuick3D|Qt3D|Qt5Compat|QtWayland|QtGraphs|QtCharts|QtDataVisualization|QtWebEngine|QtWebView|QtLocation|QtPositioning|QtMultimedia|QtSensors|QtTextToSpeech|QtTest|QtScxml|QtRemoteObjects|QtWebSockets|QtWebChannel)[/\\]",
    r"QuickControls2(Material|Universal|Imagine|FluentWinUI3|Fusion|WindowsStyle|MacOSStyle|IOSStyle)",
    r"Qt6(Quick3D|3D|Graphs|Charts|DataVisualization|WebEngine|Pdf|LabsStyleKit|Multimedia|Location|Positioning|Sensors|TextToSpeech|Test)",
    r"[/\\]translations[/\\]",
]

SPEC_TEMPLATE = """# -*- mode: python -*-
# Сгенерировано scripts/build_exe.py — не редактировать вручную.
import re
PRUNE = [re.compile(p) for p in {prune!r}]

def keep(entry):
    return not any(p.search(entry[0]) or p.search(entry[1]) for p in PRUNE)

a = Analysis(
    [{entry!r}],
    pathex=[{root!r}],
    datas={datas!r},
    hiddenimports={hidden!r},
    excludes={excludes!r},
    noarchive=False,
)
a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if keep(d)]
pyz = PYZ(a.pure)
{tail}
"""

ONEFILE_TAIL = """exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name='THR10Editor', debug=False,
          strip=False, upx=False, console=False, icon={icon!r})"""

ONEDIR_TAIL = """exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='THR10Editor', debug=False,
          strip=False, upx=False, console=False, icon={icon!r})
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='THR10Editor')"""


def build_editor(mode: str) -> str:
    from PyInstaller.utils.hooks import collect_submodules

    datas = [
        (os.path.join(UI, "qml"), "thr10editor/ui/qml"),
        (os.path.join(UI, "fonts"), "thr10editor/ui/fonts"),
        (os.path.join(UI, "assets"), "thr10editor/ui/assets"),
        (os.path.join(UI, "theme", "tokens.json"), "thr10editor/ui/theme"),
    ]
    sys.path.insert(0, ROOT)
    hidden = ["mido.backends.rtmidi", "rtmidi", *collect_submodules("thr10editor")]
    icon = os.path.join(UI, "assets", "icon.ico")
    tail = (ONEFILE_TAIL if mode == "--onefile" else ONEDIR_TAIL).format(icon=icon)
    spec = SPEC_TEMPLATE.format(prune=PRUNE_PATTERNS, entry=os.path.join(ROOT, "thr10editor", "__main__.py"),
                                root=ROOT, datas=datas, hidden=hidden, excludes=QT_EXCLUDES, tail=tail)
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    spec_path = os.path.join(ROOT, "build", "THR10Editor.spec")
    with open(spec_path, "w", encoding="utf-8") as f:
        f.write(spec)
    run_pyinstaller([spec_path, "--noconfirm", "--clean",
                     "--distpath", os.path.join(ROOT, "dist"),
                     "--workpath", os.path.join(ROOT, "build")])
    exe = "THR10Editor.exe" if os.name == "nt" else "THR10Editor"
    return os.path.join(ROOT, "dist", exe if mode == "--onefile" else os.path.join("THR10Editor", exe))


def build_probe() -> str:
    args = [
        os.path.join(ROOT, "tools", "thr_probe.py"),
        "--name", "THR10Probe",
        "--onefile", "--console", "--noconfirm", "--clean",
        "--icon", os.path.join(UI, "assets", "icon.ico"),
        "--paths", ROOT,
        "--hidden-import", "mido.backends.rtmidi",
        "--hidden-import", "rtmidi",
        "--exclude-module", "PySide6",
        "--exclude-module", "tkinter",
        "--distpath", os.path.join(ROOT, "dist"),
        "--workpath", os.path.join(ROOT, "build"),
        "--specpath", os.path.join(ROOT, "build"),
    ]
    run_pyinstaller(args)
    return os.path.join(ROOT, "dist", "THR10Probe.exe" if os.name == "nt" else "THR10Probe")


def selftest(exe: str) -> int:
    print(f"Самопроверка {exe} …")
    env = dict(os.environ)
    env["THR10EDITOR_HOME"] = os.path.join(ROOT, "build", "selftest-home")
    r = subprocess.run([exe, "--selftest", "3"], env=env, timeout=180)
    print("Самопроверка:", "OK" if r.returncode == 0 else f"ОШИБКА (код {r.returncode}),"
          f" журнал: {env['THR10EDITOR_HOME']}/thr10editor.log")
    return r.returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--editor", action="store_true", help="только редактор")
    ap.add_argument("--probe", action="store_true", help="только диагностика")
    ap.add_argument("--onedir", action="store_true", help="папка вместо одного файла")
    ap.add_argument("--no-test", action="store_true", help="не запускать самопроверку")
    args = ap.parse_args()
    both = not args.editor and not args.probe
    rc = 0
    if args.editor or both:
        exe = build_editor("--onedir" if args.onedir else "--onefile")
        print("Готово:", exe)
        if not args.no_test:
            rc = selftest(exe)
    if args.probe or both:
        print("Готово:", build_probe())
    return rc


if __name__ == "__main__":
    sys.exit(main())
