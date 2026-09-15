"""Regras de validação aplicadas antes de gerar a imagem final."""

from __future__ import annotations

from dataclasses import dataclass

from core.rom import SNESRom
from devices.flash_profiles import FlashProfile


class ValidationError(Exception):
    """Levantada quando alguma regra de bloqueio é violada."""


@dataclass
class ValidationMessage:
    level: str  # "error" | "warning"
    message: str


def validate(
    roms: list[SNESRom],
    flash_profile: FlashProfile,
    slot_sizes: list[int] | None = None,
) -> list[ValidationMessage]:
    """Valida a lista de ROMs contra as regras de bloqueio/aviso.

    `slot_sizes` vem do perfil de placa, um tamanho de slot por ROM (mesma ordem
    de `roms`): quando definido (placa com PIC bank-switch), cada ROM deve caber
    sozinha dentro do seu slot, e é a SOMA dos slots (não a soma exata dos
    tamanhos reais) que precisa caber na flash — os slots podem ter tamanhos
    diferentes entre si (modo "auto" do perfil de placa). Quando None, usa o
    merge compacto (soma exata dos tamanhos das ROMs).

    Levanta ValidationError na primeira regra de bloqueio violada.
    Retorna a lista de avisos (não bloqueantes) quando tudo está OK.
    """
    if not roms:
        raise ValidationError("Nenhuma ROM selecionada para o merge.")

    messages: list[ValidationMessage] = []

    mappings = {rom.mapping for rom in roms}
    if "unknown" in mappings:
        bad = next(rom.filename for rom in roms if rom.mapping == "unknown")
        raise ValidationError(
            f"'{bad}': mapeamento não pôde ser determinado (ROM corrompida ou sem vetor válido)."
        )

    if len(mappings) > 1:
        raise ValidationError(
            f"Mapeamento misto entre as ROMs selecionadas ({', '.join(sorted(mappings))}); "
            "todas devem ser LoROM ou todas HiROM."
        )

    if slot_sizes is not None:
        oversized = [
            rom.filename for rom, slot_size in zip(roms, slot_sizes) if rom.rom_size_bytes > slot_size
        ]
        if oversized:
            raise ValidationError(
                f"ROM(s) maior(es) que o slot calculado para elas na placa: {', '.join(oversized)}."
            )
        total_slots_size = sum(slot_sizes)
        if total_slots_size > flash_profile.capacity_bytes:
            raise ValidationError(
                f"Os slots das ROMs somam {total_slots_size} bytes, o que excede a capacidade da flash "
                f"'{flash_profile.name}' ({flash_profile.capacity_bytes} bytes)."
            )
    else:
        total_size = sum(rom.rom_size_bytes for rom in roms)
        if total_size > flash_profile.capacity_bytes:
            raise ValidationError(
                f"Tamanho total das ROMs ({total_size} bytes) excede a capacidade da flash "
                f"'{flash_profile.name}' ({flash_profile.capacity_bytes} bytes)."
            )

    for rom in roms:
        if rom.has_smc_header:
            messages.append(ValidationMessage("warning", f"'{rom.filename}': header SMC de 512 bytes removido."))
        if not rom.checksum_valid:
            messages.append(
                ValidationMessage("warning", f"'{rom.filename}': checksum original inválido, será corrigido.")
            )
        if not rom.title or not all(0x20 <= ord(c) < 0x7F for c in rom.title):
            messages.append(
                ValidationMessage("warning", f"'{rom.filename}': título interno contém caracteres inválidos.")
            )

    return messages
