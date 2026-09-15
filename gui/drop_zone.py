"""Área de arrastar-e-soltar (ou clicar) para importar novas ROMs."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFileDialog, QFrame, QLabel, QVBoxLayout

from gui import theme
from gui.rom_card import CARD_WIDTH

ROM_FILE_FILTER = "ROMs SNES (*.sfc *.smc *.bin);;Todos os arquivos (*)"
ROM_EXTENSIONS = (".sfc", ".smc", ".bin")


class DropZoneWidget(QFrame):
    files_selected = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(CARD_WIDTH)
        self.setMinimumHeight(230)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self._apply_style(active=False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel("\U0001F3AE")
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 36px; background: transparent; border: none;")
        layout.addWidget(icon_label)

        text_label = QLabel("clique ou arraste\na ROM para esta área")
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setWordWrap(True)
        text_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; background: transparent; border: none;")
        layout.addWidget(text_label)

    def _apply_style(self, active: bool) -> None:
        border_color = theme.ACCENT_BLUE if active else theme.BORDER
        self.setStyleSheet(f"""
            DropZoneWidget {{
                border: 2px dashed {border_color};
                border-radius: 10px;
                background: {theme.BG_PANEL if active else 'transparent'};
            }}
        """)

    def mousePressEvent(self, event) -> None:
        paths, _ = QFileDialog.getOpenFileNames(self, "Adicionar ROM(s)", "", ROM_FILE_FILTER)
        if paths:
            self.files_selected.emit(paths)

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            self._apply_style(active=True)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._apply_style(active=False)

    def dropEvent(self, event) -> None:
        self._apply_style(active=False)
        paths = [
            url.toLocalFile()
            for url in event.mimeData().urls()
            if url.toLocalFile().lower().endswith(ROM_EXTENSIONS)
        ]
        if paths:
            self.files_selected.emit(paths)
        event.acceptProposedAction()
