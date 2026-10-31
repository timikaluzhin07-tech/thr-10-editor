#!/usr/bin/env python3
"""Диагностика THR10 на реальном железе.

Что делает (всё пишет в лог-файл):
  1. показывает все MIDI-порты и находит порт THR10;
  2. слушает heartbeat и определяет модель;
  3. запрашивает текущее состояние и расшифровывает все параметры;
  4. безопасно меняет ОДИН параметр (по умолчанию Master) на −5 (тише),
     проверяет, что комбик принял значение, и возвращает исходное;
  5. по желанию слушает порт N секунд (крутите ручки на комбике).

На комбик уходят только: запрос состояния и изменение выбранного
параметра (каждое сообщение проходит SafetyGate). Никаких дампов,
системных команд, прошивки или сброса. Исходное значение возвращается
в любом случае, даже при Ctrl+C.

Примеры:
    python tools/thr_probe.py                  # автопоиск порта, тест Master
    python tools/thr_probe.py --list           # только список портов
    python tools/thr_probe.py --no-change      # только чтение состояния
    python tools/thr_probe.py --listen 30      # потом 30 с слушать ручки
    python tools/thr_probe.py --port "THR10" --param amp.gain --delta 3
    python tools/thr_probe.py --demo           # проверка самого скрипта без комбика

Коды выхода: 0 — всё в порядке; 1 — порт не найден/не открылся;
2 — комбик не ответил; 3 — значение не подтвердилось.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import platform
import sys
import time
from typing import Callable, TextIO

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from thr10editor import __version__  # noqa: E402
from thr10editor.protocol.params import PARAMS, Kind  # noqa: E402
from thr10editor.protocol.patch import decode_patch  # noqa: E402
from thr10editor.protocol.sysex import (  # noqa: E402
    Heartbeat,
    ParamChange,
    PatchDump,
    decode,
    encode_dump_request,
    encode_param,
    hexstr,
)
from thr10editor.transport.base import Transport, TransportError  # noqa: E402

EXIT_OK, EXIT_PORT, EXIT_NO_RESPONSE, EXIT_MISMATCH = 0, 1, 2, 3


class Log:
    def __init__(self, stream: TextIO | None, echo: bool = True):
        self.stream = stream
        self.echo = echo
        self.t0 = time.monotonic()

    def __call__(self, msg: str = "") -> None:
        line = f"[{time.monotonic() - self.t0:8.3f}] {msg}"
        if self.stream:
            self.stream.write(line + "\n")
            self.stream.flush()
        if self.echo:
            print(line)


def describe(raw: bytes, values: dict[str, int] | None = None) -> str:
    m = decode(raw)
    if isinstance(m, Heartbeat):
        return f"heartbeat, модель {m.model}"
    if isinstance(m, PatchDump):
        return f"дамп пресета «{decode_patch(m.patch).name}», сумма {'OK' if m.checksum_ok else 'НЕВЕРНА'}"
    if isinstance(m, ParamChange):
        p = m.resolve(values or {})
        if p is None:
            return f"изменение параметра: НЕИЗВЕСТНЫЙ адрес 0x{m.address:02X} = {m.value}"
        return f"изменение параметра {p.key} = {m.value} ({p.format(p.from_raw(m.value))})"
    return type(m).__name__ + (f": {m.reason}" if hasattr(m, "reason") else "")


class Probe:
    def __init__(self, transport: Transport, log: Log, *,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.t = transport
        self.log = log
        self.clock = clock
        self.sleep = sleep
        self.values: dict[str, int] = {}
        self.model = ""

    def send(self, msg: bytes) -> None:
        self.log(f"→ {hexstr(msg)}   [{describe(msg, self.values)}]")
        self.t.send(msg)

    def pump(self, seconds: float, until: Callable[[bytes], bool] | None = None,
             quiet_heartbeat: bool = True) -> bytes | None:
        end = self.clock() + seconds
        while self.clock() < end:
            for raw in self.t.poll():
                m = decode(raw)
                if isinstance(m, Heartbeat):
                    if m.model != self.model:
                        self.model = m.model
                        self.log(f"← {hexstr(raw)}   [{describe(raw)}]")
                    elif not quiet_heartbeat:
                        self.log(f"← heartbeat {m.model}")
                else:
                    self.log(f"← {hexstr(raw)}   [{describe(raw, self.values)}]")
                if until is not None and until(raw):
                    return raw
            self.sleep(0.005)
        return None

    def read_state(self, timeout: float = 3.0) -> dict[str, int] | None:
        self.send(encode_dump_request())
        raw = self.pump(timeout, until=lambda r: isinstance(decode(r), PatchDump))
        if raw is None:
            return None
        m = decode(raw)
        if not m.checksum_ok:
            self.log("ВНИМАНИЕ: контрольная сумма дампа не сошлась")
        d = decode_patch(m.patch, base=self.values or None)
        for w in d.warnings:
            self.log(f"ВНИМАНИЕ: {w}")
        self.values = d.values
        return d.values

    def print_state(self, values: dict[str, int]) -> None:
        self.log("Текущее состояние (сырое значение → отображение):")
        for key, p in PARAMS.items():
            mark = "" if p.is_active(values) else "   (неактивен при текущем типе)"
            self.log(f"   {key:24s} 0x{p.address:02X}  {values[key]:5d}  →  {p.format(values[key])}{mark}")


def run_probe(transport: Transport, log: Log, *, param: str = "amp.master", delta: int = -5,
              change: bool = True, listen: float = 0.0,
              clock: Callable[[], float] = time.monotonic,
              sleep: Callable[[float], None] = time.sleep) -> int:
    probe = Probe(transport, log, clock=clock, sleep=sleep)
    p = PARAMS[param]
    if p.kind is not Kind.RANGE:
        log(f"Параметр {param} не является ручкой — выберите другой")
        return EXIT_PORT

    log("Шаг 1. Жду heartbeat (до 2 с)…")
    probe.pump(2.0, until=lambda r: isinstance(decode(r), Heartbeat))
    log(f"   модель: {probe.model or 'heartbeat не получен (это не обязательно ошибка)'}")

    log("Шаг 2. Запрашиваю текущее состояние…")
    values = probe.read_state()
    if values is None:
        log("ОШИБКА: комбик не прислал дамп в ответ на запрос. Проверьте питание, кабель,"
            " драйвер и что порт не занят официальным THR Editor.")
        return EXIT_NO_RESPONSE
    probe.print_state(values)

    result = EXIT_OK
    if change:
        if not p.is_active(values):
            log(f"Параметр {param} неактивен при текущем типе эффекта — пропускаю изменение")
        else:
            original = values[param]
            target = p.clamp(original + delta)
            if target == original:
                target = p.clamp(original - delta)
            log(f"Шаг 3. Меняю {param}: {original} → {target} ({p.format(target)})")
            try:
                probe.send(encode_param(p, target))
                probe.pump(0.6)
                after = probe.read_state()
                if after is None:
                    log("ОШИБКА: после изменения комбик не ответил на запрос состояния")
                    result = EXIT_NO_RESPONSE
                elif after[param] != target:
                    log(f"ОШИБКА: ожидалось {target}, комбик сообщает {after[param]}")
                    result = EXIT_MISMATCH
                else:
                    log(f"   OK: комбик принял {param} = {target}")
            finally:
                log(f"Шаг 4. Возвращаю {param} = {original}")
                probe.send(encode_param(p, original))
                probe.pump(0.6)
                back = probe.read_state()
                if back is None:
                    log("ОШИБКА: не удалось проверить возврат значения — проверьте ручку вручную")
                    result = result or EXIT_NO_RESPONSE
                elif back[param] != original:
                    log(f"ОШИБКА: значение не вернулось ({back[param]} вместо {original})")
                    result = result or EXIT_MISMATCH
                else:
                    log(f"   OK: {param} снова {original}")

    if listen > 0:
        log(f"Шаг 5. Слушаю {listen:.0f} с — покрутите ручки и понажимайте кнопки на комбике…")
        probe.pump(listen)
    log("Итог: " + {EXIT_OK: "всё в порядке", EXIT_NO_RESPONSE: "комбик не ответил",
                     EXIT_MISMATCH: "значение не подтвердилось"}.get(result, str(result)))
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true", help="показать MIDI-порты и выйти")
    ap.add_argument("--port", default="", help="имя порта (вход и выход), по умолчанию — автопоиск")
    ap.add_argument("--in-port", default="", help="имя входного порта, если отличается")
    ap.add_argument("--out-port", default="", help="имя выходного порта, если отличается")
    ap.add_argument("--param", default="amp.master", help="какой параметр менять (ручка)")
    ap.add_argument("--delta", type=int, default=-5,
                    help="на сколько изменить (по умолчанию −5: тише; если упёрлось в минимум — +5)")
    ap.add_argument("--no-change", action="store_true", help="ничего не менять, только читать")
    ap.add_argument("--listen", type=float, default=0.0, metavar="SEC", help="потом слушать SEC секунд")
    ap.add_argument("--log", default="", help="файл лога (по умолчанию thr_probe_<время>.log)")
    ap.add_argument("--demo", action="store_true", help="прогон на демо-комбике (без железа)")
    args = ap.parse_args(argv)

    log_path = args.log or f"thr_probe_{dt.datetime.now():%Y%m%d_%H%M%S}.log"
    with open(log_path, "w", encoding="utf-8") as f:
        log = Log(f)
        log(f"thr_probe {__version__}; Python {platform.python_version()}; {platform.platform()}")
        log(f"Лог: {os.path.abspath(log_path)}")

        if args.demo:
            from thr10editor.transport.demo import DemoTransport

            transport: Transport = DemoTransport()
        else:
            from thr10editor.transport.midi import MidiTransport, PortPair, find_thr_ports, list_ports

            try:
                ins, outs = list_ports()
            except TransportError as e:
                log(f"ОШИБКА: {e}")
                return EXIT_PORT
            log("MIDI-входы:  " + (", ".join(ins) or "(нет)"))
            log("MIDI-выходы: " + (", ".join(outs) or "(нет)"))
            if args.list:
                return EXIT_OK
            if args.port or args.in_port or args.out_port:
                pair = PortPair(args.in_port or args.port, args.out_port or args.port)
            else:
                pair = find_thr_ports(ins, outs)
            if pair is None:
                log("ОШИБКА: порт THR не найден. Включите комбик, проверьте драйвер Yamaha Steinberg"
                    " USB и закройте официальный THR Editor. Или укажите --port.")
                return EXIT_PORT
            log(f"Порт: вход «{pair.input}», выход «{pair.output}»")
            transport = MidiTransport(pair)
        try:
            transport.open()
        except TransportError as e:
            log(f"ОШИБКА: {e}")
            return EXIT_PORT
        try:
            return run_probe(transport, log, param=args.param, delta=args.delta,
                             change=not args.no_change, listen=args.listen)
        except KeyboardInterrupt:
            log("Прервано пользователем")
            return EXIT_OK
        except TransportError as e:
            log(f"ОШИБКА связи: {e}")
            return EXIT_NO_RESPONSE
        finally:
            transport.close()
            log(f"Готово. Пришлите этот лог при ошибке: {os.path.abspath(log_path)}")


if __name__ == "__main__":
    sys.exit(main())
