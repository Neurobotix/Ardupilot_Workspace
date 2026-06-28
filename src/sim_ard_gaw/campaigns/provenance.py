"""Content provenance for campaign inputs."""
from __future__ import annotations

import hashlib
from pathlib import Path
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
