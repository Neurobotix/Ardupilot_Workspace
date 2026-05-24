# Phase 5 Live Round-Robin Parity Remediation

This curated bundle captures the bounded 2026-05-21 Phase 5 remediation run
used to compare a new-workspace `test_suite.cli.run_round_robin` attempt with
the Phase 1 production-reference one-case round-robin result.

Scope:

- one `wind_x_04_y_04` case;
- one target run and one pass;
- production-reference round-robin settings reused for the slot-derived
  timeout and optional local parameter overlay;
- raw simulator logs, BIN, tlog, SDF, and metric plots stay under `var/`.

Comparison anchors:

- production-reference manifest promoted earlier to
  `evidence/curated_logs/phase1_live_rr_parity_test/manifest.json`;
- read-only production-reference run config inspected at
  `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/phase1_live_rr_parity_test/wind_x_04_y_04/runs/attempt_001/run_config.json`;
- new-workspace proof files in this directory.

Observed parity facts:

- both manifests contain one accepted `wind_x_04_y_04` attempt with legacy
  status `success_full`, analysis status `done`, and full mission completion;
- both run configs use the 1862-second slot-derived mission timeout;
- the Phase 5 manifest adds canonical terminal status `success`;
- the Phase 5 run config records SHA-256 provenance for the actual parameter
  stack, including the read-only production local overlay used for comparison;
- the Phase 5 wind injection record shows strict echo verification enabled.
