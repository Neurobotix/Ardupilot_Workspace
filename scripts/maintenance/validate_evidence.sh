#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1

failures=0

section() {
  printf '\n== %s ==\n' "$1"
}

pass() {
  printf 'PASS: %s\n' "$1"
}

fail() {
  printf 'FAIL: %s\n' "$1"
  failures=$((failures + 1))
}

print_list() {
  sed 's/^/  - /'
}

allow_reviewed_evidence_signature() {
  local path="$1"

  case "$path" in
    "evidence/curated_logs/phase_2_runtime_2026-05-20/bridge-copter_console.txt")
      printf '%s\n' "reviewed bounded Phase 2 bridge console capture"
      return 0
      ;;
    "evidence/curated_logs/phase_2_runtime_2026-05-20/bridge-plane_console.txt")
      printf '%s\n' "reviewed bounded Phase 2 bridge console capture"
      return 0
      ;;
  esac

  return 1
}

check_raw_log_leakage() {
  section "evidence raw log leakage"
  local output
  output="$(
    find . \
      \( -path './.git' -o -path './var' -o -path './.private' \
      -o -path './src/ardupilot' -o -path './src/SITL_Models' \
      -o -path './src/ardupilot_gazebo' -o -path './env' \
      -o -path './build' -o -path './install' \) -prune -o \
      -type f \( -iname '*.bin' -o -name '*.tlog' -o -name '*.tlog.raw' \) \
      -print | sort
  )"
  if [[ -z "$output" ]]; then
    pass "no raw .BIN/.bin/.tlog/.tlog.raw files outside allowed runtime or ignored homes"
  else
    fail "raw log files leaked outside allowed runtime or ignored homes"
    printf '%s\n' "$output" | print_list
  fi
}

check_evidence_runtime_pollution() {
  section "tracked evidence runtime pollution"
  local raw_files raw_dirs allowed disallowed path reason
  raw_files="$(
    find evidence -type f \
      \( -iname '*.bin' -o -name '*.tlog' -o -name '*.tlog.raw' \
      -o -iname '*.log' -o -name 'LASTLOG.TXT' -o -name 'mav.parm' \
      -o -name 'defaults.parm' -o -name '*_console.txt' \) \
      -print 2>/dev/null | sort
  )"
  raw_dirs="$(
    find evidence -type d \
      \( -name 'logs' -o -name 'runs' -o -name 'mavproxy' \
      -o -name 'flight_logger' -o -name 'terrain' -o -name 'sitl' \
      -o -name 'round_robin_logs' -o -name 'orchestrator_logs' \
      -o -name '*_sitl_state' \) \
      -print 2>/dev/null | sort
  )"

  allowed=""
  disallowed=""
  while IFS= read -r path; do
    [[ -z "$path" ]] && continue
    if reason="$(allow_reviewed_evidence_signature "$path")"; then
      allowed+="$path: $reason"$'\n'
    else
      disallowed+="$path"$'\n'
    fi
  done <<< "$raw_files"

  if [[ -n "$allowed" ]]; then
    echo "allowed reviewed signatures:"
    printf '%s' "$allowed" | print_list
  fi

  if [[ -z "$disallowed" && -z "$raw_dirs" ]]; then
    pass "evidence homes contain no unallowlisted raw runtime signatures"
  else
    fail "evidence homes contain raw runtime signatures without review allowlists"
    if [[ -n "$disallowed" ]]; then
      echo "raw-looking files:"
      printf '%s' "$disallowed" | print_list
    fi
    if [[ -n "$raw_dirs" ]]; then
      echo "raw-looking directories:"
      printf '%s\n' "$raw_dirs" | print_list
    fi
  fi
}

check_raw_run_directories() {
  section "raw run directories"
  local output
  output="$(
    find . \
      \( -path './.git' -o -path './var' -o -path './.private' \
      -o -path './src/ardupilot' -o -path './src/SITL_Models' \
      -o -path './src/ardupilot_gazebo' -o -path './env' \
      -o -path './build' -o -path './install' \) -prune -o \
      -type d \( -name 'runs' -o -name 'round_robin_logs' \
      -o -name 'orchestrator_logs' -o -name '*_sitl_state' \) \
      -print | sort
  )"
  if [[ -z "$output" ]]; then
    pass "no raw campaign or simulator run directories outside runtime or ignored homes"
  else
    fail "raw campaign or simulator run directories leaked outside runtime or ignored homes"
    printf '%s\n' "$output" | print_list
  fi
}

check_report_home_shape() {
  section "report home shape"
  local allowed_subdirs=(
    "evidence/reports/migration"
    "evidence/reports/features"
    "evidence/reports/operations"
    "evidence/reports/audits"
    "evidence/reports/campaigns"
  )
  local non_md unexpected_dirs top_level_reports
  local entry path

  non_md="$(
    find evidence/reports -type f ! -name '*.md' -print 2>/dev/null | sort
  )"

  unexpected_dirs="$(
    while IFS= read -r entry; do
      [[ -z "$entry" ]] && continue
      local allowed=0
      for path in "${allowed_subdirs[@]}"; do
        if [[ "$entry" == "$path" ]]; then
          allowed=1
          break
        fi
      done
      if [[ "$allowed" -eq 0 ]]; then
        printf '%s\n' "$entry"
      fi
    done < <(find evidence/reports -mindepth 1 -maxdepth 1 -type d -print 2>/dev/null | sort)
  )"

  top_level_reports="$(
    find evidence/reports -mindepth 1 -maxdepth 1 -type f -name '*.md' \
      ! -name 'README.md' -print 2>/dev/null | sort
  )"

  if [[ -z "$non_md" && -z "$unexpected_dirs" && -z "$top_level_reports" ]]; then
    pass "evidence/reports contains README, allowed subdirectories, and report Markdown only"
  else
    fail "evidence/reports has disallowed entries"
    if [[ -n "$non_md" ]]; then
      echo "non-Markdown files:"
      printf '%s\n' "$non_md" | print_list
    fi
    if [[ -n "$unexpected_dirs" ]]; then
      echo "unexpected top-level subdirectories:"
      printf '%s\n' "$unexpected_dirs" | print_list
    fi
    if [[ -n "$top_level_reports" ]]; then
      echo "report files at the top level (only README.md is allowed there):"
      printf '%s\n' "$top_level_reports" | print_list
    fi
  fi
}

