# Funções auxiliares

import re
import subprocess
from typing import Optional, Set

PORTA_MIN = 5554
PORTA_MAX = 5680


def limpar_nome_avd(nome: str) -> str:
    nome_limpo = nome.strip().replace(" ", "_")
    return re.sub(r"[^a-zA-Z0-9._-]", "", nome_limpo)


def normalizar_porta_console(porta: int) -> int:
    p = int(porta)
    if p < PORTA_MIN:
        p = PORTA_MIN
    if p > PORTA_MAX:
        p = PORTA_MAX
    if p % 2 == 1:
        p -= 1  # console precisa ser PAR
    return p


def portas_em_uso() -> Set[int]:
    usados: Set[int] = set()
    try:
        out = subprocess.check_output(["adb", "devices"], encoding="utf-8", errors="ignore")
        for line in (l.strip() for l in out.splitlines()[1:] if l.strip()):
            if line.startswith("emulator-"):
                try:
                    usados.add(int(line.split()[0].split("-")[1]))
                except Exception:
                    pass
    except Exception:
        pass
    return usados


def proxima_porta_livre(preferida: Optional[int] = None) -> int:
    usados = portas_em_uso()
    start = normalizar_porta_console(preferida) if preferida is not None else PORTA_MIN
    # varre para frente
    p = start
    while p <= PORTA_MAX:
        if p not in usados:
            return p
        p += 2
    # volta ao início
    p = PORTA_MIN
    while p < start:
        if p not in usados:
            return p
        p += 2
    raise RuntimeError("Não há portas de console livres no intervalo 5554–5680.")
