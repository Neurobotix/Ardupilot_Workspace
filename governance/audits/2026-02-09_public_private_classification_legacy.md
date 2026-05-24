# Migration Classification Document

**Purpose:** Classify every directory/file into PUBLIC, NEVER, or TRANSITION categories for GitHub migration.

**Last Updated:** 2026-02-09
**Status:** FINAL - Ready for execution

---

## Legend

| Symbol | Category | Meaning |
|--------|----------|---------|
| 🟢 | **PUBLIC** | Safe to commit, standard implementation |
| 🔴 | **NEVER** | Your edge, never commit |
| 🟡 | **TRANSITION** | Needs dual versions (public skeleton + private detailed) |
| ⚫ | **EXTERNAL** | External dependency, gitignore |

---

## DECISIONS FINALIZED

1. ✅ Push `src/ardupilot_gazebo/` - Your fork with modifications
2. ✅ Gitignore `src/ardupilot/` - Document how to clone (no comments in gitignore)
3. ✅ Gitignore `src/SITL_Models/` - Document how to clone
4. ✅ Edit `003_Plane_Airspeed/TEST_RESULT_*.md` - Removed hints about alternatives
5. ✅ Create skeleton bridges - `lidar_bridge.py`, `airspeed_bridge.py` in root `scripts/`
6. ✅ Gitignore `launch.sh` - No skeleton, omit entirely

---

## Root Level (`/home/ahmed/ardupilot_workspace/`)

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `README.md` | File | 🟡 TRANSITION | Currently minimal, good for public | Keep as-is |
| `setup.bash` | File | 🔴 NEVER | Contains YOUR path discoveries, env setup, aliases | Gitignore + create skeleton |
| `test_zephyr_mission.txt` | File | 🟢 PUBLIC | Just waypoints | Commit |
| `.cursorrules` | File | 🟢 PUBLIC | Editor config | Commit |

---

## `.ai/` Directory

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `.ai/` | Dir | 🔴 NEVER (ALL) | Your research diary, the WHY behind everything | Gitignore entirely |
| `.ai/architecture/` | Dir | 🔴 NEVER | System understanding, data flow insights | Gitignore |
| `.ai/external_mods/` | Dir | 🔴 NEVER | Documents WHY changes were made, what failed | Gitignore |
| `.ai/features/` | Dir | 🔴 NEVER | Deep implementation docs with discoveries | Gitignore |
| `.ai/sessions/` | Dir | 🔴 NEVER | Your work diary, debugging journey | Gitignore |
| `.ai/issues/` | Dir | 🔴 NEVER | Problem-solving process | Gitignore |
| `.ai/vehicles/` | Dir | 🔴 NEVER | Vehicle-specific learnings | Gitignore |
| `.ai/tests/` | Dir | 🔴 NEVER | Test analysis beyond results | Gitignore |
| `.ai/templates/` | Dir | 🔴 NEVER | Your documentation system | Gitignore |

---

## `.private/` Directory

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `.private/` | Dir | 🔴 NEVER (ALL) | Already designed to be private | Gitignore (already is) |
| `.private/config/` | Dir | 🔴 NEVER | Tuned parameters (NOTE: appears outdated vs SIM_ARD_GAW) | Keep private |
| `.private/scripts/` | Dir | 🔴 NEVER | (NOTE: smaller than SIM_ARD_GAW version) | Keep private |
| `.private/docs/` | Dir | 🔴 NEVER | Detailed docs with gotchas | Keep private |
| `.private/notes/` | Dir | 🔴 NEVER | Research notes | Keep private |
| `.private/WORKSPACE_GUIDE.md` | File | 🔴 NEVER | This very system | Keep private |
| `.private/GIT_COMMIT_STYLE.md` | File | 🔴 NEVER | Your workflow | Keep private |

---

