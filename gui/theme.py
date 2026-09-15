"""Paleta e stylesheet (QSS) compartilhados pela interface."""

from __future__ import annotations

BG = "#1b1e26"
BG_PANEL = "#242832"
BG_CARD = "#2c313c"
BORDER = "#3a4050"
TEXT = "#e8eaf0"
TEXT_MUTED = "#9aa1b0"

ACCENT_BLUE = "#3b82f6"
ACCENT_PURPLE = "#8b5cf6"
ACCENT_ORANGE = "#f59e0b"
ACCENT_GREEN = "#22c55e"
ACCENT_RED = "#ef4444"
ACCENT_GRAY = "#5b6272"

# Cor de destaque por mapping, usada no banner do card e no badge de tipo.
MAPPING_COLORS = {
    "lorom": ACCENT_BLUE,
    "hirom": ACCENT_PURPLE,
    "unknown": ACCENT_GRAY,
}

STYLESHEET = f"""
QMainWindow, QWidget#central {{
    background: {BG};
}}

QWidget {{
    color: {TEXT};
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QPlainTextEdit {{
    background: {BG_PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    color: {TEXT_MUTED};
    font-family: Consolas, monospace;
    font-size: 12px;
    padding: 6px;
}}

QComboBox {{
    background: {BG_CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    color: {TEXT};
}}

QDialog {{
    background: {BG};
}}

QLabel#sectionLabel {{
    color: {TEXT_MUTED};
    font-weight: 600;
}}
"""


def sidebar_button_style(color: str) -> str:
    return f"""
        QPushButton {{
            background: {color};
            border: none;
            border-radius: 12px;
            min-width: 64px;
            min-height: 64px;
            font-size: 26px;
        }}
        QPushButton:hover {{
            background: {color};
            border: 2px solid {TEXT};
        }}
        QPushButton:pressed {{
            background: {BORDER};
        }}
        QPushButton:disabled {{
            background: {ACCENT_GRAY};
            color: {TEXT_MUTED};
        }}
    """


def badge_style(color: str) -> str:
    return f"""
        background: {color};
        color: white;
        font-weight: 600;
        font-size: 11px;
        border-radius: 5px;
        padding: 2px 8px;
    """
