from __future__ import annotations
import threading
from typing import Any, Callable

def fire_and_forget(fn: Callable[..., Any], *args, **kwargs) -> None:
    t = threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True)
    t.start()