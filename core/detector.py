"""Detecção de header SMC (copier) e de mapeamento LoROM/HiROM de ROMs SNES."""

from dataclasses import dataclass

SMC_HEADER_SIZE = 512

LOROM_HEADER_OFFSET = 0x7FC0
HIROM_HEADER_OFFSET = 0xFFC0

_TITLE_OFFSET = 0x00
_TITLE_SIZE = 21
_MAP_MODE_OFFSET = 0x15
_ROM_TYPE_OFFSET = 0x16
_ROM_SIZE_OFFSET = 0x17
_SRAM_SIZE_OFFSET = 0x18
_COUNTRY_OFFSET = 0x19
_COMPLEMENT_OFFSET = 0x1C
_CHECKSUM_OFFSET = 0x1E
_HEADER_BLOCK_SIZE = 0x40

_RESET_VECTOR_OFFSET = {
    "lorom": 0x7FFC,
    "hirom": 0xFFFC,
}

MIN_DETECTION_SCORE = 2


@dataclass
class HeaderCandidate:
    mapping: str
    header_offset: int
    title: str
    map_mode: int
    rom_type: int
    rom_size_byte: int
    sram_size_byte: int
    country: int
    complement: int
    checksum: int
    score: int


def strip_smc_header(raw: bytes) -> tuple[bytes, bool]:
    """Remove o header SMC de 512 bytes, se presente."""
    if len(raw) % 1024 == SMC_HEADER_SIZE:
        return raw[SMC_HEADER_SIZE:], True
    return raw, False


def _read_u16le(data: bytes, offset: int) -> int:
    return data[offset] | (data[offset + 1] << 8)


def _score_candidate(data: bytes, mapping: str) -> HeaderCandidate | None:
    header_offset = LOROM_HEADER_OFFSET if mapping == "lorom" else HIROM_HEADER_OFFSET
    if len(data) < header_offset + _HEADER_BLOCK_SIZE:
        return None

    title_bytes = data[header_offset + _TITLE_OFFSET: header_offset + _TITLE_OFFSET + _TITLE_SIZE]
    title = title_bytes.decode("ascii", errors="replace").strip("\x00 ")
    map_mode = data[header_offset + _MAP_MODE_OFFSET]
    rom_type = data[header_offset + _ROM_TYPE_OFFSET]
    rom_size_byte = data[header_offset + _ROM_SIZE_OFFSET]
    sram_size_byte = data[header_offset + _SRAM_SIZE_OFFSET]
    country = data[header_offset + _COUNTRY_OFFSET]
    complement = _read_u16le(data, header_offset + _COMPLEMENT_OFFSET)
    checksum = _read_u16le(data, header_offset + _CHECKSUM_OFFSET)

    score = 0

    if (checksum ^ complement) == 0xFFFF:
        score += 2

    if 0 < rom_size_byte < 32:
        expected_size = (1 << rom_size_byte) * 1024
        if expected_size * 0.5 <= len(data) <= expected_size * 2:
            score += 1

    if title_bytes:
        printable = sum(1 for b in title_bytes if 0x20 <= b < 0x7F)
        if printable / len(title_bytes) > 0.8:
            score += 1

    reset_vector_offset = _RESET_VECTOR_OFFSET[mapping]
    if reset_vector_offset + 1 < len(data):
        reset_vector = _read_u16le(data, reset_vector_offset)
        if 0x8000 <= reset_vector <= 0xFFFF:
            score += 2

    return HeaderCandidate(
        mapping=mapping,
        header_offset=header_offset,
        title=title,
        map_mode=map_mode,
        rom_type=rom_type,
        rom_size_byte=rom_size_byte,
        sram_size_byte=sram_size_byte,
        country=country,
        complement=complement,
        checksum=checksum,
        score=score,
    )


def detect(data: bytes) -> tuple[str, HeaderCandidate | None, dict[str, int]]:
    """Detecta o mapeamento (LoROM/HiROM) de uma ROM já sem header SMC.

    Retorna (mapping, candidato_escolhido_ou_None, scores_brutos).
    mapping é "lorom", "hirom" ou "unknown".
    """
    lorom_candidate = _score_candidate(data, "lorom")
    hirom_candidate = _score_candidate(data, "hirom")

    scores = {
        "lorom": lorom_candidate.score if lorom_candidate else -1,
        "hirom": hirom_candidate.score if hirom_candidate else -1,
    }

    best_mapping = max(scores, key=scores.get)
    best_score = scores[best_mapping]

    if best_score < MIN_DETECTION_SCORE:
        return "unknown", None, scores

    best_candidate = lorom_candidate if best_mapping == "lorom" else hirom_candidate
    return best_mapping, best_candidate, scores
