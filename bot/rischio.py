"""Limiti duri, applicati prima di ogni ordine."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Limiti:
    esposizione_massima: float = 1.0
    perdita_giornaliera: float = 0.03
    drawdown_stop: float = 0.20
    ordini_al_giorno: int = 6


class Bloccato(RuntimeError):
    pass


class Guardia:
    def __init__(self, limiti: Limiti = Limiti()):
        self.l = limiti
        self.picco = 1.0
        self.ordini_oggi = 0
        self.pl_oggi = 0.0
        self.fermo = False

    def nuovo_giorno(self) -> None:
        self.ordini_oggi, self.pl_oggi = 0, 0.0

    def aggiorna(self, equity: float, pl_giorno: float) -> None:
        self.picco = max(self.picco, equity)
        self.pl_oggi = pl_giorno
        if equity / self.picco - 1 <= -self.l.drawdown_stop:
            self.fermo = True

    def filtra(self, voluta: float) -> float:
        if self.fermo:
            raise Bloccato("drawdown oltre il limite: bot fermo")
        if self.pl_oggi <= -self.l.perdita_giornaliera:
            return 0.0
        if self.ordini_oggi >= self.l.ordini_al_giorno:
            raise Bloccato("troppi ordini oggi")
        return max(-self.l.esposizione_massima, min(self.l.esposizione_massima, voluta))

    def registra_ordine(self) -> None:
        self.ordini_oggi += 1
