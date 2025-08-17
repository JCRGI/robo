from __future__ import annotations

import subprocess
import time

from core.utils import normalizar_porta_console

from .avd_manager import criar_avd, listar_avds


def listar_emuladores_ativos() -> list[str]:
    try:
        out = subprocess.check_output(["adb", "devices"], encoding="utf-8")
        lines = [l.strip() for l in out.strip().splitlines()[1:] if l.strip()]
        return [l.split()[0] for l in lines if "emulator-" in l]
    except Exception:
        return []


def start_emulator(nome_avd: str, port: int, modo_janela: bool = True) -> None:
    port = normalizar_porta_console(port)
    if nome_avd not in listar_avds():
        criar_avd(nome_avd)
    cmd = ["emulator", "-avd", nome_avd, "-port", str(port)]
    if not modo_janela:
        cmd += ["-no-audio", "-no-window"]
    subprocess.Popen(cmd)
    time.sleep(3)


def wait_for_online(serial: str, timeout: float = 30.0) -> bool:
    ini = time.time()
    while time.time() - ini < timeout:
        try:
            out = subprocess.check_output(["adb", "devices"], encoding="utf-8")
            for line in out.strip().splitlines()[1:]:
                if serial in line and "device" in line:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def wait_for_boot_completed(serial: str, timeout: float = 30.0) -> bool:
    ini = time.time()
    while time.time() - ini < timeout:
        try:
            boot = subprocess.check_output(
                ["adb", "-s", serial, "shell", "getprop", "sys.boot_completed"], encoding="utf-8"
            ).strip()
            if boot == "1":
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def _run(serial: str, *args: str, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["adb", "-s", serial, *args], check=check, capture_output=True, text=True)


def unlock_and_home(serial: str) -> None:
    try:
        _run(serial, "shell", "input", "keyevent", "224")  # wake
        _run(serial, "shell", "wm", "dismiss-keyguard")
        _run(serial, "shell", "input", "keyevent", "82")   # unlock
        _run(serial, "shell", "input", "keyevent", "3")    # HOME
    except Exception:
        pass


def is_package_installed(serial: str, pacote: str) -> bool:
    try:
        out = _run(serial, "shell", "pm", "list", "packages", pacote).stdout
        return pacote in out
    except Exception:
        return False


def launch_app(serial: str, pacote: str) -> None:
    """
    Tenta abrir via monkey; em caso de falha, resolve a main-activity e usa am start.
    """
    unlock_and_home(serial)
    # pequena estabilização do package manager
    time.sleep(2)

    # 1) tenta monkey
    res = _run(serial, "shell", "monkey", "-p", pacote, "-c", "android.intent.category.LAUNCHER", "1")
    if res.returncode == 0 and "Events injected: 1" in (res.stdout + res.stderr):
        return

    # 2) fallback: resolver atividade principal e abrir com am
    try:
        out = _run(serial, "shell", "cmd", "package", "resolve-activity", "--brief", pacote).stdout.strip()
        # normalmente retorna algo como: com.disney.wdw.android/com.disney.wdw.android.SplashActivity
        comp = out.splitlines()[-1] if out else ""
        if "/" in comp:
            _run(serial, "shell", "am", "start", "-n", comp, check=False)
            return
    except Exception:
        pass

    # 3) último recurso: am start pelo package (pode abrir chooser)
    _run(serial, "shell", "am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-n", f"{pacote}/.MainActivity", check=False)


def stop_emulator(serial: str) -> None:
    subprocess.run(["adb", "-s", serial, "emu", "kill"], check=False)
    for _ in range(10):
        time.sleep(0.5)
        if serial not in listar_emuladores_ativos():
            break
