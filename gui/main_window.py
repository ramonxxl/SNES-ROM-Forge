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
    QSpinBox,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from core.merger import merge
from core.rom import SNESRom
from core.validator import ValidationError
from devices.board_profiles import BOARD_PROFILES, DEFAULT_BOARD_PROFILE, BoardProfile
from devices.flash_profiles import DEFAULT_FLASH_PROFILE, FLASH_PROFILES
from gui.rom_table_model import RomTableModel

ROM_FILE_FILTER = "ROMs SNES (*.sfc *.smc *.bin);;Todos os arquivos (*)"


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

        board_row = QHBoxLayout()

        board_row.addWidget(QLabel("Placa:"))
        self._board_combo = QComboBox()
        for profile in BOARD_PROFILES:
            self._board_combo.addItem(profile.name, profile)
        self._board_combo.setCurrentIndex(BOARD_PROFILES.index(DEFAULT_BOARD_PROFILE))
        self._board_combo.currentIndexChanged.connect(self._on_board_combo_changed)
        board_row.addWidget(self._board_combo)

        board_row.addWidget(QLabel("Slot personalizado (KB):"))
        self._custom_slot_spin = QSpinBox()
        self._custom_slot_spin.setRange(32, 64 * 1024)  # 32 KB .. 64 MB
        self._custom_slot_spin.setSingleStep(32)
        self._custom_slot_spin.setValue(1024)
        self._custom_slot_spin.setEnabled(False)
        board_row.addWidget(self._custom_slot_spin)

        board_row.addStretch()
        layout.addLayout(board_row)

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
            self._log_line(f"Importada: '{rom.filename}' ({rom.mapping}, {rom.rom_size_bytes} bytes).")

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

    def _on_board_combo_changed(self, _index: int) -> None:
        profile: BoardProfile = self._board_combo.currentData()
        self._custom_slot_spin.setEnabled(profile.is_custom)

    def _effective_board_profile(self) -> BoardProfile:
        profile: BoardProfile = self._board_combo.currentData()
        if profile.is_custom:
            slot_size_bytes = self._custom_slot_spin.value() * 1024
            return BoardProfile(profile.name, mode="fixed", slot_size_bytes=slot_size_bytes, is_custom=True)
        return profile

    def _on_generate_bin(self) -> None:
        roms = self._model.roms()
        flash_profile = self._flash_combo.currentData()
        board_profile = self._effective_board_profile()

        try:
            data, report = merge(roms, flash_profile, board_profile)
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

        self._log_line(f"Imagem gerada: '{save_path}' ({report.output_size} bytes).")
        if report.slot_sizes is not None:
            self._log_line(f"Placa: {board_profile.name}.")
        self._log_line("Resumo:")
        for (filename, offset, size), slot_size in zip(
            report.rom_offsets, report.slot_sizes or [None] * len(report.rom_offsets)
        ):
            slot_note = ""
            if slot_size is not None:
                slot_padding = slot_size - size
                slot_note = f" [slot de {slot_size} bytes, + {slot_padding} bytes de padding]"
            self._log_line(f"  - {filename}: offset 0x{offset:06X}, {size} bytes{slot_note}")
        self._log_line(f"  - Padding final (0xFF): {report.padding_size} bytes")
