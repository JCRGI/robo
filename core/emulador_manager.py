from __future__ import annotations

import warnings

from core.gateways.emulator_ctl import (
    launch_app,
    wait_for_boot_completed,
    wait_for_online,
)
from core.gateways.emulator_ctl import (
    start_emulator as _start,
)

DEFAULT_PACKAGE = "com.disney.wdw.android"


def iniciar_emulador(
    nome_avd: str,
    porta: int,
    modo_janela: bool = True,
    abrir_app: bool = True,
    pacote: str | None = None,
) -> None:
    """
    Mantém assinatura pública, mas delega para gateways.
    """
    _start(nome_avd, porta, modo_janela=modo_janela)
    serial = f"emulator-{porta}"
    if not wait_for_online(serial, timeout=30):
        print(f"[ERRO] Timeout: {serial} não ficou online.")
        return
    if not wait_for_boot_completed(serial, timeout=60):
        print(f"[ERRO] Timeout: {serial} não completou boot.")
        return
    pkg = pacote or (DEFAULT_PACKAGE if abrir_app else None)
    if pkg:
        try:
            launch_app(serial, pkg)
            print(f"[OK] App {pkg} aberto automaticamente em {serial}")
        except Exception as e:
            print(f"[ERRO] Ao abrir app {pkg}: {e}")


def esperar_home_e_clicar_purchase(*args, **kwargs):
    warnings.warn(
        "esperar_home_e_clicar_purchase foi descontinuada. "
        "Use OcrService.click_text_with_scroll(serial, 'Purchase').",
        DeprecationWarning,
        stacklevel=2,
    )
