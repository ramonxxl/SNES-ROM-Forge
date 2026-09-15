import pytest

from core import checksum
from core.merger import merge
from core.rom import SNESRom
from core.validator import ValidationError
from devices.flash_profiles import FlashProfile


def _make_rom(name: str, mapping: str, size: int) -> SNESRom:
    header_offset = 0x7FC0 if mapping == "lorom" else 0xFFC0
    data = bytes([0xAB]) * size
    fixed = checksum.fix_checksum(data, header_offset)
    checksum_value, complement = checksum.read_checksum_pair(fixed, header_offset)

    return SNESRom(
        filename=name,
        raw_data=fixed,
        data=fixed,
        has_smc_header=False,
        mapping=mapping,
        header_offset=header_offset,
        title="GAME",
        checksum_value=checksum_value,
        complement=complement,
        checksum_valid=True,
        rom_size_bytes=len(fixed),
    )


def test_merge_with_4_roms_uses_1mb_slots_in_4mb_flash():
    # Placa real do usuário: PIC liga 2 linhas de endereço (A20/A21) na flash de
    # 4 MB -> 4 posições de 1 MB cada quando as 4 sao usadas.
    roms = [
        _make_rom("small.sfc", "lorom", 0x8000),    # menor que 1 MB -> ainda ocupa o slot de 1 MB
        _make_rom("exact.sfc", "lorom", 0x100000),  # exatamente 1 MB
        _make_rom("g3.sfc", "lorom", 0x90000),
        _make_rom("g4.sfc", "lorom", 0x100000),
    ]
    flash = FlashProfile("29L3211", 4 * 1024 * 1024)

    data, report = merge(roms, flash)

    assert report.slot_sizes == [0x100000] * 4
    offsets = [offset for _, offset, _ in report.rom_offsets]
    assert offsets == [0, 0x100000, 0x200000, 0x300000]
    assert report.padding_size == 0
    assert len(data) == flash.capacity_bytes

    # padding dentro do slot da rom pequena preenchido com 0xFF
    assert data[0x8000:0x100000] == bytes([0xFF]) * (0x100000 - 0x8000)

    for rom, (_, offset, size) in zip(roms, report.rom_offsets):
        assert checksum.is_checksum_valid(data[offset:offset + size], rom.header_offset)


def test_merge_matches_user_scenario_two_2mb_games_fill_4mb_flash():
    # Cenário real do usuário: 2 jogos carregados -> só 1 linha de endereço em
    # uso -> 2 posições de 2048 KB cada, preenchendo os 4096 KB (4 MB) da flash.
    roms = [
        _make_rom("gameA.sfc", "lorom", 0x180000),  # 1.5 MB
        _make_rom("gameB.sfc", "lorom", 0x190000),  # ~1.56 MB
    ]
    flash = FlashProfile("29L3211", 4 * 1024 * 1024)

    data, report = merge(roms, flash)

    assert report.slot_sizes == [2 * 1024 * 1024, 2 * 1024 * 1024]
    assert sum(report.slot_sizes) == flash.capacity_bytes
    assert report.padding_size == 0
    assert len(data) == flash.capacity_bytes


def test_merge_with_3_roms_expands_one_to_avoid_a_floating_address():
    # 3 jogos: com só 2 linhas de endereço (4 posições possíveis), nenhuma
    # posição pode ficar sem jogo (endereço "flutuando" = flash em branco se o
    # PIC parar ali). A primeira ROM se repete inteira (1 MB -> 2 MB) para
    # preencher a posição que sobraria, em vez de deixá-la em branco.
    roms = [_make_rom(f"g{i}.sfc", "lorom", 0x100000) for i in range(3)]
    flash = FlashProfile("29L3211", 4 * 1024 * 1024)

    data, report = merge(roms, flash)

    assert report.slot_sizes == [0x200000, 0x100000, 0x100000]
    offsets = [offset for _, offset, _ in report.rom_offsets]
    assert offsets == [0, 0x200000, 0x300000]
    assert report.padding_size == 0
    assert len(data) == flash.capacity_bytes

    # a rom0 (expandida) aparece inteira, com header válido, nas duas metades do seu slot de 2 MB
    rom0_size = report.rom_offsets[0][2]
    assert data[0:rom0_size] == data[0x100000:0x100000 + rom0_size]
    assert checksum.is_checksum_valid(data[0x100000:0x100000 + rom0_size], roms[0].header_offset)


def test_merge_blocks_rom_bigger_than_computed_slot():
    # 3 jogos de ~1.5 MB cada: com 3 ROMs o slot calculado é de 1 MB (4
    # posições), mas nenhum deles cabe nesse tamanho.
    roms = [_make_rom(f"g{i}.sfc", "lorom", 0x180000) for i in range(3)]
    flash = FlashProfile("29L3211", 4 * 1024 * 1024)

    with pytest.raises(ValidationError):
        merge(roms, flash)


def test_merge_blocks_mixed_mapping():
    lorom = _make_rom("lo.sfc", "lorom", 0x8000)
    hirom = _make_rom("hi.sfc", "hirom", 0x10000)
    flash = FlashProfile("test-flash", 4 * 1024 * 1024)

    with pytest.raises(ValidationError):
        merge([lorom, hirom], flash)


def test_merge_blocks_unknown_mapping():
    roms = [_make_rom("lo.sfc", "lorom", 0x8000)]
    roms[0].mapping = "unknown"
    flash = FlashProfile("test-flash", 4 * 1024 * 1024)

    with pytest.raises(ValidationError):
        merge(roms, flash)
