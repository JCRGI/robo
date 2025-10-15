"""Cria estrutura de diretórios necessários"""

import os

dirs = [
    'static/screenshots',
    'static/ocr',
    'temp',
    'logs'
]

print("📁 Criando diretórios...")
for d in dirs:
    os.makedirs(d, exist_ok=True)
    print(f"  ✅ {d}")

print("\n✅ Estrutura criada!")