check_evidence_top_level() {
  section "evidence top-level homes"
  local output
  output="$(
    find evidence -mindepth 1 -maxdepth 1 \
      \( -type d ! -name 'curated_logs' ! -name 'indexes' ! -name 'manifests' \
      ! -name 'reports' ! -name 'templates' -o -type f \) \
      -print 2>/dev/null | sort
  )"
  if [[ -z "$output" ]]; then
    pass "evidence top-level content stays in the approved homes"
  else
    fail "evidence content is outside approved top-level homes"
    printf '%s\n' "$output" | print_list
  fi
}

check_phase_report_home() {
  section "phase report home"
  local output
  output="$(
    find . \
      \( -path './.git' -o -path './var' -o -path './.private' \
      -o -path './src/ardupilot' -o -path './src/SITL_Models' \
      -o -path './src/ardupilot_gazebo' -o -path './env' \
      -o -path './build' -o -path './install' \) -prune -o \
      -type f -name 'PHASE_*.md' ! -path './evidence/reports/*' \
      -print | sort
  )"
  if [[ -z "$output" ]]; then
    pass "dated phase reports stay under evidence/reports"
  else
    fail "phase-named evidence reports exist outside evidence/reports"
    printf '%s\n' "$output" | print_list
  fi
}

check_template_inventory() {
  section "evidence template inventory"
  local path
  local failed=0
  local required=(
    "evidence/templates/launch_runtime_smoke_report.md"
    "evidence/templates/vehicle_verification_report.md"
    "evidence/templates/campaign_result_report.md"
    "evidence/templates/evidence_promotion_checklist.md"
  )

  for path in "${required[@]}"; do
    if [[ -f "$path" ]] &&
       rg -q --fixed-strings "Date/time:" "$path" &&
       rg -q --fixed-strings "Timezone:" "$path" &&
       rg -q --fixed-strings "Old workspace modification statement:" "$path"; then
      printf 'template ok: %s\n' "$path"
    else
      printf 'template incomplete: %s\n' "$path"
      failed=1
    fi
  done

  if [[ "$failed" -eq 0 ]]; then
    pass "required evidence templates exist with migration metadata fields"
  else
    fail "required evidence templates are missing or incomplete"
  fi
}

check_catalog_sanity() {
  section "evidence catalog sanity"
  local path="evidence/indexes/evidence_catalog.md"
  local failed=0
  local needle
  local required=(
    "Evidence ID"
    "What it proves"
    "Curated manifest or artifact"
    "Raw output or archive reference"
    "reference"
    "verified"
    "superseded"
    "incident"
    "blocked"
  )

  if [[ ! -f "$path" ]]; then
    fail "evidence catalog is missing"
    return
  fi

  for needle in "${required[@]}"; do
    if rg -q --fixed-strings "$needle" "$path"; then
      printf 'catalog marker ok: %s\n' "$needle"
    else
      printf 'catalog marker missing: %s\n' "$needle"
      failed=1
    fi
  done

  if [[ "$failed" -eq 0 ]]; then
    pass "evidence catalog exposes the required review fields and statuses"
  else
    fail "evidence catalog is missing required review fields or statuses"
  fi
}

check_curated_root_catalog_coverage() {
  section "curated root catalog coverage"
  local catalog="evidence/indexes/evidence_catalog.md"
  local root path missing
  missing=""

  if [[ ! -f "$catalog" ]]; then
    fail "evidence catalog is missing for curated-root coverage"
    return
  fi

  while IFS= read -r root; do
    [[ -z "$root" ]] && continue
    path="evidence/curated_logs/$root/"
    if rg -q --fixed-strings "$path" "$catalog"; then
      printf 'cataloged curated root: %s\n' "$path"
    else
      missing+="$path"$'\n'
    fi
  done < <(find evidence/curated_logs -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | sort)

  if [[ -z "$missing" ]]; then
    pass "all retained curated evidence roots are named in the evidence catalog"
  else
    fail "retained curated evidence roots are missing from the evidence catalog"
    printf '%s' "$missing" | print_list
  fi
}

check_raw_log_leakage
check_evidence_runtime_pollution
check_raw_run_directories
check_evidence_top_level
check_report_home_shape
check_phase_report_home
check_template_inventory
check_catalog_sanity
check_curated_root_catalog_coverage

printf '\n'
if [[ "$failures" -eq 0 ]]; then
  echo "EVIDENCE VALIDATION PASSED"
else
  echo "EVIDENCE VALIDATION FAILED: $failures check group(s) failed"
fi

exit "$failures"
