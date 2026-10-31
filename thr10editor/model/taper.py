"""Шкала ручки: значение ↔ положение 0..1 (линейная или логарифмическая).

Используется ручками, рандомайзером, морфингом и LFO, чтобы частоты и
времена менялись «музыкально» (равномерно на слух, а не в герцах).
"""

from __future__ import annotations

import math

from ..protocol.params import ParamDef

LOG_TAPER = frozenset({"delay.time", "delay.highcut", "delay.lowcut", "reverb.time",
                       "reverb.pre", "reverb.lowcut", "reverb.highcut"})


def to_position(p: ParamDef, value: float) -> float:
    if p.span == 0:
        return 0.0
    value = min(max(value, p.minimum), p.maximum)
    if p.key in LOG_TAPER and p.minimum > 0:
        return math.log(value / p.minimum) / math.log(p.maximum / p.minimum)
    return (value - p.minimum) / p.span


def from_position(p: ParamDef, x: float) -> int:
    x = max(0.0, min(1.0, x))
    if p.key in LOG_TAPER and p.minimum > 0:
        return p.clamp(p.minimum * (p.maximum / p.minimum) ** x)
    return p.clamp(p.minimum + x * p.span)
