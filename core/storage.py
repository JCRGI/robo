import json
import os

DISPOSITIVOS_PATH = "dispositivos.json"


def carregar_dispositivos():
    if not os.path.exists(DISPOSITIVOS_PATH):
        return []
    with open(DISPOSITIVOS_PATH, "r") as f:
        return json.load(f)


def salvar_dispositivos(lista):
    with open(DISPOSITIVOS_PATH, "w") as f:
        json.dump(lista, f, indent=4)
