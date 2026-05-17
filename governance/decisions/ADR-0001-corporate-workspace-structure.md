# ADR-0001: Corporate Workspace Structure

Status: Accepted

The new workspace uses explicit boundaries for code, assets, config, docs,
governance, evidence, runtime output, and private overlays. This prevents the
production failure mode where docs, logs, scripts, and local state drifted into
one operational knot.

Production remains read-only until shadow parity passes.
