"""Perfis de placa: como o hardware físico troca entre os jogos gravados na flash.

A placa real do usuário usa um PIC (16F1829) que, a cada reset do próprio SNES,
avança para o próximo bloco de endereço na flash — o jogo então boota normalmente
através do seu próprio vetor de reset, sem precisar de nenhum stub/marcador extra
gravado na ROM. Isso só funciona se cada jogo ocupar um "slot" de tamanho FIXO
dentro da flash (mesmo que o jogo em si seja menor que o slot), porque o PIC pula
em incrementos fixos de endereço, não pelo tamanho real de cada ROM.

O modo "auto" cobre o caso em que os slots não são todos do mesmo tamanho: cada
ROM maior que a unidade base dobra de tamanho até caber (1 MB -> 2 MB -> 4 MB...),
mantendo a soma de todos os slots dentro da capacidade da flash.
"""

from __future__ import annotations

from dataclasses import dataclass

from core.rom import SNESRom

_MODES = ("none", "fixed", "auto")


@dataclass(frozen=True)
class BoardProfile:
    name: str
    mode: str = "none"  # "none" | "fixed" | "auto"
    slot_size_bytes: int | None = None  # usado quando mode == "fixed"
    base_unit_bytes: int = 1024 * 1024  # usado quando mode == "auto"
    is_custom: bool = False

    def __post_init__(self):
        if self.mode not in _MODES:
            raise ValueError(f"Modo de placa desconhecido: {self.mode!r}")


BOARD_PROFILES = [
    BoardProfile("Sem placa (merge compacto, offsets exatos das ROMs)", mode="none"),
    BoardProfile("PIC Reset Bank-Switch — slots de 512 KB", mode="fixed", slot_size_bytes=512 * 1024),
    BoardProfile("PIC Reset Bank-Switch — slots de 1 MB", mode="fixed", slot_size_bytes=1024 * 1024),
    BoardProfile("PIC Reset Bank-Switch — slots de 2 MB", mode="fixed", slot_size_bytes=2 * 1024 * 1024),
    BoardProfile("PIC Reset Bank-Switch — slots de 4 MB", mode="fixed", slot_size_bytes=4 * 1024 * 1024),
    BoardProfile(
        "PIC Reset Bank-Switch — slot automático (dobra conforme o tamanho de cada ROM)",
        mode="auto",
        base_unit_bytes=1024 * 1024,
    ),
    BoardProfile("PIC Reset Bank-Switch — slot personalizado...", mode="fixed", is_custom=True),
]

# Bate com o pedido do usuário: jogos de até 1 MB ficam num slot de 1 MB, jogos
# maiores (até 2 MB) dobram para um slot de 2 MB, sempre respeitando o total da flash.
DEFAULT_BOARD_PROFILE = BOARD_PROFILES[5]


def compute_auto_slot_size(rom_size_bytes: int, base_unit_bytes: int) -> int:
    """Dobra o tamanho do slot a partir de `base_unit_bytes` até caber a ROM."""
    slot_size = base_unit_bytes
    while slot_size < rom_size_bytes:
        slot_size *= 2
    return slot_size


def resolve_slot_sizes(roms: list[SNESRom], board_profile: BoardProfile | None) -> list[int] | None:
    """Calcula o tamanho de slot de cada ROM (na mesma ordem), ou None (merge compacto)."""
    if board_profile is None or board_profile.mode == "none":
        return None
    if board_profile.mode == "fixed":
        return [board_profile.slot_size_bytes for _ in roms]
    return [compute_auto_slot_size(rom.rom_size_bytes, board_profile.base_unit_bytes) for rom in roms]
