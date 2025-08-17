from __future__ import annotations

import os
from pathlib import Path


def sdk_path() -> str:
    return (
        os.environ.get("ANDROID_HOME")
        or os.environ.get("ANDROID_SDK_ROOT")
        or str(Path.home() / "AppData" / "Local" / "Android" / "Sdk")
    )


def java_home() -> str | None:
    return os.environ.get("JAVA_HOME")


def tool_path(tool: str) -> str:
    # avdmanager/sdkmanager ficam em cmdline-tools/latest/bin
    return str(Path(sdk_path()) / "cmdline-tools" / "latest" / "bin" / f"{tool}.bat")


def env_with_java() -> dict:
    env = os.environ.copy()
    jh = java_home()
    if jh:
        env["JAVA_HOME"] = jh
    return env
