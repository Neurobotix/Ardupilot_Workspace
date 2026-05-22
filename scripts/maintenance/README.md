# Maintenance Scripts

`validate_structure.sh` enforces the Phase 1 workspace boundary checks. It is
called by `scripts/ops/doctor.sh` and can be run directly when changing paths,
docs, ignore rules, or local overlay policy.

The validator uses broad stale-reference blocklists plus exact file/label/text
allowlist entries for known historical or compatibility exceptions. Allowed
exceptions are printed with a reason and matched text so evidence reports can
distinguish intentional bridge references from new drift.

`validate_evidence.sh` enforces the Phase 6 evidence boundary checks. It is also
called by `scripts/ops/doctor.sh` and can be run directly when changing
`evidence/`, runtime-output claims, templates, or the evidence catalog. It
checks raw `.BIN`/`.bin`/`.tlog` leakage, raw run directories outside runtime
homes, raw-looking evidence-home signatures, the report-home shape, approved
evidence top-level homes, phase-report placement, required template fields,
catalog markers, and curated-root catalog coverage. Reviewed bounded artifacts
that resemble raw runtime output need an exact allowlist reason in the
validator.

## Naming

Maintenance scripts use `lower_snake_case.sh` or `lower_snake_case.py`. New
validators should document their scope here or in `scripts/README.md`, and
policy-file checks should stay narrowly scoped so historical names do not fail
only because they predate the policy.
