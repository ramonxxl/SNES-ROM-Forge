# SNES ROM Forge

Ferramenta para fazer merge de ROMs de Super Nintendo (LoROM/HiROM) em uma única imagem
para gravação em memória flash (padrão: 29L3211, 4 MB / 32 Mbit).

## O que faz

- Detecta e remove header SMC de 512 bytes, quando presente.
- Detecta automaticamente o mapeamento (LoROM ou HiROM) de cada ROM.
- Corrige o checksum interno de cada ROM individualmente.
- Concatena as ROMs na ordem escolhida (merge sequencial).
- Preenche o restante da capacidade da flash selecionada com `0xFF`.
- Bloqueia merges inválidos: mapeamento misto, ROM não identificada, ou tamanho total maior
  que a capacidade da flash.

## Como rodar

```
pip install -r requirements.txt
python main.py
```

## Como rodar os testes

```
pip install -r requirements.txt
pytest
```

## Como gerar o executável (.exe)

```
pip install -r requirements-build.txt
python -m PyInstaller "SNES ROM Forge.spec"
```

O executável fica em `dist/SNES ROM Forge.exe` (arquivo único, sem console, ~48 MB — inclui
o runtime do PySide6/Qt). O arquivo `SNES ROM Forge.spec` já está configurado (onefile,
windowed); reaproveite-o em vez de rodar `pyinstaller` direto com flags para manter builds
reproduzíveis. As pastas `build/` e `dist/` são geradas a cada build e não devem ser versionadas.

## Fora do escopo desta versão

- Perfis de placa/CPLD com bank-switching customizado (endereços embaralhados).
- Modo de bancos manual (posicionar cada ROM em um offset específico).
- Salvar/abrir projeto (`.srmproj`).
- Drag-and-drop na lista de ROMs.
