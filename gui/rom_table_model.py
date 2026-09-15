"""Modelo de tabela Qt para exibir as ROMs importadas."""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from core.rom import SNESRom

_COLUMNS = ["Arquivo", "Tamanho", "Header SMC", "Mapping", "Checksum", "Título"]


class RomTableModel(QAbstractTableModel):
    def __init__(self, roms: list[SNESRom] | None = None, parent=None):
        super().__init__(parent)
        self._roms: list[SNESRom] = roms or []

    def roms(self) -> list[SNESRom]:
        return self._roms

    def set_roms(self, roms: list[SNESRom]) -> None:
        self.beginResetModel()
        self._roms = roms
        self.endResetModel()

    def add_rom(self, rom: SNESRom) -> None:
        row = len(self._roms)
        self.beginInsertRows(QModelIndex(), row, row)
        self._roms.append(rom)
        self.endInsertRows()

    def remove_row(self, row: int) -> None:
        if 0 <= row < len(self._roms):
            self.beginRemoveRows(QModelIndex(), row, row)
            del self._roms[row]
            self.endRemoveRows()

    def move_row(self, row: int, direction: int) -> int:
        """Move a linha `row` por `direction` (-1 sobe, +1 desce). Retorna a nova posição."""
        new_row = row + direction
        if not (0 <= new_row < len(self._roms)):
            return row
        self.beginMoveRows(
            QModelIndex(), row, row, QModelIndex(), new_row if direction < 0 else new_row + 1
        )
        self._roms[row], self._roms[new_row] = self._roms[new_row], self._roms[row]
        self.endMoveRows()
        return new_row

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._roms)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(_COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return _COLUMNS[section]
        return None

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role != Qt.DisplayRole or not index.isValid():
            return None

        rom = self._roms[index.row()]
        column = index.column()

        if column == 0:
            return rom.filename
        if column == 1:
            return f"{rom.rom_size_bytes:,} bytes".replace(",", ".")
        if column == 2:
            return "Sim" if rom.has_smc_header else "Não"
        if column == 3:
            return {"lorom": "LoROM", "hirom": "HiROM", "unknown": "Desconhecido"}[rom.mapping]
        if column == 4:
            return "Válido" if rom.checksum_valid else "Inválido (será corrigido)"
        if column == 5:
            return rom.title

        return None
