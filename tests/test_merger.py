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
