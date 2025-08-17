from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path

from .android_sdk import env_with_java, tool_path


def listar_avds() -> list[str]:
    try:
        out = subprocess.check_output(["emulator", "-list-avds"], encoding="utf-8")
        return [l for l in out.strip().splitlines() if l]
    except Exception:
        return []


def criar_avd(
    nome_avd: str,
    package: str = "system-images;android-35;google_apis_playstore;x86_64",
    device_name: str = "pixel",
) -> None:
    avdmanager = tool_path("avdmanager")
    sdkmanager = tool_path("sdkmanager")
    env = env_with_java()
    # garante imagem instalada
    subprocess.run([sdkmanager, package], env=env, check=False)
    # cria/força override
    subprocess.run(
        [avdmanager, "create", "avd", "-n", nome_avd, "-k", package, "-d", device_name, "--force"],
        env=env,
        check=False,
    )


def deletar_avd(nome_avd: str) -> None:
    avd_dir = Path.home() / ".android" / "avd" / f"{nome_avd}.avd"
    ini_file = Path.home() / ".android" / "avd" / f"{nome_avd}.ini"

    def make_writable(func, path, _):
        try:
            os.chmod(path, stat.S_IWRITE)
        except Exception:
            pass
        func(path)

    try:
        if avd_dir.exists():
            shutil.rmtree(avd_dir, onerror=make_writable)
        if ini_file.exists():
            ini_file.unlink(missing_ok=True)  # py311+
    except Exception as e:
        raise Exception(f"Erro ao deletar AVD '{nome_avd}': {e}")
