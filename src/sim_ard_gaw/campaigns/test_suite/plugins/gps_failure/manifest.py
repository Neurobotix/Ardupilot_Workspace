"""Manifest adapter for the gps_failure plugin."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ...core.manifest import Manifest, attempt_record_to_generic_fields, generic_manifest_view
from ...core.models import AttemptRecord, TestCase
from . import defaults


_BAD_REASONS = {
    "analysis_incomplete",
    "failed_analysis",
    "failed_launch",
    "failed_readback",
    "missing_required_artifacts",
    "pre_injection",
    "pre_injection_failure",
}

# Behavior classes that can be an *accepted* observation. Adverse but
# measurement-valid behaviors count as accepted; analysis/discard states never
# do. Anything outside this set is an unknown class and fails closed.
_ACCEPTABLE_BEHAVIOR_CLASSES = frozenset(
    {
        "nominal",
        "silent_drift",
        "detected_rejected",
        "reset_captured",
        "autopilot_contained",
        "loss_of_control",
    }
)


class GpsFailureManifest(Manifest):
    def __init__(self, campaign_root: Path) -> None:
        self._root = campaign_root

    def load(self) -> dict[str, Any]:
        path = self._root / "manifest.json"
        if not path.exists():
            return {
                "campaign_root": str(self._root),
                "created_at_utc": defaults.utc_now(),
                "updated_at_utc": defaults.utc_now(),
                "attempts": [],
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, manifest: dict[str, Any]) -> None:
        manifest["updated_at_utc"] = defaults.utc_now()
        self._root.mkdir(parents=True, exist_ok=True)
        defaults.write_json(self._root / "manifest.json", manifest)

    def accepted_count(self, case: TestCase) -> int:
        count = 0
        for attempt in self.load().get("attempts", []):
            if not isinstance(attempt, dict):
                continue
            if attempt.get("case_id") != case.case_id:
                continue
            if accepted_observation_from_attempt(attempt):
                count += 1
        return count

    def next_attempt_index(self, case: TestCase) -> int:
        highest = 0
        for attempt in self.load().get("attempts", []):
            if isinstance(attempt, dict) and attempt.get("case_id") == case.case_id:
                try:
                    highest = max(highest, int(attempt.get("attempt_index") or 0))
                except (TypeError, ValueError):
                    continue
        return highest + 1

    def append_attempt(self, record: AttemptRecord) -> None:
        manifest = self.load()
        row = attempt_record_to_generic_fields(record)
        row.update(record.plugin_manifest_fields)
        row["attempt_index"] = record.attempt_index
        row["target_run_index"] = record.target_run_index
        manifest.setdefault("attempts", []).append(row)
        self.save(manifest)

    def generic_view(self) -> dict[str, Any]:
        return generic_manifest_view(self.load())


def accepted_observation_from_attempt(attempt: dict[str, Any]) -> bool:
    """Authoritative Phase-1 GPS observation acceptance rule.

    Accepted means the measurement was valid enough to characterize behavior. It
    does not mean the aircraft behaved nominally: adverse but measurement-valid
    behaviors (``loss_of_control``, ``autopilot_contained``, ...) can still be
    accepted. Every acceptance-bearing signal must *agree*; a contradiction
    between the verdict's behavior and the authoritative analysis behavior, an
    analysis-incomplete state, a pre-injection failure, conflicting top-level or
    verdict metadata, multiple incompatible behavior classes, or an unknown
    behavior class all fail closed.
    """
    if not _top_level_status_valid_if_present(attempt):
        return False
    if attempt.get("accepted_observation") is False:
        return False

    verdict = attempt.get("verdict")
    if not isinstance(verdict, dict):
        return False
    if not _valid_success_verdict(verdict):
        return False
    metadata = verdict.get("metadata")
    # The verdict must carry explicit accepted-observation metadata set to True.
    if not isinstance(metadata, dict) or metadata.get("accepted_observation") is not True:
        return False

    results = attempt.get("analysis_results")
    if not isinstance(results, list) or not results:
        return False

    # Every required GPS analysis result must be ok=True, explicitly accepted,
    # and agree on a single authoritative behavior class.
    analysis_behavior_classes: set[str] = set()
    for result in results:
        if not isinstance(result, dict):
            return False
        if result.get("ok") is not True:
            return False
        summary = result.get("summary")
        if not isinstance(summary, dict):
            return False
        if _bad_analysis_summary(summary):
            return False
        if summary.get("accepted_observation") is not True:
            return False
        behavior = summary.get("behavior_class")
        if not isinstance(behavior, str) or behavior not in _ACCEPTABLE_BEHAVIOR_CLASSES:
            return False
        analysis_behavior_classes.add(behavior)

    # Multiple incompatible behavior classes across analysis results fail closed.
    if len(analysis_behavior_classes) != 1:
        return False
    authoritative_behavior = next(iter(analysis_behavior_classes))

    # The verdict's behavior (its reason) must agree with the authoritative
    # analysis behavior class.
    verdict_behavior = verdict.get("reason")
    if not isinstance(verdict_behavior, str):
        return False
    if verdict_behavior not in _ACCEPTABLE_BEHAVIOR_CLASSES:
        return False
    if verdict_behavior != authoritative_behavior:
        return False

    return True


def _top_level_status_valid_if_present(attempt: dict[str, Any]) -> bool:
    for key in ("status", "terminal_status"):
        value = attempt.get(key)
        if value is not None and str(value).lower() != "success":
            return False
    return True


def _valid_success_verdict(verdict: dict[str, Any]) -> bool:
    klass = verdict.get("class") or verdict.get("klass")
    reason = verdict.get("reason")
    if klass is None or str(klass).lower() != "success":
        return False
    if reason is not None and str(reason).lower() in _BAD_REASONS:
        return False
    return True


def _bad_analysis_summary(summary: dict[str, Any]) -> bool:
    if summary.get("accepted_observation") is False:
        return True
    behavior = summary.get("behavior_class")
    quality = summary.get("observation_quality_class")
    reason = summary.get("reason")
    if behavior is not None and str(behavior).lower() in {
        "analysis_incomplete",
        "pre_injection_failure",
    }:
        return True
    for value in (quality, reason):
        if value is not None and str(value).lower() in _BAD_REASONS:
            return True
    return False
