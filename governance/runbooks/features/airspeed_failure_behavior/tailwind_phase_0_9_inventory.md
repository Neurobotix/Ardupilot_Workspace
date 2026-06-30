# Tailwind Phase 0–9 Raw-Evidence Inventory

Date: 2026-06-23 UTC

Scope: Chunk 2 provenance, artifact, schedule, readback, and coverage inventory

Behavior-analysis boundary: no new aerodynamic interpretation was performed.
The original manifest/mechanism verdicts below are reported as historical
metadata, not endorsed as corrected results.

Working machine-readable inventory:

`var/analysis/tailwind_phase_0_9_expectations_20260623/tailwind_run_inventory.json`

Inventory SHA-256:
`a6495811ca697116091085e0d6bc1babed2cef7ac84a68f481d3aed6b9699b48`.

## Configuration identities

All discovered tailwind attempts record `wind_profile.profile_id` as
`tailwind_eastbound`. The phase mapping used case ID, wind profile, mission,
mission hash, parameter overlay/hash, speed source, mechanism tier, and
expected `AHRS_WIND_MAX`; directory names were not used as the authority.

Mission identities:

| ID | Mission | SHA-256 |
| --- | --- | --- |
| M15 | `assets/missions/airspeed_failure_eastbound_long_speed_15_mission.waypoints` | `8c842dd4ffb25d22ef6cf987624ec9a905f86bbb798d49da13652cb28fff2a94` |
| MCR | `assets/missions/airspeed_failure_eastbound_long_cruise_follow_mission.waypoints` | `bea0bf2ea4a5da0f53ba2b53fb43c34b9e52b9ed4a873d4bc1e88a9330d87ce7` |

Parameter-stack identities (paths are loaded in the listed order):

| ID | Parameter stack with recorded SHA-256 |
| --- | --- |
| S0 | `config/vehicles/plane_base.parm` `8941fa559f762fb4111c150db04e4d36c0ad05d680f8cff2cd28219ba8ceaa01`; `config/overlays/plane_airspeed.parm` `154bf537b26c6018e55a8a0e8c0c0d2ca2103e7d91931c923db478f0622c6159` |
| S1 | `config/vehicles/plane_base.parm` `8941fa559f762fb4111c150db04e4d36c0ad05d680f8cff2cd28219ba8ceaa01`; `config/overlays/plane_airspeed_windmax0.parm` `1dcc31f0f81ff63ff624573dee6832c99cb2cc8d91bc25fede592a66253f5aec` |
| S2 | `config/vehicles/plane_base.parm` `8941fa559f762fb4111c150db04e4d36c0ad05d680f8cff2cd28219ba8ceaa01`; `config/overlays/plane_airspeed_max28.parm` `14f2f6e67ccddc3b670e9c566abb41ae339fb6347aabb11b67d9f75982c64c70` |
| S3 | `config/vehicles/plane_base.parm` `8941fa559f762fb4111c150db04e4d36c0ad05d680f8cff2cd28219ba8ceaa01`; `config/overlays/plane_airspeed_max18.parm` `73efb6b53950f3d8254fcc5a612e2606c08c1010051e1a89c67e4570680f2c9f` |
| S4 | `config/vehicles/plane_base.parm` `8941fa559f762fb4111c150db04e4d36c0ad05d680f8cff2cd28219ba8ceaa01`; `config/overlays/plane_airspeed_cruise17.parm` `92accd3260f6cd2d9ef1cce47346b91be4a7cdb7a317defa4b77357b38d1a2aa` |
| S5 | `config/vehicles/plane_base.parm` `8941fa559f762fb4111c150db04e4d36c0ad05d680f8cff2cd28219ba8ceaa01`; `config/overlays/plane_airspeed_scaled18_28.parm` `06735f39884f93ffb8362c4b260c3b167d11ff6cedb500eb6dce72cab9b52d3e` |

Expected phase configuration:

