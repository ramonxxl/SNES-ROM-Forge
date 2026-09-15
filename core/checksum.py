"""Cálculo e correção do checksum interno de uma ROM SNES."""

_COMPLEMENT_REL_OFFSET = 0x1C
_CHECKSUM_REL_OFFSET = 0x1E


def compute_checksum(data: bytes, header_offset: int) -> int:
    """Soma todos os bytes de `data`, tratando os 4 bytes de checksum como zero.

    Equivale a zerar esses 4 bytes antes de somar, mas evita a cópia: os bytes
    são simplesmente excluídos da soma (contribuiriam com 0 de qualquer forma).
    """
    checksum_start = header_offset + _COMPLEMENT_REL_OFFSET
    checksum_end = header_offset + _CHECKSUM_REL_OFFSET + 2

    total = sum(data[:checksum_start]) + sum(data[checksum_end:])
    return total & 0xFFFF


def fix_checksum(data: bytes, header_offset: int) -> bytes:
    """Recalcula e regrava o checksum/complemento interno de uma ROM.

    Usa sempre `header_offset` (0x7FC0 para LoROM, 0xFFC0 para HiROM) do
    mapeamento já detectado da ROM — nunca um offset fixo.
    """
    checksum = compute_checksum(data, header_offset)
    complement = checksum ^ 0xFFFF

    fixed = bytearray(data)
    complement_offset = header_offset + _COMPLEMENT_REL_OFFSET
    checksum_offset = header_offset + _CHECKSUM_REL_OFFSET

    fixed[complement_offset] = complement & 0xFF
    fixed[complement_offset + 1] = (complement >> 8) & 0xFF
    fixed[checksum_offset] = checksum & 0xFF
    fixed[checksum_offset + 1] = (checksum >> 8) & 0xFF

    return bytes(fixed)


def read_checksum_pair(data: bytes, header_offset: int) -> tuple[int, int]:
    """Lê (checksum, complemento) já gravados na ROM, sem recalcular."""
    complement_offset = header_offset + _COMPLEMENT_REL_OFFSET
    checksum_offset = header_offset + _CHECKSUM_REL_OFFSET

    complement = data[complement_offset] | (data[complement_offset + 1] << 8)
    checksum = data[checksum_offset] | (data[checksum_offset + 1] << 8)
    return checksum, complement


def is_checksum_valid(data: bytes, header_offset: int) -> bool:
    """Confere se o checksum gravado bate com o valor calculado da ROM."""
    checksum, complement = read_checksum_pair(data, header_offset)
    if (checksum ^ complement) != 0xFFFF:
        return False

    return compute_checksum(data, header_offset) == checksum
