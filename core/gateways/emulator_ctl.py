"""Controlador de emuladores Android via ADB"""

import subprocess
import time
import os
from typing import List, Tuple, Optional

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


# ============================================================================
# 🆕 NOVAS FUNÇÕES ADICIONADAS
# ============================================================================

def executar_comando_adb(serial: str, comando: str, timeout: int = 30) -> Tuple[bool, str]:
    """
    Executa comando ADB em um emulador específico.
    
    Args:
        serial: Serial do emulador (ex: emulator-5560)
        comando: Comando ADB a executar
        timeout: Timeout em segundos
        
    Returns:
        Tuple (sucesso, output)
    """
    try:
        cmd_completo = f'adb -s {serial} {comando}'
        print(f"[ADB] Executando: {cmd_completo}")
        
        resultado = subprocess.run(
            cmd_completo,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        sucesso = resultado.returncode == 0
        output = resultado.stdout.strip() if sucesso else resultado.stderr.strip()
        
        if not sucesso:
            print(f"[ADB] Erro: {output}")
        
        return sucesso, output
        
    except subprocess.TimeoutExpired:
        print(f"[ADB] Timeout após {timeout}s")
        return False, f"Timeout após {timeout}s"
    except Exception as e:
        print(f"[ADB] Exceção: {e}")
        return False, str(e)


def swipe(serial: str, x1: int, y1: int, x2: int, y2: int, duration: int = 300) -> bool:
    """
    Realiza um swipe na tela do emulador.
    
    Args:
        serial: Serial do emulador
        x1, y1: Coordenadas iniciais
        x2, y2: Coordenadas finais
        duration: Duração do swipe em milissegundos
        
    Returns:
        True se sucesso
    """
    try:
        print(f"[SWIPE] {serial}: ({x1},{y1}) -> ({x2},{y2}) em {duration}ms")
        
        # Comando ADB para swipe
        comando = f"shell input swipe {x1} {y1} {x2} {y2} {duration}"
        sucesso, output = executar_comando_adb(serial, comando, timeout=10)
        
        if sucesso:
            print(f"[SWIPE] ✅ Swipe executado com sucesso")
            time.sleep(0.5)  # Aguardar animação
        else:
            print(f"[SWIPE] ❌ Falha: {output}")
        
        return sucesso
        
    except Exception as e:
        print(f"[SWIPE] ❌ Exceção: {e}")
        return False


def tap(serial: str, x: int, y: int) -> bool:
    """
    Toca em uma coordenada específica na tela.
    
    Args:
        serial: Serial do emulador
        x, y: Coordenadas do toque
        
    Returns:
        True se sucesso
    """
    try:
        print(f"[TAP] {serial}: ({x},{y})")
        
        comando = f"shell input tap {x} {y}"
        sucesso, output = executar_comando_adb(serial, comando, timeout=10)
        
        if sucesso:
            print(f"[TAP] ✅ Tap executado")
        else:
            print(f"[TAP] ❌ Falha: {output}")
        
        return sucesso
        
    except Exception as e:
        print(f"[TAP] ❌ Exceção: {e}")
        return False


def get_screen_size(serial: str) -> Optional[Tuple[int, int]]:
    """
    Obtém o tamanho da tela do emulador.
    
    Returns:
        Tuple (width, height) ou None se falhar
    """
    try:
        comando = "shell wm size"
        sucesso, output = executar_comando_adb(serial, comando, timeout=10)
        
        if sucesso and output:
            # Output: "Physical size: 1080x1920"
            if ":" in output:
                size_str = output.split(":")[-1].strip()
                if "x" in size_str:
                    width, height = map(int, size_str.split("x"))
                    print(f"[SCREEN] {serial}: {width}x{height}")
                    return (width, height)
        
        print(f"[SCREEN] ⚠️ Não foi possível obter tamanho da tela")
        return None
        
    except Exception as e:
        print(f"[SCREEN] ❌ Exceção: {e}")
        return None


def press_key(serial: str, keycode: int) -> bool:
    """
    Pressiona uma tecla no emulador.
    
    Args:
        serial: Serial do emulador
        keycode: Código da tecla (KEYCODE_BACK = 4, KEYCODE_HOME = 3, etc)
        
    Returns:
        True se sucesso
    """
    try:
        print(f"[KEY] {serial}: keycode {keycode}")
        
        comando = f"shell input keyevent {keycode}"
        sucesso, output = executar_comando_adb(serial, comando, timeout=10)
        
        if sucesso:
            print(f"[KEY] ✅ Tecla pressionada")
        else:
            print(f"[KEY] ❌ Falha: {output}")
        
        return sucesso
        
    except Exception as e:
        print(f"[KEY] ❌ Exceção: {e}")
        return False


def capture_screen(serial: str, output_path: str) -> bool:
    """
    Captura screenshot do emulador.
    
    Args:
        serial: Serial do emulador
        output_path: Caminho onde salvar a imagem
        
    Returns:
        True se sucesso
    """
    try:
        import os
        
        print(f"[SCREEN] Capturando {serial} -> {output_path}")
        
        # Garantir que diretório existe
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        
        # Caminho temporário no dispositivo
        temp_path = "/sdcard/screenshot_temp.png"
        
        # 1. Capturar no dispositivo
        comando_capture = f"shell screencap -p {temp_path}"
        sucesso, output = executar_comando_adb(serial, comando_capture, timeout=15)
        
        if not sucesso:
            print(f"[SCREEN] ❌ Falha ao capturar: {output}")
            return False
        
        # 2. Puxar para o computador
        comando_pull = f"pull {temp_path} {output_path}"
        sucesso, output = executar_comando_adb(serial, comando_pull, timeout=30)
        
        if not sucesso:
            print(f"[SCREEN] ❌ Falha ao puxar: {output}")
            return False
        
        # 3. Limpar arquivo temporário
        comando_rm = f"shell rm {temp_path}"
        executar_comando_adb(serial, comando_rm, timeout=5)
        
        # Verificar se arquivo foi criado
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print(f"[SCREEN] ✅ Screenshot salvo: {os.path.getsize(output_path)} bytes")
            return True
        else:
            print(f"[SCREEN] ❌ Arquivo não foi criado ou está vazio")
            return False
        
    except Exception as e:
        print(f"[SCREEN] ❌ Exceção: {e}")
        return False
