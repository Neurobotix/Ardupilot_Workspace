"""Content provenance for campaign inputs."""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
from typing import Iterable


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_provenance(path_like: Path | str) -> dict[str, str | int]:
    """Return content provenance for one file."""
    path = Path(path_like).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found for provenance: {path}")
    stat = path.stat()
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "size_bytes": stat.st_size,
    }


def relative_file_provenance(
    root: Path,
    relative_paths: Iterable[str],
) -> list[dict[str, str | int]]:
    """Hash workspace files while preserving repository-relative names."""
    resolved_root = root.expanduser().resolve()
    rows: list[dict[str, str | int]] = []
    for relative_name in relative_paths:
        row = file_provenance(resolved_root / relative_name)
        row["path"] = relative_name
        rows.append(row)
    return rows


def parameter_file_provenance(paths: Iterable[Path | str]) -> list[dict[str, str | int]]:
    """Return reviewable content provenance for the effective param stack."""
    rows: list[dict[str, str | int]] = []
    for path_like in paths:
        try:
            rows.append(file_provenance(path_like))
        except FileNotFoundError as exc:
            path = Path(path_like).expanduser().resolve()
            raise FileNotFoundError(
                f"Parameter file not found for provenance: {path}"
            ) from exc
    return rows


def source_tree_snapshot(workspace_root: Path | str) -> dict[str, object]:
    """Record the Git working-tree snapshot used by a live campaign run."""

    root = Path(workspace_root).expanduser().resolve()
    head = _git_output(root, ["git", "rev-parse", "HEAD"])
    status = _git_output(root, ["git", "status", "--short"], allow_failure=True)
    diff_stat = _git_output(root, ["git", "diff", "--stat"], allow_failure=True)
    diff_name_status = _git_output(
        root,
        ["git", "diff", "--name-status"],
        allow_failure=True,
    )
    untracked = _git_output(
        root,
        ["git", "ls-files", "--others", "--exclude-standard"],
        allow_failure=True,
    )
    diff = _git_output(root, ["git", "diff", "--binary"], allow_failure=True)
    untracked_files = untracked.splitlines()
    return {
        "git_head": head,
        "dirty": bool(status.strip()),
        "status_short": status.splitlines(),
        "diff_name_status": diff_name_status.splitlines(),
        "untracked_files": untracked_files,
        "untracked_file_provenance": relative_file_provenance(
            root,
            untracked_files,
        ),
        "diff_stat": diff_stat.splitlines(),
        "diff_sha256": (
            hashlib.sha256(diff.encode("utf-8")).hexdigest() if diff else None
        ),
        "note": (
            "Live smoke was run from this working tree snapshot, not "
            "necessarily a committed tree."
        ),
    }


def _git_output(
    workspace_root: Path,
    args: list[str],
    *,
    allow_failure: bool = False,
) -> str:
    result = subprocess.run(
        args,
        cwd=workspace_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 and not allow_failure:
        raise RuntimeError(
            f"{' '.join(args)} failed with {result.returncode}: "
            f"{result.stderr.strip()}"
        )
    return result.stdout.strip()
