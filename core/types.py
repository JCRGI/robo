from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EmulatorDevice:
    serial: str
    port: int
    avd: str | None = None
    status: str = "Desligado"


@dataclass(frozen=True)
class ClickMatch:
    x: int
    y: int
    score: float | None = None