| Phase | Expected cell ID | Expected attempts | Case | Mission / stack | Speed source | Tier / expected `AHRS_WIND_MAX` |
| ---: | --- | ---: | --- | --- | --- | --- |
| 0 | `healthy_tailwind_speed15` | 1 | `healthy_reference_tailwind` | M15 / S0 | `do_change_speed_15` | protected / 15 (final gate attempt) |
| 1 | `protected_cruise_follow_p200` | 3 | `ratio_bias_ramp_p10_to_p200_tailwind` | MCR / S0 | `airspeed_cruise` | protected / 15 |
| 2 | `diagnostic_cruise_follow_p200` | 3 | `ratio_bias_ramp_p10_to_p200_tailwind` | MCR / S1 | `airspeed_cruise` | diagnostic / 0 |
| 3 | `max28_speed15_p200` | 3 | `ratio_bias_ramp_p10_to_p200_tailwind` | M15 / S2 | `do_change_speed_15` | protected / 15 |
| 4 | `max18_speed15_p200` | 3 | `ratio_bias_ramp_p10_to_p200_tailwind` | M15 / S3 | `do_change_speed_15` | protected / 15 |
| 5 | `cruise17_speed15_p200` | 1 | `ratio_bias_ramp_p10_to_p200_tailwind` | M15 / S4 | `do_change_speed_15` | protected / 15 |
| 6 | `scaled18_28_speed15_p200` | 1 | `ratio_bias_ramp_p10_to_p200_tailwind` | M15 / S5 | `do_change_speed_15` | protected / 15 |
| 7 | `standard_speed15_p200` | 1 | `ratio_bias_ramp_p10_to_p200_tailwind` | M15 / S0 | `do_change_speed_15` | protected / 15 |
| 8 | `standard_speed15_p100` | 1 | `ratio_bias_ramp_p10_to_p100_tailwind` | M15 / S0 | `do_change_speed_15` | protected / 15 |
| 9 | `standard_speed15_pulse_p130` | 1 | `ratio_bias_pulse_p10_to_p130_tailwind` | M15 / S0 | `do_change_speed_15` | protected / 15 |

## Full attempt inventory

Artifact count is 9/9 for healthy attempts and 11/11 for scheduled attempts.
The common nine are `run_config.json`, `reference_wind.json`,
`airspeed_injection.json`, `airspeed_behavior_summary.json`,
`airspeed_signal_metrics.json`, `altitude_speed_envelope.json`,
`mission_progress.json`, `mode_timeline.json`, and
`vehicle_airspeed_params.json`. Scheduled attempts additionally require
`airspeed_mechanism_gate.json` and the applicable ramp or pulse artifact.
Every row also has the matching BIN shown separately.

`Manifest` is `accepted / behavior_class / observation_quality_class`.
`Schedule` is `complete? applied/expected stop_reason`. `RB/reset` reports all
applied-event readbacks and final reset readback. Each classification is exactly
one of the requested inventory classes.

