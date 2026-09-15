"""Cálculo do tamanho de slot de cada ROM para a placa PIC Reset Bank-Switch do usuário.

Hardware confirmado (fotos da placa + datasheet do usuário): um PIC12F629 tem
duas saídas ligadas direto nas duas linhas de endereço mais altas da flash
29L3211 de 4 MB (A20 e A21). A cada reset do SNES, o PIC avança para a próxima
combinação dessas 2 linhas e o jogo selecionado boota normalmente pelo próprio
vetor de reset — sem stub nem marcador extra gravado na ROM (o PIC em si é
gravado à parte, fora deste programa).

Como essas 2 linhas só têm 4 combinações possíveis (2 bits), NENHUMA das 4
posições pode ficar sem um jogo atribuído — um endereço "flutuando" (flash em
branco) faria o SNES travar se o PIC algum dia parasse ali. Por isso, quando o
número de ROMs não preenche as 4 posições sozinho (ex.: 3 jogos), uma das ROMs
precisa se repetir inteira (cabeçalho e tudo) para ocupar a(s) posição(ões)
que sobrariam — exatamente como um jogo que já é naturalmente maior ocuparia
mais de uma posição sozinho.
"""

from __future__ import annotations

from core.rom import SNESRom

DEFAULT_BASE_UNIT_BYTES = 1024 * 1024  # 1 MB — o que cada combinação de endereço cobre


def compute_natural_slot_size(rom_size_bytes: int, base_unit_bytes: int = DEFAULT_BASE_UNIT_BYTES) -> int:
    """Menor múltiplo (potência de 2) da unidade base que cabe a ROM sozinha."""
    slot_size = base_unit_bytes
    while slot_size < rom_size_bytes:
        slot_size *= 2
    return slot_size


def resolve_slot_sizes(
    roms: list[SNESRom],
    flash_capacity_bytes: int,
    base_unit_bytes: int = DEFAULT_BASE_UNIT_BYTES,
) -> list[int]:
    """Calcula o slot de cada ROM, expandindo (dobrando) o(s) menor(es) até
    ocupar EXATAMENTE toda a capacidade da flash — nunca deixando uma posição
    de endereço sem jogo nenhum atribuído.

    Expande sempre o slot atualmente menor primeiro (e cada expansão dobra um
    slot já existente, nunca cria um tamanho fora das potências de 2), o que
    naturalmente evita ter que expandir um jogo que já ocupa mais de uma
    posição por tamanho próprio.
    """
    if not roms:
        return []

    sizes = [compute_natural_slot_size(rom.rom_size_bytes, base_unit_bytes) for rom in roms]
    total = sum(sizes)

    while total < flash_capacity_bytes:
        min_index = min(range(len(sizes)), key=lambda i: sizes[i])
        added = sizes[min_index]
        if total + added > flash_capacity_bytes:
            break  # não dá pra fechar exato sem ultrapassar; validate() reporta o excesso
        sizes[min_index] *= 2
        total += added

    return sizes
