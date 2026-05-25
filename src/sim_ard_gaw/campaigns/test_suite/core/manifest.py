"""Manifest read/write interface.

The manifest is the durable record of every attempt: which cases were
attempted, when, with what verdict. `LegacyManifest` delegates legacy
wind-matrix loading and saving to `run_one.load_manifest` /
`save_manifest`, while exposing an additive generic view for the
framework.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict
from enum import Enum
from pathlib import Path
from typing import Any

from sim_ard_gaw.campaigns.manifest_safety import campaign_manifest_lock
from sim_ard_gaw.campaigns.status import (
    legacy_analysis_succeeded,
    terminal_status_for_legacy,
)

from .models import (
    AnalysisResult,
    AttemptRecord,
    AttemptStatus,
    GENERIC_MANIFEST_SCHEMA_VERSION,
    TestCase,
)


GENERIC_ATTEMPT_FIELDS = (
    "schema_version",
    "attempt_id",
    "suite_name",
    "case_id",
    "parameters",
    "stimulus_result",
    "analysis_results",
    "verdict",
    "artifacts",
    "started_at",
    "finished_at",
)


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

    def legacy_view(self) -> dict[str, Any]:
        """Return the plugin/legacy manifest shape without normalization."""
        return self.load()

    def generic_view(self) -> dict[str, Any]:
        """Return a framework-level manifest view.

        Older rows are normalized in-memory; this method does not mutate
        the persisted manifest.
        """
        return generic_manifest_view(self.load())


class LegacyManifest(Manifest):
    """Delegates to `run_one.load_manifest` / `save_manifest`.

    This keeps the wind-matrix campaign-log schema compatible while
    Phase 2 adds framework fields additively to rows written through
    the test_suite path. Legacy fields are not renamed or overwritten.

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
        with campaign_manifest_lock(self._root):
            manifest = self.load()
            attempts = manifest.setdefault("attempts", [])
            generic_fields = attempt_record_to_generic_fields(record)

            for attempt in attempts:
                if (
                    isinstance(attempt, dict)
                    and attempt.get("attempt_id") == record.attempt_id
                ):
                    additive_fields = dict(generic_fields)
                    additive_fields.pop("attempt_id", None)
                    attempt.update(additive_fields)
                    self.save(manifest)
                    save_summary = getattr(self._run_one, "save_campaign_summary", None)
                    if callable(save_summary):
                        save_summary(self._root, manifest)
                    return

            row = _to_jsonable(record.plugin_manifest_fields)
            if row:
                row.update(generic_fields)
            else:
                row = generic_fields
            attempts.append(row)
            self.save(manifest)
            save_summary = getattr(self._run_one, "save_campaign_summary", None)
            if callable(save_summary):
                save_summary(self._root, manifest)


def generic_manifest_view(manifest: dict[str, Any]) -> dict[str, Any]:
    """Return a normalized generic manifest without changing legacy data."""
    return {
        "schema_version": GENERIC_MANIFEST_SCHEMA_VERSION,
        "campaign_root": manifest.get("campaign_root"),
        "created_at_utc": manifest.get("created_at_utc"),
        "updated_at_utc": manifest.get("updated_at_utc"),
        "attempts": [
            generic_attempt_view(attempt)
            for attempt in manifest.get("attempts", [])
            if isinstance(attempt, dict)
        ],
    }


def generic_attempt_view(attempt: dict[str, Any]) -> dict[str, Any]:
    """Normalize a legacy or new manifest row into the generic contract."""
    return {
        "schema_version": (
            attempt.get("schema_version") or GENERIC_MANIFEST_SCHEMA_VERSION
        ),
        "attempt_id": attempt.get("attempt_id") or "",
        "suite_name": _suite_name(attempt),
        "case_id": _case_id(attempt),
        "parameters": _parameters(attempt),
        "stimulus_result": _stimulus_result(attempt),
        "analysis_results": _analysis_results(attempt),
        "verdict": _verdict(attempt),
        "artifacts": _artifacts(attempt),
        "started_at": attempt.get("started_at") or attempt.get("start_time_utc"),
        "finished_at": attempt.get("finished_at") or attempt.get("end_time_utc"),
    }


def attempt_record_to_generic_fields(record: AttemptRecord) -> dict[str, Any]:
    """Serialize a framework AttemptRecord into additive manifest fields."""
    return {
        "schema_version": GENERIC_MANIFEST_SCHEMA_VERSION,
        "attempt_id": record.attempt_id,
        "suite_name": record.suite_name,
        "case_id": record.case_id,
        "parameters": _to_jsonable(record.parameters),
        "stimulus_result": _to_jsonable(record.stimulus_result),
        "analysis_results": [
            _analysis_result_to_dict(result)
            for result in record.analysis_results
        ],
        "verdict": _record_verdict(record),
        "artifacts": _to_jsonable(record.artifacts),
        "started_at": record.start_time_utc or None,
        "finished_at": record.end_time_utc or None,
    }


def _analysis_result_to_dict(result: AnalysisResult) -> dict[str, Any]:
    return {
        "analyzer_name": result.analyzer_name,
        "ok": result.ok,
        "summary": _to_jsonable(result.summary),
        "output_paths": [str(path) for path in result.output_paths],
        "error": result.error,
    }


