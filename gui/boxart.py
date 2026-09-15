"""Busca de capas de jogos (melhor esforço, sem chave de API) via libretro-thumbnails.

Fonte: https://github.com/libretro-thumbnails (o mesmo acervo usado pelo RetroArch),
gratuito e sem cadastro. Como o título interno do cabeçalho da ROM costuma vir
truncado/abreviado, a busca tenta primeiro o nome do próprio arquivo importado
(geralmente mais parecido com o nome oficial do jogo) e, se não achar, tenta o
título interno. Quando nenhuma tentativa encontra a capa (ou não há internet),
o card simplesmente mantém o banner colorido — a busca nunca bloqueia o uso do
programa nem impede gerar o BIN.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Callable
from urllib.parse import quote

from PySide6.QtCore import QUrl
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from core.rom import SNESRom

_REPO_BASE = (
    "https://raw.githubusercontent.com/libretro-thumbnails/"
    "Nintendo_-_Super_Nintendo_Entertainment_System/master/Named_Boxarts/"
)
_REGIONS = ["USA", "World", "Europe", "Japan"]

_CACHE_DIR = Path.home() / ".snes_rom_forge" / "boxart_cache"


def build_candidate_filenames(rom: SNESRom) -> list[str]:
    """Nomes de arquivo candidatos no repositório, na ordem em que devem ser tentados."""
    names = [Path(rom.filename).stem]

    title = (rom.title or "").strip().title()
    if title and title not in names:
        names.append(title)

    return [f"{name} ({region}).png" for name in names for region in _REGIONS]


def _cache_path_for(cache_key: str) -> Path:
    digest = hashlib.sha1(cache_key.encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{digest}.png"


class BoxArtFetcher:
    """Busca a capa de um jogo (melhor esforço) e mantém cache local em disco."""

    def __init__(self):
        self._manager = QNetworkAccessManager()
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def fetch(self, cache_key: str, candidates: list[str], on_result: Callable[[QPixmap | None], None]) -> None:
        """Tenta cada nome candidato em ordem; chama `on_result(pixmap_ou_None)` uma vez, no fim."""
        cache_path = _cache_path_for(cache_key)
        if cache_path.exists():
            pixmap = QPixmap(str(cache_path))
            on_result(pixmap if not pixmap.isNull() else None)
            return

        self._try_next(list(candidates), cache_path, on_result)

    def _try_next(
        self,
        remaining: list[str],
        cache_path: Path,
        on_result: Callable[[QPixmap | None], None],
    ) -> None:
        if not remaining:
            on_result(None)
            return

        filename = remaining.pop(0)
        url = QUrl(_REPO_BASE + quote(filename))
        reply = self._manager.get(QNetworkRequest(url))

        def handle_finished() -> None:
            reply.deleteLater()
            if reply.error() == QNetworkReply.NoError:
                data = bytes(reply.readAll())
                pixmap = QPixmap()
                if pixmap.loadFromData(data) and not pixmap.isNull():
                    cache_path.write_bytes(data)
                    on_result(pixmap)
                    return
            self._try_next(remaining, cache_path, on_result)

        reply.finished.connect(handle_finished)
