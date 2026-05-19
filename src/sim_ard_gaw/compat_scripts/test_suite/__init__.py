"""Compatibility package for the owned campaign test suite.

Importers that still put `src/sim_ard_gaw/compat_scripts` on `PYTHONPATH` can
continue using `test_suite.*`. Submodules are loaded from the owned package at
`src/sim_ard_gaw/campaigns/test_suite`.
"""

from __future__ import annotations

import sys
from pathlib import Path


_RUNTIME_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _RUNTIME_ROOT.parent
_OWNED_PACKAGE = _RUNTIME_ROOT / "campaigns" / "test_suite"

src_text = str(_SRC_ROOT)
if src_text not in sys.path:
    sys.path.insert(0, src_text)

__path__ = [str(_OWNED_PACKAGE)]
__file__ = str(_OWNED_PACKAGE / "__init__.py")
