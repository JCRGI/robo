import json
import os

DISPOSITIVOS_PATH = "dispositivos.json"
EMULADORES_PATH = "emuladores.json"

def carregar_dispositivos():
    if not os.path.exists(DISPOSITIVOS_PATH):
        return []
    with open(DISPOSITIVOS_PATH, 'r') as f:
        return json.load(f)

def salvar_dispositivos(lista):
    with open(DISPOSITIVOS_PATH, 'w') as f:
        json.dump(lista, f, indent=4)

def carregar_emuladores():
    if not os.path.exists(EMULADORES_PATH):
        return []
    with open(EMULADORES_PATH, 'r') as f:
        return json.load(f)

def salvar_emuladores(lista):
    with open(EMULADORES_PATH, 'w') as f:
        json.dump(lista, f, indent=4)
