"""Cálculo do tamanho de slot de cada ROM para a placa PIC Reset Bank-Switch do usuário.

Hardware confirmado (fotos da placa + datasheet do usuário): um PIC12F629 tem
duas saídas ligadas direto nas duas linhas de endereço mais altas da flash
29L3211 de 4 MB (A20 e A21). A cada reset do SNES, o PIC avança para a próxima
combinação dessas 2 linhas e o jogo selecionado boota normalmente pelo próprio
vetor de reset — sem stub nem marcador extra gravado na ROM (o PIC em si é
gravado à parte, fora deste programa).

Como essas linhas de endereço são compartilhadas por TODOS os jogos da mesma
gravação, todo jogo precisa ocupar um slot do MESMO tamanho: capacidade da
flash dividida pelo número de posições de endereço usadas. Com 2 linhas de
endereço só existem 4 posições possíveis (2 bits = 2^2), então o número de
slots é sempre a próxima potência de 2 a partir da quantidade de ROMs
carregadas (1, 2 ou 4) — 3 jogos, por exemplo, ainda usam 4 posições de 1 MB,
sobrando uma vazia (preenchida com 0xFF).
"""

from __future__ import annotations

from core.rom import SNESRom


def _next_power_of_two(n: int) -> int:
    if n <= 1:
        return 1
    return 1 << (n - 1).bit_length()


def resolve_slot_sizes(roms: list[SNESRom], flash_capacity_bytes: int) -> list[int]:
    """Calcula o tamanho de slot uniforme (capacidade da flash / nº de posições)."""
    if not roms:
        return []
    num_slots = _next_power_of_two(len(roms))
    slot_size = flash_capacity_bytes // num_slots
    return [slot_size] * len(roms)
