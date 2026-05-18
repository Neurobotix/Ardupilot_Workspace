"""Manifest read/write interface.

The manifest is the durable record of every attempt: which cases were
attempted, when, with what verdict. The Phase-1 implementation is
`LegacyManifest`, which delegates to `run_one.load_manifest` /
`save_manifest` so the wind-matrix campaign log keeps working
unchanged.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from .models import AttemptRecord, TestCase


class Manifest(ABC):
    """Generic manifest contract."""

    @abstractmethod
    def load(self) -> dict[str, Any]:
        """Return the current manifest object."""

    @abstractmethod
    def save(self, manifest: dict[str, Any]) -> None:
        """Persist atomically."""

    @abstractmethod
    def accepted_count(self, case: TestCase) -> int:
        """How many accepted runs the case currently has."""

    @abstractmethod
    def next_attempt_index(self, case: TestCase) -> int:
        """Next attempt index for this case, used in directory naming."""

    @abstractmethod
    def append_attempt(self, record: AttemptRecord) -> None:
        """Append an attempt record and persist."""


class LegacyManifest(Manifest):
    """Delegates to `run_one.load_manifest` / `save_manifest`.

    This keeps the wind-matrix campaign-log schema identical during the
    Phase-1 wrap. Phase 3 introduces a generic JSON manifest written
    additively next to the legacy one; only after that can we retire the
    delegation.

    Acceptance counting is policy-aware: when ``accept_square_only`` is
    False, legacy attempts with ``status == "success_square_only"`` are
    treated as partial successes and do not contribute to the accepted
    count. This prevents an older square-only manifest row from silently
    satisfying acceptance for a new full-mission policy.
    """

    def __init__(
        self,
        campaign_root: Path,
        *,
        require_analysis: bool = False,
        accept_square_only: bool = False,
    ) -> None:
        from . import _legacy
        self._run_one = _legacy.run_one_module()
        self._root = campaign_root
        self._require_analysis = require_analysis
        self._accept_square_only = accept_square_only

    def load(self) -> dict[str, Any]:
        return self._run_one.load_manifest(self._root)

    def save(self, manifest: dict[str, Any]) -> None:
        self._run_one.save_manifest(self._root, manifest)

    def accepted_count(self, case: TestCase) -> int:
        manifest = self.load()
        key = case.case_id
        successes = self._run_one.combo_successes(
            manifest, key, require_analysis=self._require_analysis,
        )
        if self._accept_square_only:
            return len(successes)
        return sum(
            1 for attempt in successes
            if attempt.get("status") != "success_square_only"
        )

    def next_attempt_index(self, case: TestCase) -> int:
        manifest = self.load()
        return self._run_one.next_attempt_index(self._root, manifest, case.case_id)

    def append_attempt(self, record: AttemptRecord) -> None:
        # Phase 1: legacy run_one writes its own attempt rows inside
        # `run_one.run_one`. The framework does not duplicate that here.
        # Phase 3 will move attempt-record assembly into the framework
        # and this method becomes the canonical write path.
        return None
