# CTE Wind-Envelope Result Pillar

Date/time: 2026-06-02T20:21:24+03:00

Timezone: Africa/Cairo / EEST (+03:00)

Evidence kind: feature analysis and curated evidence package

Conclusion: PASS for the production-like CTE wind-envelope result package. The
corrected 020 analysis of campaign `017_params_old_009_matrix_r3_plugin_fixed`
supports a deck-ready result: square tracking error rises with the wind vector,
the high-wind no-accepted cells are a cruise-airspeed-limited envelope edge, and
the claim is bounded by accepted/rejected separation, SIM-only metric rules, and
internal EKF wind-audit provenance.

## Scope

This report closes the CTE wind-envelope result pillar for the platform
briefing. It replaces the thin presentation brief with a deeper scientific
analysis package and curates the proof into this workspace.

In scope:

- Read-only analysis of the old-workspace 017/020 source material.
- Derived metrics, richer statistics, regenerated deck-ready figures, and
  written conclusions.
- Curated package under
  `evidence/curated_logs/cte_wind_envelope_017_20260602/`.
- Updated platform briefing brief:
  `docs/presentations/platform_briefing/cte_result_brief.md`.

Out of scope:

- Live SITL/Gazebo runs.
- New flights.
- Raw BIN reprocessing.
- Any use of campaign `018_New_Param_Full_CTE_Matrix` as the production-like
  tracking headline.

## Inputs And Provenance

Primary source dataset:

```text
/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/017_params_old_009_matrix_r3_plugin_fixed
```

Primary numeric source:

```text
/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/020_Old_Param_Fixed_CTE_Report/summary/corrected
```

The 020 metadata records:

- generated UTC: `2026-05-14T11:50:52+00:00`
- manifest mode: `raw`
- analysis source: `sim`
- dataset rows: 32 accepted run rows, 13 accepted combo rows, 3 failure-no-
  accepted combos, 4 partial-failure combos
- script SHA256 chain:
  - `build_square_postprocessing_report.py`:
    `dbd25c06af2d4140f595e2a82740fec573172efcc8daa6c8dcf848ad6ad24559`
  - `true_path_deviation.py`:
    `6b2d5df289209e32673609f110725f8058f4b95be09f6fbba040dc2a6547e762`
  - `square_loiter_mission_metrics.py`:
    `69783668c0ec8c6130432e48245f0306dc4607951f82d7fd0831072bfe06df48`

The 017 failure analysis records the internal EKF wind audit as 38 accepted
named BIN files and 0 rejected named BIN files. The no-accepted cells are
therefore treated as valid wind-envelope outcomes, not harness data gaps.

## Method

The derived package uses the corrected 020 tables as the numeric foundation:

- `corrected_combo_summary.csv`
- `corrected_accepted_runs_summary_sim.csv`
- `corrected_campaign_outcome_summary.csv`
- `corrected_failure_envelope_attempts.csv`
- `scientific_summary.json`
- `metadata.json`

The generation script lives outside evidence as a development helper:

```text
scripts/dev/generate_cte_wind_envelope_package.py
```

It computes ordinary least-squares models with `numpy.linalg.lstsq`, derives
adjacent-cell monotonicity, repeatability summaries, no-accepted cell envelope
ratios, and refreshed plots. It does not read or decode raw BIN files.

Glossary constraints followed:

- SIM position is the primary analysis source.
- Square conclusions use mission seq 3..22.
- Loiter is reported separately with after-capture metrics.
- Landing is excluded from square-performance claims.
- No-accepted cells are campaign outcomes; no interpolated CTE values are
  assigned to them.
- Mission edge/heading effects are not described as pure aerodynamic heading
  effects.
- Square p95 is the management-facing tail metric; max is retained as a backup
  stress indicator.

## Headline Result

The production-like stack completes low and moderate wind cells with quantified
tracking degradation, then reaches a high-wind envelope edge where the mission
does not produce accepted square/loiter evidence.

| Metric | Value |
| --- | ---: |
| Accepted runs | 32 |
| Accepted wind cells | 13 / 16 |
| No-accepted high-wind cells | 3 / 16 |
| Partial-failure-with-accepted cells | 4 / 16 |
| Calm square RMS true-path deviation | 7.15 m |
| Worst accepted square RMS true-path deviation | 17.99 m at `wind_x_12_y_04` |
| Worst accepted square p95 true-path deviation | 45.13 m at `wind_x_12_y_04` |
| Worst accepted RMS vs calm | 2.52x |
| Square vs loiter-after-capture Pearson r | 0.829 |

The accepted-cell wind model shows that the wind vector explains most, but not
all, combo-level RMS degradation:

| Model | R2 | Residual RMSE |
| --- | ---: | ---: |
| Wind magnitude only | 0.673 | 1.84 m |
| East/North components | 0.733 | 1.67 m |
| East/North components + interaction | 0.751 | 1.61 m |

Accepted-adjacent RMS steps are nondecreasing in 16 of 18 comparable pairs.
Square p95 is less monotonic, 12 of 18 comparable pairs, which is consistent
with tail sensitivity and mission edge/heading confounding.