| Phase | Root | Attempt | Mission / stack | Start UTC | End UTC | Artifacts | BIN bytes / SHA-256 | Events; RB/reset | Schedule | Original manifest | Original mechanism | Ready | Classification / exact blocker |
| ---: | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `var/runs/tailwind_phase3_healthy_speed15_gate_20260622` | 001 | M15 hash **not recorded** / S0 | 2026-06-22T09:52:12Z | 2026-06-22T09:52:12Z | 9/9 | 7,507,968 / `0af8304f37f25cad886791c822cfe186031de936c5b0deec729fb7bf59356fed` | 1; yes/yes | yes 1/1 healthy baseline | true / nominal / valid nominal | n/a | no | `raw_evidence_incomplete`: mission hash absent; untracked-input hashes absent; start=end; manifest retains no-SITL stimulus verification |
| 0 | `var/runs/tailwind_phase3_healthy_speed15_gate_20260622` | 002 | M15 hash **not recorded** / S0 | 2026-06-22T10:55:42Z | 2026-06-22T10:55:42Z | 9/9 | 7,565,312 / `521fadd9e21f75f77017e0841060094c80398f69ef5babcf1b1406c6525a6c32` | 1; yes/yes | yes 1/1 healthy baseline | true / nominal / valid nominal | n/a | no | `raw_evidence_incomplete`: mission hash absent; untracked-input hashes absent; start=end; manifest retains no-SITL stimulus verification |
| 0 | `var/runs/tailwind_phase3_healthy_speed15_gate_20260622` | 003 | M15 / S0 | 2026-06-22T11:24:51Z | 2026-06-22T11:28:06Z | 9/9 | 7,589,888 / `d3bad8b3477d6f03791da6e2218ca6cd6720b175a0d04a2737a7cf94c8eae713` | 1; yes/yes | yes 1/1 healthy baseline | true / nominal / valid nominal | n/a | yes | `ready_for_corrected_reanalysis` |
| 1 | `var/runs/tailwind_protected_cruise_follow_p200_n3` | 001 | MCR / S0 | 2026-06-22T18:00:28Z | 2026-06-22T18:15:53Z | 11/11 | 41,832,448 / `c8299455340906218b6a8defd3f13e16345efb6531b26a3fb2135378c493163d` | 13; yes/yes | no 13/21 low-altitude abort | true / loss-timeout / valid bad behavior | `clamp_verified` | yes | `ready_for_corrected_reanalysis` |
| 1 | `var/runs/tailwind_protected_cruise_follow_p200_n3` | 002 | MCR / S0 | 2026-06-22T18:27:17Z | 2026-06-22T18:43:58Z | 11/11 | 45,060,096 / `d991d17370043dd97fe65d002e158e17c6cd5ec49a8d4baff3abe75b702da021` | 15; yes/yes | no 15/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 1 | `var/runs/tailwind_protected_cruise_follow_p200_n3` | 003 | MCR / S0 | 2026-06-22T19:39:33Z | 2026-06-22T19:55:19Z | 11/11 | 42,311,680 / `8111c1f8afffa7485d81567593260fc5a932efd8f1abae46dc22e12ab4a44993` | 14; yes/yes | no 14/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 2 | `var/runs/tailwind_diagnostic_cruise_follow_p200_n3` | 001 | MCR / S1 | 2026-06-22T16:25:24Z | 2026-06-22T16:39:39Z | 11/11 | 38,522,880 / `f61f4d9e9c9c1242b01e081ac9f4233255e1979a42512de8e3929ef2c5250df3` | 12; yes/yes | no 12/21 low-altitude abort | false / loss-timeout / mechanism unverified | `mechanism_unverified` | yes | `analysis_only_false_negative_candidate` |
| 2 | `var/runs/tailwind_diagnostic_cruise_follow_p200_n3` | 002 | MCR / S1 | 2026-06-22T17:12:33Z | 2026-06-22T17:26:45Z | 11/11 | 37,806,080 / `75827689c80857df913fe5236e9fdb3a6846d1c34f5f9f7629c1874862d61072` | 12; yes/yes | no 12/21 low-altitude abort | false / loss-timeout / mechanism unverified | `mechanism_unverified` | yes | `analysis_only_false_negative_candidate` |
| 2 | `var/runs/tailwind_diagnostic_cruise_follow_p200_n3` | 003 | MCR / S1 | 2026-06-22T17:45:11Z | 2026-06-22T17:59:28Z | 11/11 | 38,326,272 / `a609b869457eb8c74f3f01721b7e7d6f927df1cd609c3eb0b7ca730f5ecf187a` | 12; yes/yes | no 12/21 low-altitude abort | false / loss-timeout / mechanism unverified | `mechanism_unverified` | yes | `analysis_only_false_negative_candidate` |
| 3 | `var/runs/tailwind_max28_speed15_p200_n3` | 001 | M15 / S2 | 2026-06-22T15:35:36Z | 2026-06-22T15:51:16Z | 11/11 | 42,278,912 / `de1d3275b8dca7449f17845f6176796f4ae762c8953d81184f3b04460cce4e56` | 14; yes/yes | no 14/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 3 | `var/runs/tailwind_max28_speed15_p200_n3` | 002 | M15 / S2 | 2026-06-22T15:51:36Z | 2026-06-22T16:07:13Z | 11/11 | 42,229,760 / `9602e4f38b12659eb2c39d1835e18a813caf367502444eea74d229209625edfd` | 14; yes/yes | no 14/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 3 | `var/runs/tailwind_max28_speed15_p200_n3` | 003 | M15 / S2 | 2026-06-22T16:07:32Z | 2026-06-22T16:23:26Z | 11/11 | 42,070,016 / `7f0e535f0462ec01bb17d2d712807b9ba0d8f7ebf9ace350ae5f968825b96d8d` | 14; yes/yes | no 14/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 4 | `var/runs/tailwind_max18_speed15_p200_n3` | 001 | M15 / S3 | 2026-06-22T14:33:02Z | 2026-06-22T14:48:45Z | 11/11 | 42,528,768 / `438ed38b5951f8015cfd6c5a5913d29d4125275326a89c23effe6aa7d8a560e5` | 14; yes/yes | no 14/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 4 | `var/runs/tailwind_max18_speed15_p200_n3` | 002 | M15 / S3 | 2026-06-22T14:49:25Z | 2026-06-22T15:11:15Z | 11/11 | 59,682,816 / `bf33eac4f6ab049690c9e8fbf3a33a374a7a06b3d0690fa1c0f15738bfeffd82` | 20; yes/yes | no 20/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 4 | `var/runs/tailwind_max18_speed15_p200_n3` | 003 | M15 / S3 | 2026-06-22T15:11:35Z | 2026-06-22T15:35:17Z | 11/11 | 65,044,480 / `f542267c72cba4566f015d56cd81849db8bb35d204eaf65e88c988ce1cd68145` | 21; yes/yes | yes 21/21 ramp complete | true / degraded / valid degraded | `clamp_verified` | yes | `ready_for_corrected_reanalysis` |
| 5 | `var/runs/tailwind_cruise17_speed15_p200_n1` | 001 | M15 / S4 | 2026-06-22T14:16:54Z | 2026-06-22T14:32:33Z | 11/11 | 42,381,312 / `52d8153639a988c948768a3229b00ad305cc8f1c3d2ba3d715b0b5878c873f56` | 14; yes/yes | no 14/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 6 | `var/runs/tailwind_scaled18_28_speed15_p200_n1` | 001 | M15 / S5 | 2026-06-22T13:48:48Z | 2026-06-22T14:12:26Z | 11/11 | 64,851,968 / `e843f305cdb471f088d5b2b47d7f345301aa1ac2fa5a9d4e510f9f9c5a63873b` | 21; yes/yes | yes 21/21 ramp complete | true / degraded / valid degraded | `clamp_verified` | yes | `ready_for_corrected_reanalysis` |
| 7 | `var/runs/tailwind_standard_speed15_p200_n1` | 001 | M15 / S0 | 2026-06-22T13:21:11Z | 2026-06-22T13:36:58Z | 11/11 | 42,680,320 / `75ee3e5fc322678cf82afc2924c91f3079b6b7acf19bdfc176e9df3f75f7348b` | 14; yes/yes | no 14/21 low-altitude abort | false / loss-timeout / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 8 | `var/runs/tailwind_standard_speed15_p100_n1` | 001 | M15 / S0 | 2026-06-22T13:07:12Z | 2026-06-22T13:20:42Z | 11/11 | 36,257,792 / `57af7cb4212652d25d64cee5bd8dbf5d399b75a2eeb6378e1afa6b1a42045a5f` | 11; yes/yes | yes 11/11 ramp complete | false / degraded / clamp not exercised | `clamp_not_exercised` | yes | `analysis_only_false_negative_candidate` |
| 9 | `var/runs/tailwind_standard_speed15_pulse_p130_n1` | 001 | M15 / S0 | 2026-06-22T11:35:36Z | 2026-06-22T12:04:34Z | 11/11 | 77,258,752 / `5da89257c8ce42892b2ce4b86b1d737222b0203678c8c80d0fca4e042f9d8fb2` | 26; yes/yes | yes 26/26 pulse complete | false / degraded / sensor rejected before verification | `sensor_rejected_before_verification` | yes | `ready_for_corrected_reanalysis`; additive correction already exists |
| 9 | `var/runs/tailwind_standard_speed15_pulse_p130_n1` | 002 | M15 / S0 | 2026-06-22T12:06:46Z | 2026-06-22T12:35:39Z | 11/11 | 78,589,952 / `202889bda27a3654f79b307257597f4642904060515061d49c3552c0080fe920` | 26; yes/yes | yes 26/26 pulse complete | false / degraded / sensor rejected before verification | `sensor_rejected_before_verification` | yes | `duplicate_extra_attempt`; valid repetition, additive correction already exists |

