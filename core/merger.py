"""Merge sequencial de ROMs SNES em uma única imagem para gravação em flash."""

from __future__ import annotations

from dataclasses import dataclass

from core.rom import SNESRom
from core.validator import ValidationMessage, validate
from devices.board_profiles import resolve_slot_sizes
from devices.flash_profiles import FlashProfile

PADDING_BYTE = 0xFF


@dataclass
class MergeReport:
    messages: list[ValidationMessage]
    rom_offsets: list[tuple[str, int, int]]  # (filename, offset, tamanho real da ROM)
    slot_sizes: list[int]  # slot de cada ROM, na mesma ordem de rom_offsets
    total_roms_size: int  # tamanho ocupado por ROMs + padding de slot (sem contar o padding final)
    padding_size: int  # padding final até a capacidade da flash
    output_size: int


def merge(roms: list[SNESRom], flash_profile: FlashProfile) -> tuple[bytes, MergeReport]:
    """Corrige o checksum de cada ROM (na ordem informada) e concatena.

    Cada ROM mantém seu próprio checksum interno corrigido — é o que o SNES lê
    quando aquele slot está ativo; não existe (nem faz sentido gerar) um checksum
    "global" sobre a imagem final. Cada ROM é preenchida com 0xFF até completar
    o próprio slot (capacidade da flash / número de posições de endereço, igual
    para todos os jogos) antes do próximo jogo começar, para bater com a placa
    PIC reset-bank-switch do usuário, que pula em incrementos fixos de endereço.
    O restante da capacidade da flash é preenchido com 0xFF no final (nunca com
    0x00).
    """
    slot_sizes = resolve_slot_sizes(roms, flash_profile.capacity_bytes)
    messages = validate(roms, flash_profile, slot_sizes=slot_sizes)

    output = bytearray()
    rom_offsets: list[tuple[str, int, int]] = []

    for index, rom in enumerate(roms):
        offset = len(output)
        fixed = rom.fixed_data()
        output += fixed
        rom_offsets.append((rom.filename, offset, len(fixed)))
        output += bytes([PADDING_BYTE]) * (slot_sizes[index] - len(fixed))

    total_roms_size = len(output)
    padding_size = flash_profile.capacity_bytes - total_roms_size
    output += bytes([PADDING_BYTE]) * padding_size

    report = MergeReport(
        messages=messages,
        rom_offsets=rom_offsets,
        slot_sizes=slot_sizes,
        total_roms_size=total_roms_size,
        padding_size=padding_size,
        output_size=len(output),
    )

    return bytes(output), report
