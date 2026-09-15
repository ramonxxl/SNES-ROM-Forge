"""Merge sequencial de ROMs SNES em uma única imagem para gravação em flash."""

from __future__ import annotations

from dataclasses import dataclass

from core.rom import SNESRom
from core.validator import ValidationMessage, validate
from devices.board_profiles import compute_natural_slot_size, resolve_slot_sizes
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
    "global" sobre a imagem final. O slot de cada ROM é sempre um múltiplo de
    1 MB (capacidade da flash / número de posições de endereço do PIC, igual
    para todos os jogos). Quando o slot de uma ROM é maior que o necessário
    para caber sua própria ROM (porque sobrou posição de endereço sem jogo
    nenhum atribuído), a ROM inteira se repete para preencher esse slot —
    nunca deixando uma posição de endereço em branco ("flutuando"), já que o
    PIC pode selecionar qualquer uma das posições a qualquer momento. O
    restante da capacidade da flash (além de todos os slots) é preenchido com
    0xFF no final (nunca com 0x00).
    """
    slot_sizes = resolve_slot_sizes(roms, flash_profile.capacity_bytes)
    messages = validate(roms, flash_profile, slot_sizes=slot_sizes)

    output = bytearray()
    rom_offsets: list[tuple[str, int, int]] = []

    for index, rom in enumerate(roms):
        offset = len(output)
        fixed = rom.fixed_data()
        rom_offsets.append((rom.filename, offset, len(fixed)))

        natural_size = compute_natural_slot_size(rom.rom_size_bytes)
        natural_block = fixed + bytes([PADDING_BYTE]) * (natural_size - len(fixed))

        slot_size = slot_sizes[index]
        repeat_count = slot_size // natural_size
        output += natural_block * repeat_count

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
