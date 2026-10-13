"""Apenas limites de datas. Não implementa contagens, DAX ou filtros do PBIX."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import re


@dataclass(frozen=True, order=True)
class Quarter:
    year: int
    number: int

    def __post_init__(self) -> None:
        if type(self.year) is not int or not 2 <= self.year <= 9998:
            raise ValueError("Ano fora do intervalo suportado.")
        if type(self.number) is not int or not 1 <= self.number <= 4:
            raise ValueError("Trimestre inválido.")

    @classmethod
    def parse(cls, label: str) -> Quarter:
        match = re.fullmatch(r"Q([1-4])-(\d{4})", label)
        if match is None:
            raise ValueError("Use um trimestre como Q4-2026.")
        return cls(int(match[2]), int(match[1]))

    @property
    def label(self) -> str:
        return f"Q{self.number}-{self.year:04d}"

    @property
    def start(self) -> date:
        return date(self.year, 3 * (self.number - 1) + 1, 1)

    def shift(self, offset: int) -> Quarter:
        index = self.year * 4 + self.number - 1 + offset
        return Quarter(index // 4, index % 4 + 1)

    @property
    def end_exclusive(self) -> date:
        return self.shift(1).start


def comparison_windows(label: str) -> list[dict[str, str]]:
    """Previous e LY completos, sem corte pela data do servidor."""
    quarter = Quarter.parse(label)
    result = []
    for period, value in (
        ("Current", quarter),
        ("Previous", quarter.shift(-1)),
        ("LY", quarter.shift(-4)),
    ):
        end = value.end_exclusive
        result.append({
            "Período": period,
            "Trimestre": value.label,
            "Início inclusivo": value.start.isoformat(),
            "Fim inclusivo": (end - timedelta(days=1)).isoformat(),
            "Fim exclusivo": end.isoformat(),
        })
    return result
