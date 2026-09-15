"""Perfis de capacidade de memória flash suportados para gravação.

Cobre apenas a capacidade (para padding e limite de tamanho) — sem lógica de
bank-switching/CPLD de placas específicas, que fica fora do escopo do MVP.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FlashProfile:
    name: str
    capacity_bytes: int


FLASH_PROFILES = [
    FlashProfile("29L3211 (4 MB / 32 Mbit)", 4 * 1024 * 1024),
    FlashProfile("1 MB / 8 Mbit", 1 * 1024 * 1024),
    FlashProfile("2 MB / 16 Mbit", 2 * 1024 * 1024),
    FlashProfile("8 MB / 64 Mbit", 8 * 1024 * 1024),
]

DEFAULT_FLASH_PROFILE = FLASH_PROFILES[0]
