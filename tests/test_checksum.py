from core import checksum


def test_compute_checksum_excludes_checksum_bytes():
    data = bytes(range(32))  # 32 bytes: 0..31
    header_offset = 0

    result = checksum.compute_checksum(data, header_offset)

    # bytes 0x1C..0x1F (28..31) are excluded from the sum regardless of content
    expected = sum(range(28)) & 0xFFFF
    assert result == expected


def test_fix_checksum_produces_consistent_pair():
    header_offset = 0x10
    data = bytearray(bytes(range(256)) * 4)  # 1024 bytes, deterministic pattern
    # corrupt the checksum area first
    data[header_offset + 0x1C:header_offset + 0x20] = b"\xAA\xAA\xBB\xBB"

    fixed = checksum.fix_checksum(bytes(data), header_offset)

    assert checksum.is_checksum_valid(fixed, header_offset)
    checksum_value, complement = checksum.read_checksum_pair(fixed, header_offset)
    assert (checksum_value ^ complement) == 0xFFFF


def test_fix_checksum_is_idempotent():
    header_offset = 0x10
    data = bytes(range(256)) * 4

    once = checksum.fix_checksum(data, header_offset)
    twice = checksum.fix_checksum(once, header_offset)

    assert once == twice


def test_is_checksum_valid_detects_bad_checksum():
    header_offset = 0x10
    data = bytearray(bytes(range(256)) * 4)
    data[header_offset + 0x1C:header_offset + 0x20] = b"\x00\x00\x00\x00"

    assert not checksum.is_checksum_valid(bytes(data), header_offset)
