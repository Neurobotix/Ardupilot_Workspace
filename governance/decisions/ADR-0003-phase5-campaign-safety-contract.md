# ADR-0003: Phase 5 Campaign Safety Contract

Status: Accepted

Phase 5 keeps the wind-matrix compatibility runners and Phase-1 `test_suite`
wrappers while moving reusable safety rules into `src/sim_ard_gaw/campaigns/`.

Campaign manifest writers take a campaign-root lock around unsafe attempt and
manifest transactions. Legacy manifest `status` values remain compatible; the
canonical terminal taxonomy is added as `terminal_status` with
`success`, `partial`, `failed`, `failed_analysis`, `error`, and `interrupted`.

Wind-matrix evidence validates the square mission contract before relying on
hardcoded analysis assumptions. The contract covers the analyzer-sensitive
waypoint commands, supported location frames, and 500 m square-side geometry,
not just sequence presence. Campaign code transforms static SDF world wind
through XML structure, defaults runtime wind topic echo verification to strict,
and records parameter-file content hashes with run provenance.
