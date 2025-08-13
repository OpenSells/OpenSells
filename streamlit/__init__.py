"""Expose the official Streamlit package while bundling app modules."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_pkg = sys.modules[__name__]
_repo_root = Path(__file__).resolve().parent.parent
_repo_path = str(_repo_root)

orig_sys_path = list(sys.path)
base_path = []
try:
    sys.path = [p for p in sys.path if p != _repo_path]
    spec = importlib.util.find_spec(__name__)
    if spec and spec.origin != __file__ and spec.loader is not None:
        real_streamlit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(real_streamlit)
        for attr in dir(real_streamlit):
            setattr(_pkg, attr, getattr(real_streamlit, attr))
        base_path = list(getattr(real_streamlit, "__path__", []))
finally:
    sys.path = orig_sys_path

_pkg.__path__ = base_path + [str(Path(__file__).resolve().parent)]
