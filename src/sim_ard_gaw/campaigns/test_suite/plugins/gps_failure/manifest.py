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

# The exact observation-quality classes the analyzer emits for an accepted
# observation. Acceptance requires the summary quality class to be one of these
# known-good values; an unknown quality class fails closed (it is not enough to
# merely not be a known-bad string).
_ACCEPTED_QUALITY_CLASSES = frozenset(
    {
        "valid_nominal",
        "valid_silent_drift",
        "valid_detected_rejection",
        "valid_reset_behavior",
        "valid_contained_behavior",
        "valid_bad_behavior",
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
        """Count accepted repetitions for scheduler/campaign target semantics."""
        count = 0
        for attempt in self.load().get("attempts", []):
            if not isinstance(attempt, dict):
                continue
            if attempt.get("case_id") != case.case_id:
                continue
            if accepted_repetition_from_attempt(attempt):
                count += 1
        return count

    def workflow_complete_count(self, case: TestCase) -> int:
        count = 0
        for attempt in self.load().get("attempts", []):
            if not isinstance(attempt, dict):
                continue
            if attempt.get("case_id") != case.case_id:
                continue
            if workflow_complete_from_attempt(attempt):
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
        # GPS has no legacy status vocabulary to preserve. Persist the framework
        # terminal state explicitly so error/interrupt rows are self-describing.
        row["status"] = record.status.value
        row["attempt_index"] = record.attempt_index
        row["target_run_index"] = record.target_run_index
        _fill_three_verdict_fields(row)
        manifest.setdefault("attempts", []).append(row)
        self.save(manifest)

    def generic_view(self) -> dict[str, Any]:
        return generic_manifest_view(self.load())


def accepted_observation_from_attempt(attempt: dict[str, Any]) -> bool:
    """Return whether the attempt is a useful behavior observation.

    Observation acceptance means workflow completed and the behavior evidence is
    explicit enough to characterize. It does not mean the requested physical GPS
    stimulus was realized; bad-dose runs may still be observations but are never
    accepted repetitions.
    """
    if not workflow_complete_from_attempt(attempt):
        return False
    if (
        "behavior_status" in attempt
        and str(attempt.get("behavior_status") or "").lower() != "accepted"
    ):
        return False
    return _behavior_accepted_from_attempt(attempt)


def accepted_repetition_from_attempt(attempt: dict[str, Any]) -> bool:
    """Return whether the attempt counts as a valid requested-recipe repetition."""
    if (
        "accepted_repetition" in attempt
        and attempt.get("accepted_repetition") is not True
    ):
        return False
    verdict = attempt.get("verdict")
    if isinstance(verdict, dict):
        metadata = verdict.get("metadata")
        if (
            isinstance(metadata, dict)
            and "accepted_repetition" in metadata
            and metadata.get("accepted_repetition") is not True
        ):
            return False
    if not accepted_observation_from_attempt(attempt):
        return False
    return _stimulus_fidelity_passes_from_attempt(attempt)


def workflow_complete_from_attempt(attempt: dict[str, Any]) -> bool:
    """Return whether the physical run workflow completed.

    This is deliberately separate from behavior and stimulus logic. It answers
    whether the executor completed a clean, reviewable flight package.
    """
    if str(attempt.get("workflow_status") or "").lower() != "complete":
        return False
    if not _top_level_status_valid_if_present(attempt):
        return False
    return _workflow_completion_evidence_present(attempt)


def _fill_three_verdict_fields(row: dict[str, Any]) -> None:
    if "workflow_status" not in row:
        row["workflow_status"] = (
            "complete" if _workflow_completion_evidence_present(row) else "incomplete"
        )
    if "behavior_status" not in row:
        row["behavior_status"] = (
            "accepted" if _behavior_accepted_from_attempt(row) else "incomplete"
        )
    if "accepted_observation" not in row:
        row["accepted_observation"] = accepted_observation_from_attempt(row)
    if "accepted_repetition" not in row:
        row["accepted_repetition"] = accepted_repetition_from_attempt(row)


def _behavior_accepted_from_attempt(attempt: dict[str, Any]) -> bool:
    """Authoritative GPS behavior-observation acceptance rule.

    Adverse but measurement-valid behaviors (``loss_of_control``,
    ``autopilot_contained``, ...) can still be accepted behavior observations.
    Every acceptance-bearing signal must *agree*; contradictions between the
    verdict, analysis summary, and top-level fields fail closed.
    """
    if not _top_level_status_valid_if_present(attempt):
        return False
    # A top-level accepted_observation, when present, must be a strict boolean.
    # A truthy non-bool (the string "true", the int 1, ...) is malformed and
    # fails closed rather than being read as acceptance.
    if "accepted_observation" in attempt and attempt.get("accepted_observation") is not True:
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

    top_level_behavior = attempt.get("behavior_class")
    if top_level_behavior is not None and top_level_behavior not in _ACCEPTABLE_BEHAVIOR_CLASSES:
        return False
    top_level_quality = attempt.get("observation_quality_class")
    if top_level_quality is not None and top_level_quality not in _ACCEPTED_QUALITY_CLASSES:
        return False
    if _top_level_terminal_context_contradicts_analysis(attempt):
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
        if summary.get("terminal_state_reached") is not True:
            return False
        if attempt.get("case_id") == "nominal" and summary.get(
            "mission_complete"
        ) is not True:
            return False
        if _bad_analysis_summary(summary):
            return False
        if summary.get("accepted_observation") is not True:
            return False
        behavior = summary.get("behavior_class")
        if not isinstance(behavior, str) or behavior not in _ACCEPTABLE_BEHAVIOR_CLASSES:
            return False
        # When an observation-quality class is present it must strictly be one of
        # the known-good accepted classes; an unknown quality fails closed.
        quality = summary.get("observation_quality_class")
        if quality is not None and quality not in _ACCEPTED_QUALITY_CLASSES:
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
    if top_level_behavior is not None and top_level_behavior != authoritative_behavior:
        return False

    return True


def _stimulus_fidelity_passes_from_attempt(attempt: dict[str, Any]) -> bool:
    statuses: list[str] = []
    top_level = attempt.get("stimulus_fidelity_status")
    if top_level is not None:
        if not isinstance(top_level, str):
            return False
        statuses.append(top_level.lower())

    verdict = attempt.get("verdict")
    metadata = verdict.get("metadata") if isinstance(verdict, dict) else None
    if isinstance(metadata, dict) and "stimulus_fidelity_status" in metadata:
        metadata_status = metadata.get("stimulus_fidelity_status")
        if not isinstance(metadata_status, str):
            return False
        statuses.append(metadata_status.lower())

    results = attempt.get("analysis_results")
    if not isinstance(results, list) or not results:
        return False
    for result in results:
        if not isinstance(result, dict):
            return False
        summary = result.get("summary")
        if not isinstance(summary, dict):
            return False
        if "stimulus_fidelity_status" not in summary:
            return False
        summary_status = summary.get("stimulus_fidelity_status")
        if not isinstance(summary_status, str):
            return False
        statuses.append(summary_status.lower())

    return bool(statuses) and all(status == "pass" for status in statuses)


def _top_level_terminal_context_contradicts_analysis(attempt: dict[str, Any]) -> bool:
    results = attempt.get("analysis_results")
    if not isinstance(results, list):
        return True
    comparable_fields = (
        "terminal_state_reached",
        "mission_complete",
        "stop_reason",
        "max_seq_reached",
        "auto_to_rtl_transition_seq",
    )
    for field in comparable_fields:
        if field not in attempt:
            continue
        top_value = attempt.get(field)
        for result in results:
            if not isinstance(result, dict):
                return True
            summary = result.get("summary")
            if not isinstance(summary, dict):
                return True
            if field in summary and summary.get(field) != top_value:
                return True
    return False


def _workflow_completion_evidence_present(attempt: dict[str, Any]) -> bool:
    cleanup = attempt.get("cleanup")
    if not isinstance(cleanup, dict) or cleanup.get("ok") is not True:
        return False
    artifacts = attempt.get("artifacts")
    if not isinstance(artifacts, dict):
        return False
    raw_log = artifacts.get("raw_log") or attempt.get("raw_log_path")
    if not isinstance(raw_log, str) or not raw_log:
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
