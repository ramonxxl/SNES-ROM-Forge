from core import checksum, detector


def _build_valid_rom(header_offset: int, reset_vector_offset: int, total_size: int, rom_size_byte: int = 7) -> bytes:
    data = bytearray(total_size)

    title = b"TEST GAME".ljust(21, b" ")
    data[header_offset:header_offset + 21] = title
    data[header_offset + 0x15] = 0x20  # map mode
    data[header_offset + 0x16] = 0x00  # rom type
    data[header_offset + 0x17] = rom_size_byte
    data[header_offset + 0x18] = 0x00  # sram size
    data[header_offset + 0x19] = 0x00  # country

    # reset vector pointing into ROM space (0x8000-0xFFFF)
    data[reset_vector_offset] = 0x00
    data[reset_vector_offset + 1] = 0x80

    return checksum.fix_checksum(bytes(data), header_offset)


def test_detects_lorom():
    total_size = 0x20000  # 128 KB, matches rom_size_byte=7
    data = _build_valid_rom(detector.LOROM_HEADER_OFFSET, 0x7FFC, total_size)

    mapping, candidate, scores = detector.detect(data)

    assert mapping == "lorom"
    assert candidate.header_offset == detector.LOROM_HEADER_OFFSET
    assert candidate.title == "TEST GAME"
    assert scores["lorom"] > scores["hirom"]


def test_detects_hirom():
    total_size = 0x20000  # 128 KB, matches rom_size_byte=7
    data = _build_valid_rom(detector.HIROM_HEADER_OFFSET, 0xFFFC, total_size)

    mapping, candidate, scores = detector.detect(data)

    assert mapping == "hirom"
    assert candidate.header_offset == detector.HIROM_HEADER_OFFSET
    assert scores["hirom"] > scores["lorom"]


def test_strips_smc_header():
    total_size = 0x20000
    rom_data = _build_valid_rom(detector.LOROM_HEADER_OFFSET, 0x7FFC, total_size)
    raw = (b"\x00" * 512) + rom_data

    data, has_header = detector.strip_smc_header(raw)

    assert has_header is True
    assert data == rom_data


def test_no_smc_header_when_size_does_not_match():
    total_size = 0x20000
    rom_data = _build_valid_rom(detector.LOROM_HEADER_OFFSET, 0x7FFC, total_size)

    data, has_header = detector.strip_smc_header(rom_data)

    assert has_header is False
    assert data == rom_data


def test_unknown_mapping_for_blank_data():
    data = bytes(0x20000)  # all zeros: no valid header in either candidate

    mapping, candidate, scores = detector.detect(data)

    assert mapping == "unknown"
    assert candidate is None
    assert scores["lorom"] < detector.MIN_DETECTION_SCORE
    assert scores["hirom"] < detector.MIN_DETECTION_SCORE
