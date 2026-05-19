"""Compatibility helpers that delegate old script names to owned homes."""

from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path
from types import ModuleType


RUNTIME_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = RUNTIME_ROOT.parent


def _target(relative_path: str) -> Path:
    return RUNTIME_ROOT / relative_path


def _ensure_paths(target: Path) -> None:
    for path in (SRC_ROOT, target.parent):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)


def load_owned_module(relative_path: str) -> ModuleType:
    target = _target(relative_path)
    _ensure_paths(target)
    module_name = "_sim_ard_gaw_owned_" + relative_path.replace("/", "_").replace(".", "_")
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load owned module at {target}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def export_owned_module(relative_path: str, namespace: dict[str, object]) -> ModuleType:
    module = load_owned_module(relative_path)
    for key, value in vars(module).items():
        if key in {
            "__builtins__",
            "__cached__",
            "__file__",
            "__loader__",
            "__name__",
            "__package__",
            "__spec__",
        }:
            continue
        namespace[key] = value
    namespace["__doc__"] = module.__doc__
    return module


def run_owned_script(relative_path: str) -> None:
    target = _target(relative_path)
    _ensure_paths(target)
    runpy.run_path(str(target), run_name="__main__")