The Phase 1–8 `clamp_not_exercised` and `mechanism_unverified` rows are marked
as analysis-only false-negative candidates because their raw evidence,
configuration, applied-event readbacks, resets, and BINs are intact. This
classification does not pre-judge the corrected mechanism verdict. The
low-altitude stop is a recorded flight-behavior stop after valid injection, not
a runtime or injection failure, and it does not justify a rerun by itself.

## Expected-versus-discovered coverage

`Analysis-only failures` counts historical evaluator verdicts, including the
two Phase 9 verdicts already superseded by the 2026-06-23 additive correction.
`Usable` means the raw attempt is suitable for corrected offline analysis; it
does not mean a new behavior result is accepted.

| Phase | Expected | Discovered | Usable | Extras | Missing | Wrong mission | Wrong overlay | Analysis-only failures | Genuine runtime/injection failures |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 1 | 3 | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| 1 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 2 | 0 |
| 2 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| 3 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 3 | 0 |
| 4 | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 2 | 0 |
| 5 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| 6 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| 7 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| 8 | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| 9 | 1 | 2 | 2 | 1 | 0 | 0 | 0 | 2 | 0 |
| **Total including gate** | **18** | **21** | **19** | **3** | **0** | **0** | **0** | **15** | **0** |

The approved fault matrix is Phases 1–9, not the separate healthy gate: all
17 approved attempts exist and are usable. The discovered matrix has 18 usable
attempts because Phase 9 has a second valid repetition.

