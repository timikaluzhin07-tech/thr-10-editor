"""Запуск приложения: Qt, шрифты, тема, бэкенд, QML."""

from __future__ import annotations

import argparse
import logging
import logging.handlers
import os
import sys

from .. import APP_ID, APP_NAME, __version__
from ..app.paths import data_dir

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")


def setup_logging(directory: str, verbose: bool = False) -> str:
    path = os.path.join(directory, "thr10editor.log")
    handler = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=3,
                                                   encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.DEBUG if verbose else logging.INFO)
    root.addHandler(handler)
    if verbose:
        root.addHandler(logging.StreamHandler())
    return path


def parse_args(argv: list[str]) -> argparse.Namespace:
    ap = argparse.ArgumentParser(prog="thr10editor", description=f"{APP_NAME} {__version__}")
    ap.add_argument("--demo", action="store_true", help="сразу включить демо-режим (без комбика)")
    ap.add_argument("--port", default="", help="имя MIDI-порта комбика")
    ap.add_argument("--no-connect", action="store_true", help="не подключаться при старте")
    ap.add_argument("--light", action="store_true", help="светлая тема")
    ap.add_argument("--data-dir", default="", help="папка данных (по умолчанию %%APPDATA%%)")
    ap.add_argument("--selftest", type=float, default=0.0, metavar="SEC",
                    help="загрузить интерфейс, поработать SEC секунд в демо и выйти")
    ap.add_argument("--screenshot", default="", metavar="PNG",
                    help="сохранить снимок окна (вместе с --selftest)")
    ap.add_argument("--size", default="", metavar="WxH", help="размер окна, например 1600x1000")
    ap.add_argument("-v", "--verbose", action="store_true", help="подробный журнал в консоль")
    return ap.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.data_dir:
        os.environ["THR10EDITOR_HOME"] = args.data_dir
    directory = data_dir()
    log_path = setup_logging(directory, args.verbose)
    log = logging.getLogger("thr10editor")
    log.info("%s %s, данные: %s", APP_NAME, __version__, directory)

    # Импорт Qt после настройки окружения.
    from PySide6.QtCore import QCoreApplication, Qt, QTimer, QUrl
    from PySide6.QtGui import QFont, QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterSingletonInstance
    from PySide6.QtQuickControls2 import QQuickStyle

    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    QCoreApplication.setOrganizationName(APP_ID)
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setApplicationVersion(__version__)
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv[:1])
    from .backend_full import FullBackend
    from .theme_provider import ThemeProvider, load_fonts

    families = load_fonts()
    log.info("шрифты: %s", ", ".join(sorted(set(families))) or "встроенные не загружены")
    theme = ThemeProvider()
    app.setFont(QFont(theme.fontFamily, 10))
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icon.png")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    backend = FullBackend(directory)
    theme.setMode("light" if args.light else backend.settings.get("theme", "dark"))
    theme.setZoom(float(backend.settings.get("zoom", 1.0)))
    theme.changed.connect(lambda: backend.settings.set("theme", theme.mode))
    theme.metricsChanged.connect(lambda: backend.settings.set("zoom", theme.zoom, save=False))

    qmlRegisterSingletonInstance(type(theme), "THR10", 1, 0, "Theme", theme)
    qmlRegisterSingletonInstance(type(backend), "THR10", 1, 0, "Backend", backend)
    from .text_input import TextInputGuard

    input_guard = TextInputGuard()
    qmlRegisterSingletonInstance(TextInputGuard, "THR10", 1, 0, "InputGuard", input_guard)

    engine = QQmlApplicationEngine()
    engine.addImportPath(QML_DIR)
    warnings: list[str] = []
    engine.warnings.connect(lambda ws: [warnings.append(w.toString()) for w in ws])
    engine.load(QUrl.fromLocalFile(os.path.join(QML_DIR, "Main.qml")))
    if not engine.rootObjects():
        log.error("QML не загрузился: %s", "\n".join(warnings))
        print("\n".join(warnings), file=sys.stderr)
        return 1
    window = engine.rootObjects()[0]
    input_guard.attach(window)
    if args.size:
        try:
            w, h = (int(x) for x in args.size.lower().split("x"))
            window.setWidth(w)
            window.setHeight(h)
        except ValueError:
            pass

    if args.demo or args.selftest:
        backend.connectDemo()
    elif args.port:
        backend.refreshPorts()
        backend.connectPort(args.port)
    elif not args.no_connect and backend.settings.get("auto_connect", True):
        QTimer.singleShot(300, backend.autoConnect)

    exit_code = {"value": 0}
    if args.selftest:
        from .selftest import run_selftest

        run_selftest(app, backend, theme, window, args.selftest, args.screenshot, warnings,
                     exit_code)

    app.aboutToQuit.connect(backend.shutdown)
    rc = app.exec()
    if warnings:
        for w in warnings:
            log.warning("QML: %s", w)
    log.info("выход, журнал: %s", log_path)
    return exit_code["value"] or rc


if __name__ == "__main__":
    sys.exit(main())