## `.specify/` Directory

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `.specify/` | Dir | 🟢 PUBLIC | Framework configuration, not proprietary | Commit |
| `.specify/memory/` | Dir | 🟢 PUBLIC | Constitution file | Commit |
| `.specify/scripts/` | Dir | 🟢 PUBLIC | Framework scripts | Commit |
| `.specify/templates/` | Dir | 🟢 PUBLIC | Templates | Commit |

---

## `.claude/` Directory

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `.claude/` | Dir | 🟢 PUBLIC | Claude command shortcuts, generic | Commit |
| `.claude/commands/` | Dir | 🟢 PUBLIC | Speckit commands | Commit |

---

## `src/` Directory

### `src/ardupilot/`

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `src/ardupilot/` | Dir | ⚫ EXTERNAL | Upstream ArduPilot, runtime dependency only | Gitignore |

### `src/SITL_Models/`

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `src/SITL_Models/` | Dir | ⚫ EXTERNAL | Upstream models, reference only | Gitignore |

### `src/ardupilot_gazebo/` (YOUR FORK)

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `src/ardupilot_gazebo/` | Dir | 🟡 TRANSITION | Contains YOUR modifications (airspeed) | See below |
| `src/ardupilot_gazebo/src/ArduPilotPlugin.cc` | File | 🟡 TRANSITION | Code is visible, but WHY is in .ai/ | Commit code |
| `src/ardupilot_gazebo/CMakeLists.txt` | File | 🟡 TRANSITION | Has your fix | Commit code |
| `src/ardupilot_gazebo/build/` | Dir | ⚫ BUILD | Build artifacts | Gitignore |
| All other files | Files | 🟢 PUBLIC | Upstream unchanged | Commit |

**Note on ardupilot_gazebo:** The CODE changes are visible (anyone can read the diff), but the JOURNEY (why native sensor failed, velocity magnitude solution) is in `.ai/external_mods/` which is NEVER committed.

---

### `src/SIM_ARD_GAW/` (YOUR PROJECT)

This is the main project. Currently has its own `.git` - will merge into root.

#### Models

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `models/README.md` | File | 🟢 PUBLIC | Basic index | Commit |
| `models/iris_with_lidar/` | Dir | 🟢 PUBLIC | Model geometry, standard SDF | Commit |
| `models/mini_talon/` | Dir | 🟢 PUBLIC | Model geometry | Commit |
| `models/mini_talon_with_airspeed/` | Dir | 🟢 PUBLIC | Model geometry, sensor config visible | Commit |
| `models/mini_talon_with_lidar/` | Dir | 🟢 PUBLIC | Model geometry | Commit |

#### Worlds

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `worlds/*.sdf` | Files | 🟢 PUBLIC | World files, standard SDF | Commit all |

#### Config

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `config/` | Dir | 🔴 NEVER | **CRITICAL**: Contains tuned parameters! | Gitignore |
| `config/copter_params.parm` | File | 🔴 NEVER | Tuned values | Gitignore |
| `config/plane_params.parm` | File | 🔴 NEVER | Tuned values (airspeed, nav, etc.) | Gitignore |
| `config/runway_land_mission.waypoints` | File | 🟢 PUBLIC | Just waypoints | Could commit |

**WAIT - IMPORTANT DISCOVERY:**
You said parameters can be extracted from log files (.bin). But you're ALSO sharing log files in `logs/` directory. If log files are shared, parameters are exposed!

**Decision needed:** Either:
1. Gitignore `logs/` entirely (no test results shared)
2. Strip .bin files but keep markdown results (current approach - .bin gitignored)
3. Accept that parameters are exposed via logs

#### Scripts

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `scripts/` | Dir | 🔴 NEVER | Your integration knowledge! | Gitignore |
| `scripts/launch.sh` | File | 🔴 NEVER | 489 lines of YOUR setup knowledge | Gitignore |
| `scripts/lidar_bridge_unified.py` | File | 🔴 NEVER | Working bridge implementation | Gitignore |
| `scripts/airspeed_bridge.py` | File | 🔴 NEVER | Working bridge implementation | Gitignore |
| `scripts/monitor.py` | File | 🔴 NEVER | Your monitoring tools | Gitignore |
| `scripts/log_flight_data.py` | File | 🔴 NEVER | Your logging tools | Gitignore |
| `scripts/cleanup.sh` | File | 🟢 PUBLIC | Generic cleanup | Could commit |

