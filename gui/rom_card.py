"""Card visual de uma ROM importada (inspirado no site antigo do usuário)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from core.rom import SNESRom
from gui import theme

CARD_WIDTH = 190
BANNER_HEIGHT = 90


def _banner_color(title: str) -> str:
    """Cor determinística (baseada no título) pro banner do card."""
    palette = [theme.ACCENT_BLUE, theme.ACCENT_PURPLE, theme.ACCENT_GREEN, theme.ACCENT_ORANGE]
    return palette[hash(title) % len(palette)] if title else theme.ACCENT_GRAY


def _make_badge(text: str, color: str) -> QLabel:
    badge = QLabel(text)
    badge.setStyleSheet(theme.badge_style(color))
    badge.setAlignment(Qt.AlignCenter)
    return badge


class RomCardWidget(QFrame):
    remove_requested = Signal()

    def __init__(self, rom: SNESRom, parent=None):
        super().__init__(parent)
        self.rom = rom
        self.setFixedWidth(CARD_WIDTH)
        self.setStyleSheet(f"""
            RomCardWidget {{
                background: {theme.BG_CARD};
                border: 1px solid {theme.BORDER};
                border-radius: 10px;
            }}
        """)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(8)

        self._banner = QLabel()
        self._banner.setFixedSize(CARD_WIDTH, BANNER_HEIGHT)
        self._banner.setAlignment(Qt.AlignCenter)
        self._banner.setWordWrap(True)
        self._show_placeholder_banner()

        remove_button = QPushButton("✕", self._banner)
        remove_button.setFixedSize(20, 20)
        remove_button.move(CARD_WIDTH - 26, 6)
        remove_button.setCursor(Qt.PointingHandCursor)
        remove_button.setStyleSheet(f"""
            QPushButton {{
                background: rgba(0, 0, 0, 0.35);
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {theme.ACCENT_RED};
            }}
        """)
        remove_button.clicked.connect(self.remove_requested.emit)
        remove_button.raise_()

        layout.addWidget(self._banner)

        info_grid = QGridLayout()
        info_grid.setContentsMargins(10, 0, 10, 0)
        info_grid.setHorizontalSpacing(8)
        info_grid.setVerticalSpacing(6)
        info_grid.setColumnStretch(0, 0)
        info_grid.setColumnStretch(1, 1)

        mapping_label = {"lorom": "LoROM", "hirom": "HiROM", "unknown": "?"}[self.rom.mapping]
        mapping_color = theme.MAPPING_COLORS[self.rom.mapping]

        size_kb = self.rom.rom_size_bytes / 1024
        size_text = f"{size_kb:.0f} KB" if size_kb < 1024 else f"{size_kb / 1024:.2f} MB"

        checksum_text = "Válido" if self.rom.checksum_valid else "Corrigido"
        checksum_color = theme.ACCENT_GREEN if self.rom.checksum_valid else theme.ACCENT_ORANGE

        header_text = "Sim" if self.rom.has_smc_header else "Não"
        header_color = theme.ACCENT_ORANGE if self.rom.has_smc_header else theme.ACCENT_GRAY

        rows = [
            ("Mapping", mapping_label, mapping_color),
            ("Tamanho", size_text, theme.ACCENT_ORANGE),
            ("Header SMC", header_text, header_color),
            ("Checksum", checksum_text, checksum_color),
        ]

        for row_index, (label_text, value_text, color) in enumerate(rows):
            label = QLabel(label_text)
            label.setStyleSheet(f"color: {theme.TEXT_MUTED}; font-size: 12px;")
            info_grid.addWidget(label, row_index, 0)
            info_grid.addWidget(_make_badge(value_text, color), row_index, 1, alignment=Qt.AlignRight)

        layout.addLayout(info_grid)
        layout.addStretch()

    def _show_placeholder_banner(self) -> None:
        color = _banner_color(self.rom.title or self.rom.filename)
        self._banner.setPixmap(QPixmap())  # limpa qualquer capa anterior
        self._banner.setText(self.rom.title or self.rom.filename)
        self._banner.setStyleSheet(f"""
            background: {color};
            color: white;
            font-weight: 700;
            font-size: 13px;
            padding: 8px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
        """)

    def set_boxart(self, pixmap: QPixmap) -> None:
        """Substitui o banner colorido pela capa real do jogo, se uma for encontrada."""
        scaled = pixmap.scaled(
            CARD_WIDTH,
            BANNER_HEIGHT,
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        x = max(0, (scaled.width() - CARD_WIDTH) // 2)
        y = max(0, (scaled.height() - BANNER_HEIGHT) // 2)
        cropped = scaled.copy(x, y, CARD_WIDTH, BANNER_HEIGHT)

        self._banner.setText("")
        self._banner.setStyleSheet("border-top-left-radius: 10px; border-top-right-radius: 10px;")
        self._banner.setPixmap(cropped)
