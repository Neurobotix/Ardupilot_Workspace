"""sensor_failure manifest adapter (plugin-owned, sensor-agnostic).

A thin concrete Manifest. It deliberately does NOT reuse WindMatrixManifest's
wind-specific bits (combo keys, square/loiter acceptance, wind summary). It uses
the campaign manifest lock and the core generic-field serializer, and counts an
attempt as "accepted" when its plugin row recorded `passed == True`. Acceptance
is therefore resilience-based, mirroring the verdict policy.

No legacy runner import. No framework-core edit. Atomic writes via temp-file
rename, mirroring the wind manifest's durability.
"""
from __future__ import annotations

import csv
import io
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sim_ard_gaw.campaigns.manifest_safety import campaign_manifest_lock

from ...core.manifest import (
    Manifest,
    _to_jsonable,
    attempt_record_to_generic_fields,
)
from ...core.models import (
    GENERIC_MANIFEST_SCHEMA_VERSION,
    AttemptRecord,
    AttemptStatus,
    TestCase,
)
from . import defaults


_STALE_RUNNING_NOTE = "bookkeeping_recovered_stale_running_record"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _coerce_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _behavior_counts(attempts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for a in attempts:
        b = a.get("behavior")
        if b:
            counts[str(b)] = counts.get(str(b), 0) + 1
    return counts


def _write_text(path: Path, text: str, *, newline: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", newline=newline, dir=path.parent,
            prefix=f".{path.name}.", delete=False,
        ) as handle:
            tmp_path = Path(handle.name)
            handle.write(text)
        tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def _write_json(path: Path, data: Any) -> None:
    _write_text(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


_CSV_FIELDS = [
    "attempt_id", "case_id", "sensor", "fault_mode", "verdict_mode",
    "target_run_index", "attempt_index", "status", "behavior", "accepted",
    "fault_injected", "recovery_mode", "mode_changed_after_inject",
    "pre_inject_max_roll_deg", "post_inject_max_roll_deg", "delta_max_roll_deg",
    "post_inject_max_excursion_m", "post_inject_min_relalt_m",
    "post_inject_max_relalt_m", "min_relalt_drop_m", "raw_log_path",
    "attempt_dir", "run_alias", "start_time_utc", "end_time_utc",
    "duration_wall_s", "notes",
]


class SensorFailureManifest(Manifest):
    def __init__(self, campaign_root: Path) -> None:
        self._root = campaign_root

    def _path(self) -> Path:
        return self._root / "manifest.json"

    def _default(self) -> dict[str, Any]:
        return {
            "campaign_root": str(self._root),
            "suite_name": "sensor_failure",
            "created_at_utc": _utc_now(),
            "updated_at_utc": _utc_now(),
            "attempts": [],
        }

    def load(self) -> dict[str, Any]:
        path = self._path()
        if not path.exists():
            return self._default()
        return json.loads(path.read_text(encoding="utf-8"))

    def save(self, manifest: dict[str, Any]) -> None:
        manifest["updated_at_utc"] = _utc_now()
        _write_text(
            self._path(),
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        )
        self._write_csv(manifest)
        self._write_summary(manifest)

    def _write_csv(self, manifest: dict[str, Any]) -> None:
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for attempt in manifest.get("attempts", []):
            if not isinstance(attempt, dict):
                continue
            row = {field: attempt.get(field) for field in _CSV_FIELDS}
            notes = row.get("notes")
            if isinstance(notes, list):
                row["notes"] = " | ".join(str(n) for n in notes)
            writer.writerow(row)
        _write_text(self._root / "manifest.csv", buffer.getvalue(), newline="")

    def _write_summary(self, manifest: dict[str, Any]) -> None:
        attempts = [a for a in manifest.get("attempts", []) if isinstance(a, dict)]
        target_runs = _coerce_int(manifest.get("target_run_count")) or defaults.DEFAULT_REPEATS
        case_ids: list[str] = []
        for a in attempts:
            cid = a.get("case_id")
            if cid and cid not in case_ids:
                case_ids.append(str(cid))
        cases_summary = []
        for cid in case_ids:
            case_attempts = [a for a in attempts if a.get("case_id") == cid]
            accepted = [a for a in case_attempts if bool(a.get("accepted"))]
            pending = [a for a in case_attempts if str(a.get("status")) == "running"]
            last = case_attempts[-1] if case_attempts else {}
            cases_summary.append({
                "case_id": cid,
                "accepted_runs": len(accepted),
                "remaining_runs": max(0, target_runs - len(accepted)),
                "attempt_count": len(case_attempts),
                "pending_attempt_count": len(pending),
                "last_status": last.get("status"),
                "last_behavior": last.get("behavior"),
                "last_attempt_id": last.get("attempt_id"),
                "behaviors": _behavior_counts(case_attempts),
            })
        summary = {
            "campaign_root": str(self._root),
            "suite_name": "sensor_failure",
            "updated_at_utc": _utc_now(),
            "target_run_count": target_runs,
            "accepted_total": sum(c["accepted_runs"] for c in cases_summary),
            "remaining_total": sum(c["remaining_runs"] for c in cases_summary),
            "cases": cases_summary,
        }
        summary_dir = self._root / "summary"
        summary_dir.mkdir(parents=True, exist_ok=True)
        _write_json(summary_dir / "campaign_summary.json", summary)

    def accepted_count(self, case: TestCase) -> int:
        manifest = self._reconciled()
        return sum(
            1 for a in manifest.get("attempts", [])
            if isinstance(a, dict)
            and a.get("case_id") == case.case_id
            and bool(a.get("accepted"))
        )

    def next_attempt_index(self, case: TestCase) -> int:
        manifest = self._reconciled()
        indices: set[int] = set()
        for a in manifest.get("attempts", []):
            if not isinstance(a, dict) or a.get("case_id") != case.case_id:
                continue
            idx = _coerce_int(a.get("attempt_index"))
            if idx is not None and idx >= 1:
                indices.add(idx)
        runs_dir = defaults.case_runs_dir(self._root, case.case_id)
        if runs_dir.exists():
            for child in runs_dir.iterdir():
                if child.name.startswith("attempt_"):
                    idx = _coerce_int(child.name[len("attempt_"):])
                    if idx is not None and idx >= 1:
                        indices.add(idx)
        next_idx = max(indices, default=0) + 1
        while (runs_dir / defaults.attempt_key(next_idx)).exists():
            next_idx += 1
        return next_idx

    def append_attempt(self, record: AttemptRecord) -> None:
        with campaign_manifest_lock(self._root):
            manifest = self.load()
            attempts = manifest.setdefault("attempts", [])
            generic_fields = attempt_record_to_generic_fields(record)
            plugin_fields = _to_jsonable(record.plugin_manifest_fields)
            row = dict(plugin_fields) if isinstance(plugin_fields, dict) else {}
            if row:
                row.update(generic_fields)
            else:
                row = dict(generic_fields)

            for attempt in attempts:
                if (
                    isinstance(attempt, dict)
                    and attempt.get("attempt_id") == record.attempt_id
                ):
                    if (
                        record.status == AttemptStatus.RUNNING
                        and str(attempt.get("status") or "") not in {"", "running"}
                    ):
                        return
                    fields = (
                        row if str(attempt.get("status") or "") == "running"
                        else generic_fields
                    )
                    additive = dict(fields)
                    additive.pop("attempt_id", None)
                    attempt.update(additive)
                    self.save(manifest)
                    return

            attempts.append(row)
            self.save(manifest)

    def _reconciled(self) -> dict[str, Any]:
        """Recover stale `running` rows as `interrupted` before counting."""
        with campaign_manifest_lock(self._root):
            manifest = self.load()
            changed = False
            for record in manifest.get("attempts", []):
                if not isinstance(record, dict):
                    continue
                if str(record.get("status", "")).strip() == "running":
                    record["status"] = "interrupted"
                    record["accepted"] = False
                    record["behavior"] = "not_characterized"
                    notes = record.setdefault("notes", [])
                    if isinstance(notes, list) and _STALE_RUNNING_NOTE not in notes:
                        notes.append(_STALE_RUNNING_NOTE)
                    changed = True
            if changed:
                self.save(manifest)
            return manifest

    def generic_view(self) -> dict[str, Any]:
        manifest = self.load()
        return {
            "schema_version": GENERIC_MANIFEST_SCHEMA_VERSION,
            "campaign_root": manifest.get("campaign_root"),
            "created_at_utc": manifest.get("created_at_utc"),
            "updated_at_utc": manifest.get("updated_at_utc"),
            "attempts": [
                {
                    "schema_version": (
                        a.get("schema_version") or GENERIC_MANIFEST_SCHEMA_VERSION
                    ),
                    "attempt_id": a.get("attempt_id") or "",
                    "suite_name": a.get("suite_name") or "sensor_failure",
                    "case_id": a.get("case_id") or "",
                    "parameters": _to_jsonable(a.get("parameters") or {}),
                    "stimulus_result": _to_jsonable(a.get("stimulus_result") or {}),
                    "analysis_results": _to_jsonable(a.get("analysis_results") or []),
                    "verdict": _to_jsonable(a.get("verdict") or {}),
                    "artifacts": _to_jsonable(a.get("artifacts") or {}),
                    "started_at": a.get("started_at") or a.get("start_time_utc"),
                    "finished_at": a.get("finished_at") or a.get("end_time_utc"),
                }
                for a in manifest.get("attempts", [])
                if isinstance(a, dict)
            ],
        }