#### Docs

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `docs/` | Dir | 🟡 TRANSITION | Has basic docs, needs review | See below |
| `docs/INSTALLATION.md` | File | 🟢 PUBLIC | Already skeleton (42 lines vs 299 in .private) | Commit |
| `docs/TROUBLESHOOTING.md` | File | 🟡 TRANSITION | Need to verify no solutions leaked | Review |
| `docs/FLIGHT_MODES.md` | File | 🟢 PUBLIC | Standard info | Commit |
| `docs/diagrams/` | Dir | 🟢 PUBLIC | Visual diagrams | Commit |

#### Logs (Test Results)

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `logs/README.md` | File | 🟢 PUBLIC | Index | Commit |
| `logs/flights/` | Dir | ⚫ GITIGNORED | .bin files already ignored | Keep ignored |
| `logs/00X_*/TEST_RESULT_*.md` | Files | 🟡 TRANSITION | Shows WHAT works, need to ensure no WHY | Review each |

#### Notebooks

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `notebooks/` | Dir | 🔴 NEVER | Analysis notebooks, discoveries | Gitignore |

---

## Build Artifacts

| Item | Type | Category | Reasoning | Action |
|------|------|----------|-----------|--------|
| `build/` | Dir | ⚫ BUILD | CMake output | Gitignore |
| `install/` | Dir | ⚫ BUILD | Install output | Gitignore |
| `env/` | Dir | ⚫ BUILD | Python venv | Gitignore |

---

## Summary Table

| Category | Directories/Files |
|----------|-------------------|
| 🟢 **PUBLIC** | `.specify/`, `.claude/`, `models/`, `worlds/`, `docs/` (skeleton), `logs/TEST_RESULT_*.md` (reviewed), `.cursorrules` |
| 🔴 **NEVER** | `.ai/`, `.private/`, `setup.bash`, `config/`, `scripts/`, `notebooks/` |
| 🟡 **TRANSITION** | `src/ardupilot_gazebo/` (code only), `docs/TROUBLESHOOTING.md` (review), `logs/` test results (review) |
| ⚫ **EXTERNAL/BUILD** | `src/ardupilot/`, `src/SITL_Models/`, `build/`, `install/`, `env/` |

---

## Proposed `.gitignore` (Root Level)

```gitignore
# ============================================
# NEVER COMMIT - Your Edge
# ============================================
.ai/
.private/
setup.bash

# ============================================
# PROJECT FILES - Your Knowledge
# ============================================
config/
scripts/
notebooks/

# ============================================
# EXTERNAL DEPENDENCIES
# ============================================
src/ardupilot/
src/SITL_Models/

# ============================================
# BUILD ARTIFACTS
# ============================================
build/
install/
env/
src/ardupilot_gazebo/build/

# ============================================
# LOG FILES (binary)
# ============================================
*.BIN
*.bin
*.tlog
logs/flights/

# ============================================
# STANDARD IGNORES
# ============================================
__pycache__/
*.pyc
.vscode/
*.swp
.DS_Store
```

---

## Questions Remaining

1. **The `logs/` test results** - need to audit each for leaked insights
2. **`docs/TROUBLESHOOTING.md`** - need to compare public vs private versions
3. **`src/ardupilot_gazebo/`** - commit as-is or clean up git history first?
4. **Public skeleton scripts?** - Create dummy `scripts/` for appearance, or just omit?

---

## Next Steps

1. ✅ Classification complete (this document)
2. ⬜ Audit `logs/TEST_RESULT_*.md` files for leaked insights
3. ⬜ Audit `docs/TROUBLESHOOTING.md`
4. ⬜ Decide on skeleton scripts (yes/no)
5. ⬜ Create root `.gitignore`
6. ⬜ Restructure and commit