def _record_verdict(record: AttemptRecord) -> dict[str, Any]:
    if record.verdict is not None:
        return {
            "class": record.verdict.klass.value,
            "reason": record.verdict.reason,
            "retryable": record.verdict.retryable,
            "requires_analysis": record.verdict.requires_analysis,
            "metadata": _to_jsonable(record.verdict.metadata),
        }
    return {
        "class": _terminal_from_framework_status(record.status),
        "reason": record.status.value,
        "retryable": record.status
        in {
            AttemptStatus.FAILED,
            AttemptStatus.ERROR,
            AttemptStatus.INTERRUPTED,
            AttemptStatus.ANALYSIS_FAILED,
        },
        "requires_analysis": False,
        "metadata": {},
    }


def _suite_name(attempt: dict[str, Any]) -> str:
    suite_name = attempt.get("suite_name")
    if suite_name:
        return str(suite_name)
    if attempt.get("combo_key") or (
        "x_wind_mps" in attempt and "y_wind_mps" in attempt
    ):
        return "wind_matrix"
    return ""


def _case_id(attempt: dict[str, Any]) -> str:
    if attempt.get("case_id"):
        return str(attempt["case_id"])
    if attempt.get("combo_key"):
        return str(attempt["combo_key"])
    attempt_id = str(attempt.get("attempt_id") or "")
    return attempt_id.split("__", 1)[0] if attempt_id else ""


def _parameters(attempt: dict[str, Any]) -> dict[str, Any]:
    params = attempt.get("parameters")
    if isinstance(params, dict):
        return _to_jsonable(params)

    inferred: dict[str, Any] = {}
    if "x_wind_mps" in attempt:
        inferred["wind_x_mps"] = attempt.get("x_wind_mps")
    if "y_wind_mps" in attempt:
        inferred["wind_y_mps"] = attempt.get("y_wind_mps")
    return inferred


def _stimulus_result(attempt: dict[str, Any]) -> dict[str, Any]:
    stimulus = attempt.get("stimulus_result")
    if isinstance(stimulus, dict):
        return _to_jsonable(stimulus)

    if "x_wind_mps" in attempt or "y_wind_mps" in attempt:
        return {
            "kind": "wind_matrix",
            "wind_mps": {
                "x": attempt.get("x_wind_mps"),
                "y": attempt.get("y_wind_mps"),
                "z": 0.0,
            },
        }
    return {}


def _analysis_results(attempt: dict[str, Any]) -> list[dict[str, Any]]:
    results = attempt.get("analysis_results")
    if isinstance(results, list):
        return _to_jsonable(results)

    analysis_status = attempt.get("analysis_status")
    if analysis_status is None:
        return []
    return [
        {
            "analyzer_name": "legacy_run_analysis",
            "ok": legacy_analysis_succeeded(analysis_status),
            "summary": {"legacy_status": str(analysis_status)},
            "output_paths": [],
            "error": None,
        }
    ]


def _verdict(attempt: dict[str, Any]) -> dict[str, Any]:
    verdict = attempt.get("verdict")
    if isinstance(verdict, dict):
        return _to_jsonable(verdict)

    status = attempt.get("status")
    terminal = attempt.get("terminal_status") or terminal_status_for_legacy(status)
    if terminal is None and status is not None:
        terminal = str(status)
    return {
        "class": terminal,
        "reason": str(status or ""),
        "retryable": str(status or "") in {"failed", "error", "interrupted"},
        "requires_analysis": str(status or "")
        in {"success_full", "success_square_only", "failed_analysis"},
        "metadata": {
            key: _to_jsonable(attempt.get(key))
            for key in (
                "success_class",
                "mission_completed_full",
                "square_completed",
                "loiter_completed",
                "analysis_status",
            )
            if key in attempt
        },
    }


def _artifacts(attempt: dict[str, Any]) -> dict[str, Any]:
    artifacts = attempt.get("artifacts")
    if isinstance(artifacts, dict):
        return _to_jsonable(artifacts)

    inferred: dict[str, Any] = {}
    if attempt.get("raw_log_path") is not None:
        inferred["raw_log"] = attempt.get("raw_log_path")
    if attempt.get("attempt_dir") is not None:
        inferred["attempt_dir"] = attempt.get("attempt_dir")
    if attempt.get("run_alias") is not None:
        inferred["run_alias"] = attempt.get("run_alias")
    return inferred


def _terminal_from_framework_status(status: AttemptStatus) -> str:
    return {
        AttemptStatus.SUCCESS: "success",
        AttemptStatus.PARTIAL: "partial",
        AttemptStatus.FAILED: "failed",
        AttemptStatus.ERROR: "error",
        AttemptStatus.INTERRUPTED: "interrupted",
        AttemptStatus.ANALYSIS_FAILED: "failed_analysis",
        AttemptStatus.PENDING: "pending",
        AttemptStatus.RUNNING: "running",
    }[status]


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "__dataclass_fields__"):
        return _to_jsonable(asdict(value))
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    return value
