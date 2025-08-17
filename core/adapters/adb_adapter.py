from __future__ import annotations

import os
import subprocess
from typing import Iterable

from core.adb_manager import AdbManager  # legado
from core.errors import ADBError
from core.gateways.emulator_ctl import wait_for_boot_completed, wait_for_online


class AdbAdapter:
    def __init__(self) -> None:
        self._adb = AdbManager()

    # legado (mantido)
    def connect(self) -> None:
        try:
            self._adb.connect_device()
        except Exception as e:
            raise ADBError(f"Falha ao conectar ADB: {e}") from e

    def set_device_by_serial(self, serial: str) -> None:
        try:
            dev = next(d for d in self._adb.client.devices() if d.serial == serial)
            self._adb.device = dev
        except StopIteration as e:
            raise ADBError(f"Dispositivo {serial} não encontrado.") from e

    def list_serials(self) -> Iterable[str]:
        return [d.serial for d in self._adb.client.devices()]

    # novo: garante dispositivo pronto (por serial)
    def ensure_ready(self, serial: str, wait_boot: bool = True, t_online: float = 120.0, t_boot: float = 180.0) -> None:
        try:
            subprocess.run(["adb", "-s", serial, "reconnect"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        if not wait_for_online(serial, timeout=t_online):
            raise ADBError(f"Dispositivo {serial} não ficou online em {t_online}s.")
        if wait_boot and not wait_for_boot_completed(serial, timeout=t_boot):
            raise ADBError(f"Boot do {serial} não concluiu em {t_boot}s.")

    # novos: operações por serial (stateless)
    def capture_screen_for(self, serial: str, path: str) -> None:
        try:
            res = subprocess.run(["adb", "-s", serial, "exec-out", "screencap", "-p"], check=True, stdout=subprocess.PIPE)
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "wb") as f:
                f.write(res.stdout)
        except subprocess.CalledProcessError as e:
            raise ADBError(f"Falha ao capturar screenshot: {e}") from e

    def tap_for(self, serial: str, x: int, y: int) -> None:
        try:
            subprocess.run(["adb", "-s", serial, "shell", "input", "tap", str(x), str(y)], check=True)
        except subprocess.CalledProcessError as e:
            raise ADBError(f"Falha ao tocar na tela: {e}") from e

    def shell_for(self, serial: str, cmd: str) -> str:
        try:
            res = subprocess.run(["adb", "-s", serial, "shell", cmd], check=True, capture_output=True, text=True)
            return (res.stdout or "") + (res.stderr or "")
        except subprocess.CalledProcessError as e:
            raise ADBError(f"Falha ao executar shell '{cmd}': {e}") from e

    def dump_ui_xml(self, serial: str, compressed: bool = True) -> str:
        """
        Retorna o XML do layout atual (uiautomator). Tenta /dev/tty; se falhar, usa /sdcard.
        """
        args = ["adb", "-s", serial, "shell", "uiautomator", "dump"]
        if compressed:
            args.insert(6, "--compressed")
        # 1) dump para stdout (/dev/tty)
        try:
            res = subprocess.run(args + ["/dev/tty"], check=True, capture_output=True, text=True)
            return res.stdout
        except Exception:
            pass
        # 2) dump para arquivo e cat
        try:
            path = "/sdcard/uidump.xml"
            subprocess.run(args + [path], check=True, capture_output=True, text=True)
            res = subprocess.run(["adb", "-s", serial, "shell", "cat", path], check=True, capture_output=True, text=True)
            return res.stdout
        except subprocess.CalledProcessError as e:
            raise ADBError(f"Falha ao obter UI dump: {e}") from e
