"""Janela principal do SNES ROM Forge."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.merger import merge
from core.rom import SNESRom
from core.validator import ValidationError
from devices.flash_profiles import DEFAULT_FLASH_PROFILE, FLASH_PROFILES
from gui import theme
from gui.boxart import BoxArtFetcher, build_candidate_filenames
from gui.drop_zone import DropZoneWidget
from gui.rom_card import RomCardWidget

CARD_SPACING = 14


def format_size(size_bytes: int) -> str:
    """Formata um tamanho em bytes também em KB, pra evitar confusão de unidade."""
    return f"{size_bytes} bytes ({size_bytes / 1024:.0f} KB)"


def _swap_button() -> QPushButton:
    button = QPushButton("⇄")
    button.setFixedSize(26, 26)
    button.setCursor(Qt.PointingHandCursor)
    button.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {theme.TEXT_MUTED};
            border: none;
            font-size: 15px;
        }}
        QPushButton:hover {{
            color: {theme.TEXT};
        }}
    """)
    return button


class SettingsDialog(QDialog):
    def __init__(self, current_flash_profile, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)

        label = QLabel("Capacidade da flash")
        label.setObjectName("sectionLabel")
        layout.addWidget(label)

        self.flash_combo = QComboBox()
        for profile in FLASH_PROFILES:
            self.flash_combo.addItem(profile.name, profile)
        self.flash_combo.setCurrentIndex(FLASH_PROFILES.index(current_flash_profile))
        layout.addWidget(self.flash_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected_flash_profile(self):
        return self.flash_combo.currentData()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SNES ROM Forge")
        self.resize(1000, 650)
        self.setStyleSheet(theme.STYLESHEET)

        self._roms: list[SNESRom] = []
        self._flash_profile = DEFAULT_FLASH_PROFILE
        self._boxart_fetcher = BoxArtFetcher()

        self._build_ui()
        self._rebuild_cards()

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)
        outer_layout = QHBoxLayout(central)

        left_column = QVBoxLayout()
        outer_layout.addLayout(left_column, stretch=1)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._cards_container = QWidget()
        self._cards_layout = QHBoxLayout(self._cards_container)
        self._cards_layout.setContentsMargins(4, 4, 4, 4)
        self._cards_layout.setSpacing(CARD_SPACING)
        self._cards_layout.setAlignment(Qt.AlignLeft)
        self._scroll_area.setWidget(self._cards_container)

        left_column.addWidget(self._scroll_area, stretch=1)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(2000)
        self._log.setMaximumHeight(140)
        left_column.addWidget(self._log)

        sidebar = QVBoxLayout()
        sidebar.addStretch()

        settings_button = QPushButton("⚙")
        settings_button.setToolTip("Configurações")
        settings_button.setCursor(Qt.PointingHandCursor)
        settings_button.setStyleSheet(theme.sidebar_button_style(theme.ACCENT_BLUE))
        settings_button.clicked.connect(self._on_open_settings)
        sidebar.addWidget(settings_button)

        sidebar.addSpacing(16)

        generate_button = QPushButton("↻")
        generate_button.setToolTip("Gerar BIN")
        generate_button.setCursor(Qt.PointingHandCursor)
        generate_button.setStyleSheet(theme.sidebar_button_style(theme.ACCENT_ORANGE))
        generate_button.clicked.connect(self._on_generate_bin)
        sidebar.addWidget(generate_button)

        sidebar.addStretch()
        outer_layout.addLayout(sidebar)

    def _log_line(self, text: str) -> None:
        self._log.appendPlainText(text)

    def _rebuild_cards(self) -> None:
        while self._cards_layout.count():
            item = self._cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        for index, rom in enumerate(self._roms):
            card = RomCardWidget(rom)
            card.remove_requested.connect(lambda i=index: self._on_remove_rom(i))
            self._cards_layout.addWidget(card)
            self._fetch_boxart_for(card)

            if index < len(self._roms) - 1:
                swap = _swap_button()
                swap.clicked.connect(lambda _checked=False, i=index: self._on_swap_roms(i, i + 1))
                self._cards_layout.addWidget(swap)

        drop_zone = DropZoneWidget()
        drop_zone.files_selected.connect(self._on_files_selected)
        self._cards_layout.addWidget(drop_zone)

    def _fetch_boxart_for(self, card: RomCardWidget) -> None:
        rom = card.rom

        def on_result(pixmap) -> None:
            if pixmap is None:
                return
            try:
                card.set_boxart(pixmap)
            except RuntimeError:
                pass  # card já foi removido/reconstruído antes da resposta chegar

        candidates = build_candidate_filenames(rom)
        self._boxart_fetcher.fetch(rom.filename, candidates, on_result)

    def _on_files_selected(self, paths: list[str]) -> None:
        for path in paths:
            try:
                rom = SNESRom.load(path)
            except OSError as exc:
                self._log_line(f"Erro ao ler '{Path(path).name}': {exc}")
                continue
            self._roms.append(rom)
            self._log_line(f"Importada: '{rom.filename}' ({rom.mapping}, {format_size(rom.rom_size_bytes)}).")
        self._rebuild_cards()

    def _on_remove_rom(self, index: int) -> None:
        rom = self._roms.pop(index)
        self._log_line(f"Removida: '{rom.filename}'.")
        self._rebuild_cards()

    def _on_swap_roms(self, i: int, j: int) -> None:
        self._roms[i], self._roms[j] = self._roms[j], self._roms[i]
        self._rebuild_cards()

    def _on_open_settings(self) -> None:
        dialog = SettingsDialog(self._flash_profile, self)
        if dialog.exec() == QDialog.Accepted:
            self._flash_profile = dialog.selected_flash_profile()
            self._log_line(f"Flash selecionada: {self._flash_profile.name}.")

    def _on_generate_bin(self) -> None:
        try:
            data, report = merge(self._roms, self._flash_profile)
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
