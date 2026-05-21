# sim_ard_gaw Runtime

Phase 8 retired the old root bridge from runtime path resolution and then moved
runtime implementation ownership into the organized homes:

- `launch/` owns launch and cleanup shell entrypoints.
- `bridges/` owns bridge and wind-publisher scripts.
- `analysis/` owns analysis, logging, and probe helpers.
- `campaigns/wind_matrix/` owns the wind-matrix runners.
- `campaigns/test_suite/` owns the campaign test-suite package.

`compat_scripts/` remains only as a thin compatibility-wrapper layer for old
imports and script paths. Do not add new runnable implementation logic there.
