"""Janela principal do SNES ROM Forge."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.merger import merge
from core.rom import SNESRom
from core.validator import ValidationError
from devices.flash_profiles import DEFAULT_FLASH_PROFILE, FLASH_PROFILES
from gui.rom_table_model import RomTableModel

ROM_FILE_FILTER = "ROMs SNES (*.sfc *.smc *.bin);;Todos os arquivos (*)"


def format_size(size_bytes: int) -> str:
    """Formata um tamanho em bytes também em KB, pra evitar confusão de unidade."""
    return f"{size_bytes} bytes ({size_bytes / 1024:.0f} KB)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SNES ROM Forge")
        self.resize(900, 600)

        self._model = RomTableModel()

        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        table_view = QTableView()
        table_view.setModel(self._model)
        table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_view.setSelectionBehavior(QTableView.SelectRows)
        table_view.setSelectionMode(QTableView.SingleSelection)
        self._table_view = table_view
        layout.addWidget(table_view)

        button_row = QHBoxLayout()

        add_button = QPushButton("Adicionar ROM(s)")
        add_button.clicked.connect(self._on_add_roms)
        button_row.addWidget(add_button)

        remove_button = QPushButton("Remover selecionada")
        remove_button.clicked.connect(self._on_remove_selected)
        button_row.addWidget(remove_button)

        up_button = QPushButton("Subir")
        up_button.clicked.connect(lambda: self._on_move_selected(-1))
        button_row.addWidget(up_button)

        down_button = QPushButton("Descer")
        down_button.clicked.connect(lambda: self._on_move_selected(1))
        button_row.addWidget(down_button)

        button_row.addStretch()

        button_row.addWidget(QLabel("Flash:"))
        self._flash_combo = QComboBox()
        for profile in FLASH_PROFILES:
            self._flash_combo.addItem(profile.name, profile)
        self._flash_combo.setCurrentIndex(FLASH_PROFILES.index(DEFAULT_FLASH_PROFILE))
        button_row.addWidget(self._flash_combo)

        generate_button = QPushButton("Gerar BIN")
        generate_button.clicked.connect(self._on_generate_bin)
        button_row.addWidget(generate_button)

        layout.addLayout(button_row)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        layout.addWidget(self._log)

    def _log_line(self, text: str) -> None:
        self._log.appendPlainText(text)

    def _selected_row(self) -> int | None:
        indexes = self._table_view.selectionModel().selectedRows()
        if not indexes:
            return None
        return indexes[0].row()

    def _on_add_roms(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Adicionar ROM(s)", "", ROM_FILE_FILTER)
        for path in paths:
            try:
                rom = SNESRom.load(path)
            except OSError as exc:
                self._log_line(f"Erro ao ler '{Path(path).name}': {exc}")
                continue
            self._model.add_rom(rom)
            self._log_line(f"Importada: '{rom.filename}' ({rom.mapping}, {format_size(rom.rom_size_bytes)}).")

    def _on_remove_selected(self) -> None:
        row = self._selected_row()
        if row is None:
            return
        rom = self._model.roms()[row]
        self._model.remove_row(row)
        self._log_line(f"Removida: '{rom.filename}'.")

    def _on_move_selected(self, direction: int) -> None:
        row = self._selected_row()
        if row is None:
            return
        new_row = self._model.move_row(row, direction)
        self._table_view.selectRow(new_row)

    def _on_generate_bin(self) -> None:
        roms = self._model.roms()
        flash_profile = self._flash_combo.currentData()

        try:
            data, report = merge(roms, flash_profile)
        except ValidationError as exc:
            self._log_line(f"ERRO: {exc}")
            QMessageBox.critical(self, "Não foi possível gerar o BIN", str(exc))
            return

        for message in report.messages:
            prefix = "AVISO" if message.level == "warning" else "ERRO"
            self._log_line(f"{prefix}: {message.message}")

        save_path, _ = QFileDialog.getSaveFileName(self, "Salvar imagem BIN", "", "Imagem BIN (*.bin)")
        if not save_path:
            return

        Path(save_path).write_bytes(data)

        self._log_line(f"Imagem gerada: '{save_path}' ({format_size(report.output_size)}).")
        self._log_line("Resumo:")
        for (filename, offset, size), slot_size in zip(report.rom_offsets, report.slot_sizes):
            slot_padding = slot_size - size
            self._log_line(
                f"  - {filename}: offset 0x{offset:06X}, {format_size(size)} "
                f"[slot de {format_size(slot_size)}, + {format_size(slot_padding)} de padding]"
            )
        self._log_line(f"  - Padding final (0xFF): {format_size(report.padding_size)}")
