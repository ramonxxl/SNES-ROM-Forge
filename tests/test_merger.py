import pytest

from core import checksum
from core.merger import merge
from core.rom import SNESRom
from core.validator import ValidationError
from devices.board_profiles import BoardProfile
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


def test_merge_preserves_order_and_pads_with_ff():
    roms = [_make_rom(f"game{i}.sfc", "lorom", 0x8000) for i in range(1, 5)]
    flash = FlashProfile("test-flash", 0x24000)  # bigger than the 4x32KB total

    data, report = merge(roms, flash)

    assert len(data) == flash.capacity_bytes
    assert report.total_roms_size == 4 * 0x8000
    assert report.padding_size == flash.capacity_bytes - 4 * 0x8000
    assert data[report.total_roms_size:] == bytes([0xFF]) * report.padding_size

    offsets = [offset for _, offset, _ in report.rom_offsets]
    assert offsets == [0, 0x8000, 0x10000, 0x18000]

    for rom, (_, offset, size) in zip(roms, report.rom_offsets):
        assert checksum.is_checksum_valid(data[offset:offset + size], rom.header_offset)


def test_merge_blocks_mixed_mapping():
    lorom = _make_rom("lo.sfc", "lorom", 0x8000)
    hirom = _make_rom("hi.sfc", "hirom", 0x10000)
    flash = FlashProfile("test-flash", 0x30000)

    with pytest.raises(ValidationError):
        merge([lorom, hirom], flash)


def test_merge_blocks_when_exceeds_capacity():
    roms = [_make_rom(f"game{i}.sfc", "lorom", 0x8000) for i in range(1, 5)]
    flash = FlashProfile("tiny-flash", 0x8000)  # only fits one rom

    with pytest.raises(ValidationError):
        merge(roms, flash)


def test_merge_blocks_unknown_mapping():
    roms = [_make_rom("lo.sfc", "lorom", 0x8000)]
    roms[0].mapping = "unknown"
    flash = FlashProfile("test-flash", 0x8000)

    with pytest.raises(ValidationError):
        merge(roms, flash)


def test_merge_with_fixed_board_profile_pads_each_rom_to_slot_size():
    # ROMs de tamanhos diferentes, cada uma deve ocupar um slot fixo de 0x10000,
    # como faz a placa real (PIC pula em incrementos fixos de endereço).
    roms = [
        _make_rom("small.sfc", "lorom", 0x8000),   # menor que o slot
        _make_rom("exact.sfc", "lorom", 0x10000),  # exatamente o slot
    ]
    flash = FlashProfile("test-flash", 0x30000)
    board = BoardProfile("PIC teste", mode="fixed", slot_size_bytes=0x10000)

    data, report = merge(roms, flash, board)

    assert report.slot_sizes == [0x10000, 0x10000]
    offsets = [offset for _, offset, _ in report.rom_offsets]
    assert offsets == [0, 0x10000]  # cada rom começa no início do próximo slot

    # padding dentro do slot da rom pequena preenchido com 0xFF
    assert data[0x8000:0x10000] == bytes([0xFF]) * 0x8000

    assert report.total_roms_size == 2 * 0x10000
    assert report.padding_size == flash.capacity_bytes - 2 * 0x10000
    assert len(data) == flash.capacity_bytes


def test_merge_blocks_rom_larger_than_fixed_slot():
    roms = [_make_rom("big.sfc", "lorom", 0x10000)]
    flash = FlashProfile("test-flash", 0x30000)
    board = BoardProfile("PIC teste", mode="fixed", slot_size_bytes=0x8000)  # slot menor que a rom

    with pytest.raises(ValidationError):
        merge(roms, flash, board)


def test_merge_blocks_too_many_fixed_slots_for_flash_capacity():
    roms = [_make_rom(f"game{i}.sfc", "lorom", 0x8000) for i in range(1, 4)]
    flash = FlashProfile("test-flash", 0x10000)  # só cabem 2 slots de 0x8000
    board = BoardProfile("PIC teste", mode="fixed", slot_size_bytes=0x8000)

    with pytest.raises(ValidationError):
        merge(roms, flash, board)


def test_merge_auto_slot_doubles_for_larger_roms():
    roms = [
        _make_rom("small.sfc", "lorom", 0x100000),  # 1 MB -> slot de 1 MB
        _make_rom("big1.sfc", "lorom", 0x110000),   # > 1 MB -> slot de 2 MB
        _make_rom("big2.sfc", "lorom", 0x1FFFFF),   # quase 2 MB -> slot de 2 MB
    ]
    flash = FlashProfile("test-flash", 8 * 1024 * 1024)
    board = BoardProfile("auto teste", mode="auto", base_unit_bytes=0x100000)

    data, report = merge(roms, flash, board)

    assert report.slot_sizes == [0x100000, 0x200000, 0x200000]
    offsets = [offset for _, offset, _ in report.rom_offsets]
    assert offsets == [0, 0x100000, 0x300000]


def test_merge_auto_slot_matches_user_scenario_two_2mb_games_fill_4mb_flash():
    # Cenário pedido: jogos > 1024 KB viram slot de 2048 KB; 2 jogos assim
    # preenchem exatamente os 4096 KB da flash.
    roms = [
        _make_rom("gameA.sfc", "lorom", 0x180000),  # 1.5 MB -> slot de 2 MB
        _make_rom("gameB.sfc", "lorom", 0x190000),  # ~1.56 MB -> slot de 2 MB
    ]
    flash = FlashProfile("29L3211", 4 * 1024 * 1024)
    board = BoardProfile("auto", mode="auto")  # base_unit_bytes padrão = 1 MB

    data, report = merge(roms, flash, board)

    assert report.slot_sizes == [2 * 1024 * 1024, 2 * 1024 * 1024]
    assert sum(report.slot_sizes) == flash.capacity_bytes
    assert report.padding_size == 0
    assert len(data) == flash.capacity_bytes


def test_merge_auto_slot_blocks_when_total_exceeds_flash():
    # 3 jogos de ~1.5 MB cada -> 3 slots de 2 MB = 6 MB, não cabe numa flash de 4 MB.
    roms = [_make_rom(f"g{i}.sfc", "lorom", 0x180000) for i in range(3)]
    flash = FlashProfile("29L3211", 4 * 1024 * 1024)
    board = BoardProfile("auto", mode="auto")

    with pytest.raises(ValidationError):
        merge(roms, flash, board)
