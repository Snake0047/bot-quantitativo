"""Conto di carta. Nessun ordine reale, per costruzione."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

REGISTRO = Path(__file__).resolve().parent.parent / "dati" / "registro.jsonl"


@dataclass
class Conto:
    contante: float = 10_000.0
    quantita: float = 0.0
    prezzo_ultimo: float = 0.0
    storia: list = field(default_factory=list)

    @property
    def equity(self) -> float:
        return self.contante + self.quantita * self.prezzo_ultimo

    def segna(self, prezzo: float) -> None:
        self.prezzo_ultimo = prezzo

    def porta_a(self, peso: float, prezzo: float, costo_lato: float = 0.001,
                nota: str = "") -> dict | None:
        self.segna(prezzo)
        delta = self.equity * peso / prezzo - self.quantita
        if abs(delta * prezzo) < self.equity * 0.005:
            return None
        self.contante -= delta * prezzo + abs(delta) * prezzo * costo_lato
        self.quantita += delta
        riga = {"quando": datetime.now(timezone.utc).isoformat(),
                "lato": "compra" if delta > 0 else "vendi",
                "quantita": round(abs(delta), 8), "prezzo": prezzo,
                "peso_dopo": round(peso, 4), "equity": round(self.equity, 2),
                "nota": nota}
        self.storia.append(riga)
        REGISTRO.parent.mkdir(parents=True, exist_ok=True)
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(json.dumps(riga, ensure_ascii=False) + "\n")
        return riga

    def stato(self) -> dict:
        return {k: v for k, v in asdict(self).items() if k != "storia"} | {
            "equity": round(self.equity, 2)}