## Envelope Edge

The no-accepted cells are:

| Cell | Resultant wind | Wind / 14 m/s cruise | Accepted runs | Physical interpretation |
| --- | ---: | ---: | ---: | --- |
| `wind_x_12_y_08` | 14.42 m/s | 1.03 | 0 | Cruise-speed-limited mission progress; no completed square/loiter accepted run. |
| `wind_x_08_y_12` | 14.42 m/s | 1.03 | 0 | Cruise-speed-limited mission progress; no completed square/loiter accepted run. |
| `wind_x_12_y_12` | 16.97 m/s | 1.21 | 0 | High-corner groundspeed collapse; mission stalls at `Mission: 2 WP`. |

The 017 failure analysis gives the clearest mechanism at `wind_x_12_y_12`:
resultant wind is 16.97 m/s, commanded cruise is 14 m/s, median airspeed is
about 14 m/s, median groundspeed is about 2.8 m/s, and the monitor times out
after about 4537 s while the mission is still at waypoint 2. This is the
production-like operating envelope showing itself under valid wind injection.

## Repeatability

Accepted-run replicate spread is small for most cells:

- Median within-combo square RMS replicate standard deviation: 0.04 m.
- Mean within-combo square RMS replicate standard deviation: 0.33 m.
- Largest within-combo square RMS replicate standard deviation: 2.58 m at
  `wind_x_08_y_08`.
- Median lap RMS standard deviation across combo means: 1.26 m.
- Median lap RMS slope: -0.65 m/lap.

The high-spread cells are near the envelope edge or have fewer accepted
replicates, so they are treated as evidence of edge-adjacent instability rather
than as a reason to interpolate missing high-wind cells.

## Curated Package

Promoted package:

```text
evidence/curated_logs/cte_wind_envelope_017_20260602/
```

Key files:

- `README.md`
- `cte_metrics.json`
- `tables/cte_tables.md`
- `tables/corrected_combo_summary.csv`
- `tables/corrected_accepted_runs_summary_sim.csv`
- `tables/corrected_campaign_outcome_summary.csv`
- `tables/corrected_failure_envelope_attempts.csv`
- `written_conclusion_exec.md`
- `written_conclusion_technical.md`

Plot inventory:

- `plots/campaign_outcome_envelope_heatmap.png` and `.svg`
- `plots/square_rms_heatmap.png` and `.svg`
- `plots/square_p95_heatmap.png` and `.svg`
- `plots/rms_vs_wind_component_model.png` and `.svg`
- `plots/replicate_variability_square_rms.png` and `.svg`
- `plots/loiter_vs_square_after_capture.png` and `.svg`
- `plots/component_model_residuals.png` and `.svg`

Recommended hero visual:

```text
evidence/curated_logs/cte_wind_envelope_017_20260602/plots/campaign_outcome_envelope_heatmap.png
```

## 018 / 019 Correctness Note

Campaign `018_New_Param_Full_CTE_Matrix` and report `019_New_Param_Full_CTE_Report`
used a more aggressive expanded-authority parameter stack that was later
abandoned as unrealistic. Those results are not used as the production-like CTE
tracking headline. They may be mentioned only as an explicitly labeled
stress-test footnote.

## Commands Run

```text
cd /home/ahmed/ardupilot_workspace_next

sed -n '1,260p' \
  /home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/020_Old_Param_Fixed_CTE_Report/summary/corrected/metrics_glossary.md

sed -n '1,260p' \
  /home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/logs/017_params_old_009_matrix_r3_plugin_fixed/HIGH_WIND_OLD_PARAM_FAILURE_ANALYSIS.md

python3 scripts/dev/generate_cte_wind_envelope_package.py
```

Final validation is recorded below after `make doctor`.

```text
make doctor
```

## Risks And Limitations

- This is SITL + Gazebo simulation evidence, not hardware flight evidence.
- The headline applies only to the default / production-like parameter stack.
- 13 of 16 cells have accepted data; 3 high-wind cells are envelope outcomes
  and are not assigned interpolated CTE values.
- Mission edge and heading are confounded in the square route.
- The wind model is explanatory, not deterministic; component + interaction
  R2 is 0.751, leaving residual run/cell dynamics.
- The old workspace was read as reference/source material and was not modified.

## Governance And Docs

Updated:

- `docs/presentations/platform_briefing/cte_result_brief.md`
- `evidence/indexes/evidence_catalog.md`
- `.ai/index.md`

No ADR was created; this is an evidence/reporting package, not a durable policy
or architecture decision.

## Validation Results

| Check | Result |
| --- | --- |
| `cte_metrics.json` JSON validation | PASS |
| Visual inspection of hero outcome heatmap | PASS |
| Visual inspection of RMS-vs-wind model plot | PASS |
| `make doctor` | PASS |

## Migration Statements

- Old workspace modification statement: `/home/ahmed/ardupilot_workspace` was
  read only and was not modified.
- Cutover non-claim: this report does not change Phase 7/8 cutover or
  compatibility-retirement status.
- Runtime non-claim: no live SITL/Gazebo run was performed for this result
  package.
