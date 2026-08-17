# Campaign Lane Documentation Standard

Every campaign lane gets an architecture document, and every one of those
documents has the same shape. An agent or engineer who learns one campaign
lane's layout must be able to navigate the next one without guessing.

This standard defines that shape. It is the authority a future campaign lane
conformance check cites.

It complements, and does not replace, the two registries:

- `docs/architecture/campaign_lanes.md` — which campaign lanes exist, and the
  simulation lane, mission, overlay, and CLI entry point each uses.
- `docs/architecture/simulation_lanes.md` — the aircraft + world + launcher +
  bridge axis.

A campaign lane document is the depth behind one registry row. Do not restate
registry tables in a lane document; link to them.

## Scope And Terminology

This standard governs documents under `docs/architecture/` that describe a
**campaign lane** — a lane registered in
`src/sim_ard_gaw/campaigns/test_suite/cli/_registry.py`.

Use the qualified term "campaign lane" per
`governance/standards/naming.md`. This includes document titles: a campaign
lane document is titled `# <Name> Campaign Lane`, not `# <Name> Lane`.

### Two Senses Of "Envelope"

The word `envelope` is already committed in this workspace and must not be
reused to name a campaign lane profile:

- **Parameter/mission bundle** — a named set of conditions a fault experiment
  runs inside. `gps_failure` declares `baseline`, `fast_cruise_18mps`,
  `ekf_gate300_glitch0`, and `ekf_glitch10` in `ENVELOPE_DEFINITIONS`, selected
  by `--envelope`. ADR-0012 and ADR-0013 use the word this way.
- **Aircraft performance limits** — the cruise/min/max airspeed band, as in
  `config/overlays/plane_airspeed.parm`.

In both senses an envelope is the *setting* an experiment runs in, never the
subject of study. That is why the second profile below is called an
**environment sweep** and not an "envelope campaign": in a sweep the varied
quantity *is* the subject.

## Two Profiles

Campaign lanes are not all the same kind of experiment. Forcing one shape on
all of them would make a lane permanently non-conformant, and a rule that is
always violated teaches readers to ignore violations.

| Profile | Difficulty comes from | Verdict style | Lanes |
| --- | --- | --- | --- |
| **Fault injection** | A lie injected into a sensor; the world stays honest | Behavior bands; characterize, never PASS/FAIL | `airspeed_failure`, `gps_failure` |
| **Environment sweep** | A harder world; the aircraft's sensors stay honest | Scored metric with success/failure and retry | `wind_matrix` |

The distinction is observable in code, not just prose:

- Fault-injection lanes expose a `classify_observation` producing named
  behavior bands (`silent_drift`, `nominal_completion`), and separate
  measurement validity from behavior class.
- The environment-sweep lane maps to `VerdictClass.FAILED_RETRYABLE` with a
  `retryable` flag and `success_full` / `success_square_only` statuses. A
  retryable failure is incoherent for a lane whose crashes are the result.

Both profiles share the same 10-module plugin spine. That is the framework
chassis, not evidence that they are the same experiment.

A lane's profile determines which section list it must satisfy. Sections 1-3
and the last three are common to both.

## Required Sections — Fault Injection Profile

Nine sections, in this order. Every one is required.

| # | Section | Must answer |
| --- | --- | --- |
| 1 | `Purpose & Scope` | What this lane studies, and explicitly what it is *not* (not certification, not controller design) |
| 2 | `Status` | What is verified, as of which date, with the evidence path |
| 3 | `Simulation Lane & Stack` | Aircraft, world, launch targets, parameter overlay |
| 4 | `Mission & Trigger` | Route geometry, altitude, and the exact injection point |
| 5 | `Fault Set & Cases` | What is injected, via which knobs, and how severity is swept |
| 6 | `Measurement & Validity` | What is measured, and what makes a run a valid observation |
| 7 | `Behavior Classification` | The outcome vocabulary and how a run is assigned to it |
| 8 | `Output Paths` | Where raw and curated artifacts go |
| 9 | `Decisions & References` | Governing ADRs with real statuses, runbooks, operations doc |

## Required Sections — Environment Sweep Profile

Eight sections. Sections 1-3, 7 (renumbered), and 8-9 match the fault profile;
sections 4-6 differ because there is no fault and no injection trigger.

| # | Section | Must answer |
| --- | --- | --- |
| 1 | `Purpose & Scope` | What this lane studies, and what it is not |
| 2 | `Status` | What is verified, as of which date, with the evidence path |
| 3 | `Simulation Lane & Stack` | Aircraft, world, launch targets, parameter overlay |
| 4 | `Mission & Sweep` | Route geometry and the swept environmental variable with its values |
| 5 | `Metric & Validity` | The scored metric, and what makes a run valid |
| 6 | `Scoring & Verdict` | How the metric becomes a verdict, including retry semantics |
| 7 | `Output Paths` | Where raw and curated artifacts go |
| 8 | `Decisions & References` | Governing ADRs with real statuses, runbooks |

## Optional Sections

Domain content that is legitimately specific to one lane. These are **never**
forced onto another lane, and never removed to make two documents match.

Place them after the classification/verdict section and before `Output Paths`.

Current examples:

- `The Knee` — GPS EKF innovation-gate physics.
- `Key SIM_ARSPD_* Semantics` — airspeed SITL parameter semantics.
- `Reference Wind` — the airspeed lane's controlled wind constant.

A section belongs here when it explains *this sensor's or this world's physics*
rather than answering one of the required questions above.

## Rules

1. **No silent absence.** If a lane genuinely cannot fill a required section,
   the section still appears with `Not applicable — <reason>`. A missing
   heading is a defect; a documented gap is not.
2. **Reorganise, do not truncate.** Bringing a document to this shape must not
   delete content. Lanes differ in maturity and their documents differ in
   length; that asymmetry is allowed to survive.
3. **Do not level down.** Where one lane documents a required section more
   rigorously than another, the stronger version stands. Record the weaker
   one as a gap rather than trimming the stronger to match.
4. **State ADR statuses exactly.** A referenced ADR's stated status must match
   its own `Status:` line. Where an ADR has been corrected or superseded, the
   correction must be reachable from the lane document — a reader who finds a
   superseded decision and no path to its correction is worse off than one who
   finds nothing.
5. **No claim without dated evidence.** Per `AGENTS.md`. A lane that is
   structurally tested but never flown says so.
6. **Link, do not duplicate.** Registry facts live in the registries.

## Conformance

Until an automated check exists, conformance is checked by reading: every
required section present in order, or explicitly marked not applicable.

Writing that check is planned separately. This standard is its specification.
