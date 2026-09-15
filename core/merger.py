"""Merge sequencial de ROMs SNES em uma única imagem para gravação em flash."""

from __future__ import annotations

from dataclasses import dataclass

from core.rom import SNESRom
from core.validator import ValidationMessage, validate
from devices.flash_profiles import FlashProfile

PADDING_BYTE = 0xFF


@dataclass
class MergeReport:
    messages: list[ValidationMessage]
    rom_offsets: list[tuple[str, int, int]]  # (filename, offset, size)
    total_roms_size: int
    padding_size: int
    output_size: int


def merge(roms: list[SNESRom], flash_profile: FlashProfile) -> tuple[bytes, MergeReport]:
    """Corrige o checksum de cada ROM (na ordem informada) e concatena.

    Cada ROM mantém seu próprio checksum interno corrigido; o restante da
    capacidade da flash é preenchido com 0xFF (nunca com 0x00).
    """
    messages = validate(roms, flash_profile)

    output = bytearray()
    rom_offsets: list[tuple[str, int, int]] = []

    for rom in roms:
        offset = len(output)
        fixed = rom.fixed_data()
        output += fixed
        rom_offsets.append((rom.filename, offset, len(fixed)))

    total_roms_size = len(output)
    padding_size = flash_profile.capacity_bytes - total_roms_size
    output += bytes([PADDING_BYTE]) * padding_size

    report = MergeReport(
        messages=messages,
        rom_offsets=rom_offsets,
        total_roms_size=total_roms_size,
        padding_size=padding_size,
        output_size=len(output),
    )

    return bytes(output), report
