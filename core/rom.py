"""Representa uma ROM SNES carregada e já analisada."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from core import checksum, detector


@dataclass
class SNESRom:
    filename: str
    raw_data: bytes
    data: bytes
    has_smc_header: bool
    mapping: str
    header_offset: int | None
    title: str
    checksum_value: int
    complement: int
    checksum_valid: bool
    rom_size_bytes: int
    detection_scores: dict[str, int] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> "SNESRom":
        path = Path(path)
        raw_data = path.read_bytes()
        data, has_smc_header = detector.strip_smc_header(raw_data)

        mapping, candidate, scores = detector.detect(data)

        if candidate is None:
            return cls(
                filename=path.name,
                raw_data=raw_data,
                data=data,
                has_smc_header=has_smc_header,
                mapping="unknown",
                header_offset=None,
                title="",
                checksum_value=0,
                complement=0,
                checksum_valid=False,
                rom_size_bytes=len(data),
                detection_scores=scores,
            )

        checksum_value, complement = checksum.read_checksum_pair(data, candidate.header_offset)
        valid = checksum.is_checksum_valid(data, candidate.header_offset)

        return cls(
            filename=path.name,
            raw_data=raw_data,
            data=data,
            has_smc_header=has_smc_header,
            mapping=mapping,
            header_offset=candidate.header_offset,
            title=candidate.title,
            checksum_value=checksum_value,
            complement=complement,
            checksum_valid=valid,
            rom_size_bytes=len(data),
            detection_scores=scores,
        )

    def fixed_data(self) -> bytes:
        """Retorna os dados da ROM com o checksum interno corrigido."""
        if self.header_offset is None:
            raise ValueError(f"'{self.filename}': mapeamento desconhecido, não é possível corrigir o checksum.")
        return checksum.fix_checksum(self.data, self.header_offset)