No phase was found under a misleading or configuration-inconsistent campaign
root. All directory names agree with the configuration-derived mapping. No
wrong-mission or wrong-overlay attempt was found.

## Duplicate, extra, and superseded attempts

- Phase 9 attempt 002 is one valid extra repetition. Preserve it and include it
  as repetition evidence; it is not a replacement for another phase.
- Phase 0 attempts 001 and 002 are superseded gate attempts. Their flight
  artifacts and BINs exist, but strict current evidence provenance is
  incomplete: terminal timestamps collapse to one time, stimulus verification
  remains the no-SITL placeholder, and mission/untracked-input hashes are
  absent. Phase 0 attempt 003 closes the gate with complete provenance, so
  these defects do not create a missing cell or rerun need.

## Same-mission P130 headwind control

Chunk 1 is complete under:

`var/runs/headwind_control_same_mission_standard_speed15_pulse_p130_n1`

Attempt 001 did not produce a BIN. Attempt 002 is the completed usable control:
26/26 scheduled events, all applied-event readbacks complete, reset complete,
`clamp_verified`, and interpretable. Its BIN is 82,432,000 bytes with SHA-256
`448a707589771e7528bac9add0e8b0c83acf21670f425121a930a1e24a863029`.
No launch or rerun was performed in Chunk 2.

## Ready for corrected offline reanalysis

All attempts in the inventory are ready except Phase 0 attempts 001 and 002.
That gives 19 ready attempts: Phase 0 attempt 003; all 16 Phase 1–8 attempts;
and both Phase 9 attempts. Phase 9 has already received its corrected additive
reanalysis, so it does not need to be repeated in Chunk 3 merely to repair the
old evaluator verdict.

There are no configuration mismatches, true runtime/injection failures, or
missing BINs among the approved 17-attempt fault matrix.

## Proposed Chunk 3 input list

Chunk 3 should analyze the remaining blind/frozen Phase 1–8 inputs only. Exact
roots and attempts:

- `var/runs/tailwind_protected_cruise_follow_p200_n3`: attempts 001, 002, 003
- `var/runs/tailwind_diagnostic_cruise_follow_p200_n3`: attempts 001, 002, 003
- `var/runs/tailwind_max28_speed15_p200_n3`: attempts 001, 002, 003
- `var/runs/tailwind_max18_speed15_p200_n3`: attempts 001, 002, 003
- `var/runs/tailwind_cruise17_speed15_p200_n1`: attempt 001
- `var/runs/tailwind_scaled18_28_speed15_p200_n1`: attempt 001
- `var/runs/tailwind_standard_speed15_p200_n1`: attempt 001
- `var/runs/tailwind_standard_speed15_p100_n1`: attempt 001

Phase 0 and Phase 9 remain prior-known controls. Chunk 3 must continue to use
BIN `SIM_ARSPD_RATIO` `PARM` transitions, `CTUN.AsT` for actual source, and
`ARSP.U` as the distinct parameter-level state.

## Rerun decision

No rerun is currently justified. Corrected offline batch analysis is the next
step. A rerun should be considered only if Chunk 3 discovers a raw-data defect
that this provenance/readback/BIN inventory could not detect; an old evaluator
rejection or a valid low-altitude behavior stop is not such a defect.
