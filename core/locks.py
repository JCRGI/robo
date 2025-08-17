from __future__ import annotations

from pathlib import Path
from typing import Optional
from filelock import FileLock, Timeout

try:
    from flask import current_app  # pode não existir fora do app
except Exception:
    current_app = None  # type: ignore

def _locks_dir() -> Path:
    base: Path | None = None
    try:
        if current_app:
            base = Path(current_app.instance_path)  # type: ignore[attr-defined]
    except RuntimeError:
        base = None
    if base is None:
        base = Path.cwd() / "instance"
    path = base / "locks"
    path.mkdir(parents=True, exist_ok=True)
    return path

def avd_start_lock(timeout: float = 300.0) -> FileLock:
    return FileLock(str(_locks_dir() / "avd_start.lock"), timeout=timeout)

def try_acquire_avd_start(wait: bool = True, timeout: float = 300.0) -> Optional[FileLock]:
    """
    Tenta obter o lock global de inicialização de AVD.
    - wait=True: espera até 'timeout'.
    - wait=False: tenta e retorna None se estiver ocupado.
    """
    lock = avd_start_lock(timeout=timeout)
    try:
        lock.acquire(timeout=(timeout if wait else 0.01))
        return lock
    except Timeout:
        return None

def is_avd_start_busy() -> bool:
    """
    True se há um start de AVD em progresso (lock ocupado).
    """
    lock = try_acquire_avd_start(wait=False)
    if lock is None:
        return True
    try:
        lock.release()
    except Exception:
        pass
    return False
