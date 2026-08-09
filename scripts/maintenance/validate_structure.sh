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

check_required_homes() {
  section "required top-level homes"
  local missing=0
  local item kind path
  for item in \
    "file:README.md" \
    "file:setup.bash" \
    "dir:governance" \
    "dir:docs" \
    "dir:.ai" \
    "dir:src" \
    "dir:assets" \
    "dir:config" \
    "dir:tests" \
    "dir:evidence" \
    "dir:scripts" \
    "dir:var" \
    "dir:.private"
  do
    kind="${item%%:*}"
    path="${item#*:}"
    if [[ "$kind" == "file" && -f "$path" ]]; then
      printf 'ok:   %s\n' "$path"
    elif [[ "$kind" == "dir" && -d "$path" ]]; then
      printf 'ok:   %s/\n' "$path"
    else
      printf 'miss: %s\n' "$path"
      missing=1
    fi
  done

  if [[ "$missing" -eq 0 ]]; then
    pass "all required top-level homes exist"
  else
    fail "one or more required top-level homes are missing"
  fi
}

check_broken_symlinks() {
  section "broken symlinks"
  local output
  output="$(find -L . -path './.git' -prune -o -type l -print 2>/dev/null | sort)"
  if [[ -z "$output" ]]; then
    pass "no broken symlinks"
  else
    fail "broken symlinks found"
    printf '%s\n' "$output" | print_list
  fi
}

check_raw_log_leakage() {
  section "raw log leakage"
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
    pass "no raw .BIN/.bin/.tlog/.tlog.raw files outside allowed ignored/runtime areas"
  else
    fail "raw log files leaked outside allowed ignored/runtime areas"
    printf '%s\n' "$output" | print_list
  fi
}

check_nested_private() {
  section "nested .private directories"
  local output
  output="$(
    find assets config docs evidence governance scripts src tests .ai \
      -path '*/.private' -print -o -path '*/.private/*' -print 2>/dev/null | sort
  )"
  if [[ -z "$output" ]]; then
    pass "no nested .private directories under active homes"
  else
    fail "nested .private content found under active homes"
    printf '%s\n' "$output" | print_list
  fi
}

check_private_policy() {
  section ".private policy"
  local policy_failed=0
  local private_markdown disallowed_markdown duplicate_headings hidden_instructions
  local canonical_headings private_heading canonical_links_without_pointer runnable_logic

  if [[ -d ".private/docs" ]]; then
    fail ".private/docs exists"
    policy_failed=1
  fi

  if [[ -d ".private/scripts" ]]; then
    fail ".private/scripts exists"
    policy_failed=1
  fi

  disallowed_markdown="$(
    while IFS= read -r private_markdown; do
      [[ "$private_markdown" == ".private/README.md" ]] && continue
      [[ "$private_markdown" == .private/notes/*.md ]] && continue
      printf '%s\n' "$private_markdown"
    done < <(find .private -type f -name '*.md' -print 2>/dev/null | sort)
  )"

  if [[ -n "$disallowed_markdown" ]]; then
    fail ".private Markdown is outside the explicit allowlist"
    printf '%s\n' "$disallowed_markdown" | print_list
    policy_failed=1
  fi

  canonical_headings="$(
    find README.md CHANGELOG.md docs governance .ai \
      \( -path 'docs/archive' -o -path 'docs/archive/*' \
      -o -path 'governance/audits' -o -path 'governance/audits/*' \
      -o -path '.ai/audits' -o -path '.ai/audits/*' \) -prune -o \
      -type f -name '*.md' -print0 2>/dev/null |
      xargs -0 awk '/^#+[[:space:]]+/ { sub(/^#+[[:space:]]+/, ""); print }' |
      sort -u
  )"

  duplicate_headings="$(
    while IFS= read -r private_markdown; do
      [[ "$private_markdown" == ".private/README.md" ]] && continue
      while IFS= read -r private_heading; do
        if printf '%s\n' "$canonical_headings" | grep -Fxq "$private_heading"; then
          printf '%s: duplicate heading: %s\n' "$private_markdown" "$private_heading"
        fi
      done < <(awk '/^#+[[:space:]]+/ { sub(/^#+[[:space:]]+/, ""); print }' "$private_markdown")
    done < <(find .private -type f -name '*.md' -print 2>/dev/null | sort)
  )"

  if [[ -n "$duplicate_headings" ]]; then
    fail ".private notes duplicate canonical document headings"
    printf '%s\n' "$duplicate_headings" | print_list
    policy_failed=1
  fi

  hidden_instructions="$(
    while IFS= read -r private_markdown; do
      [[ "$private_markdown" == ".private/README.md" ]] && continue
      rg -n '(^```|^cd[[:space:]]|^source[[:space:]]|^make[[:space:]]|^scripts/|^param[[:space:]]|^[A-Z0-9_]+=[^`])' "$private_markdown" 2>/dev/null |
        sed "s|^|$private_markdown:|"
    done < <(find .private/notes -type f -name '*.md' -print 2>/dev/null | sort)
  )"

  if [[ -n "$hidden_instructions" ]]; then
    fail ".private notes contain command-like canonical procedure content"
    printf '%s\n' "$hidden_instructions" | print_list
    policy_failed=1
  fi

  canonical_links_without_pointer="$(
    while IFS= read -r private_markdown; do
      [[ "$private_markdown" == ".private/README.md" ]] && continue
      if rg -q '`?(README.md|docs/|governance/|scripts/|src/|config/|assets/|tests/|evidence/)`?' "$private_markdown"; then
        if ! rg -qi 'pointer|promoted to|points to|see canonical' "$private_markdown"; then
          printf '%s\n' "$private_markdown"
        fi
      fi
    done < <(find .private/notes -type f -name '*.md' -print 2>/dev/null | sort)
  )"

  if [[ -n "$canonical_links_without_pointer" ]]; then
    fail ".private notes link canonical homes without being marked as pointers"
    printf '%s\n' "$canonical_links_without_pointer" | print_list
    policy_failed=1
  fi

  runnable_logic="$(
    find .private -type f \
      \( -perm -111 -o -name '*.sh' -o -name '*.py' -o -name '*.pl' -o -name '*.rb' \
      -o -name '*.js' -o -name '*.ts' -o -name 'Makefile' \) \
      -print 2>/dev/null | sort
  )"

  if [[ -n "$runnable_logic" ]]; then
    fail ".private contains runnable logic"
    printf '%s\n' "$runnable_logic" | print_list
    policy_failed=1
  fi

  if [[ "$policy_failed" -eq 0 ]]; then
    pass ".private contains only allowed local pointer notes and no runnable logic"
  fi
}

check_gitignore() {
  section "gitignore coverage"
  local path
  local failed=0
  for path in \
    ".private/config/plane_params.local.parm" \
    "var/logs/example.BIN" \
    "var/runs/example.tlog" \
    "var/cache/example.tmp" \
    "src/ardupilot/example.txt" \
    "src/SITL_Models/example.txt"
  do
    if git check-ignore -q -- "$path"; then
      printf 'ignored: %s\n' "$path"
    else
      printf 'not ignored: %s\n' "$path"
      failed=1
    fi
  done

  if [[ "$failed" -eq 0 ]]; then
    pass "required runtime, private, and external dependency paths are ignored"
  else
    fail "required gitignore coverage is missing"
  fi
}

check_stale_references() {
  section "stale canonical references"
  local files matches disallowed allowed
  local entry file line text label
  mapfile -t files < <(
    find README.md docs governance .ai \
      \( -path 'docs/archive' -o -path 'docs/archive/*' \
      -o -path 'governance/audits' -o -path 'governance/audits/*' \
      -o -path '.ai/audits' -o -path '.ai/audits/*' \) -prune -o \
      -type f \( -name '*.md' -o -name '*.txt' \) -print 2>/dev/null | sort
  )

  matches="$(
    {
      rg -n --pcre2 '/home/ahmed/ardupilot_workspace(?!_next)' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::old absolute production workspace path/'
      rg -n --fixed-strings -e 'src/SIM_ARD_GAW' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::legacy compatibility path/'
      rg -n --fixed-strings -e 'logs/flights' -e 'src/SIM_ARD_GAW/logs' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::old log home/'
      rg -n --pcre2 '(^|[^[:alnum:]_])logs/[0-9]{3}_[^[:space:]`)]*' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::old numbered log home/'
      rg -n --fixed-strings -e 'plane_lidar_runway.sdf' -e 'wind_altitude_log_check.py' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::retired script or world/'
      rg -n --fixed-strings -e 'wind-check-altitude' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::retired launch target/'
      rg -n --pcre2 'READY FOR CUTOVER|WORKING|VERIFIED|workspace_next is production|treat this workspace as production' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::deprecated production claim/'
      rg -n --fixed-strings -e 'ARSPD_TYPE=100 in plane_base' -- "${files[@]}" 2>/dev/null |
        sed 's/$/:::obsolete parameter claim/'
    } || true
  )"

  disallowed=""
  allowed=""
  while IFS= read -r entry; do
    [[ -z "$entry" ]] && continue
    label="${entry##*:::}"
    entry="${entry%:::*}"
    file="${entry%%:*}"
    line="${entry#*:}"
    line="${line%%:*}"
    text="${entry#*:}"
    text="${text#*:}"

    if reason="$(allowed_stale_reference_reason "$file" "$text" "$label")"; then
      allowed+="$file:$line: $label: $reason: $text"$'\n'
    else
      disallowed+="$file:$line: $label: $text"$'\n'
    fi
  done <<< "$matches"

  if [[ -n "$allowed" ]]; then
    echo "allowed exceptions:"
    printf '%s' "$allowed" | sort -u | print_list
  fi

  if [[ -z "$disallowed" ]]; then
    pass "no disallowed stale canonical references in non-archive docs/governance/AI"
  else
    fail "disallowed stale canonical references found"
    printf '%s' "$disallowed" | sort -u | print_list
  fi
}

allowed_stale_reference_reason() {
  local file="$1"
  local text="$2"
  local label="$3"

  allow_exact "$file" "$label" "$text" \
    "README.md" \
    "old absolute production workspace path" \
    'Deprecated fallback/reference: `/home/ahmed/ardupilot_workspace`.' \
    "documents the ADR-0005 deprecated fallback workspace" && return 0

  allow_exact "$file" "$label" "$text" \
    ".ai/current.md" \
    "old absolute production workspace path" \
    'under `.private/`. The old workspace `/home/ahmed/ardupilot_workspace` is' \
    "records the ADR-0005 deprecated fallback workspace" && return 0

  allow_exact "$file" "$label" "$text" \
    ".ai/current.md" \
    "old absolute production workspace path" \
    '- Phase 0 production reference was `/home/ahmed/ardupilot_workspace`; after' \
    "records the Phase 0 reference superseded by ADR-0005" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/decisions/ADR-0005-workspace-next-cutover.md" \
    "old absolute production workspace path" \
    'production workspace and whether `/home/ahmed/ardupilot_workspace` can move from' \
    "ADR-0005 context for the deprecated fallback workspace" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/decisions/ADR-0005-workspace-next-cutover.md" \
    "old absolute production workspace path" \
    'Move `/home/ahmed/ardupilot_workspace` to deprecated fallback/reference status.' \
    "ADR-0005 decision for the deprecated fallback workspace" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/operations/workspace_cutover_rollback.md" \
    "old absolute production workspace path" \
    '`/home/ahmed/ardupilot_workspace` is deprecated fallback/reference, not active' \
    "rollback guidance after ADR-0005 cutover" && return 0

  allow_exact "$file" "$label" "$text" \
    "README.md" \
    "old absolute production workspace path" \
    'Production source: `/home/ahmed/ardupilot_workspace`.' \
    "documents the read-only production reference" && return 0

  allow_exact "$file" "$label" "$text" \
    ".ai/current.md" \
    "old absolute production workspace path" \
    '- Production reference remains `/home/ahmed/ardupilot_workspace`.' \
    "records the Phase 0 production reference" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/onboarding/quick_start.md" \
    "old absolute production workspace path" \
    '`/home/ahmed/ardupilot_workspace/env/bin/python3`.' \
    "documents the temporary production virtualenv fallback" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/operations/launch_targets.md" \
    "old absolute production workspace path" \
    '  `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help`' \
    "documents Phase 2 read-only production launch-surface comparison command" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/full_migration_plan.md" \
    "old absolute production workspace path" \
    'and make `/home/ahmed/ardupilot_workspace` a deprecated reference/archive.' \
    "states the migration deprecation target" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "old absolute production workspace path" \
    '/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help' \
    "Phase 2 read-only production launch-surface comparison command" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "old absolute production workspace path" \
    '    `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help`' \
    "Phase 2 read-only production launch-surface comparison command" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "old absolute production workspace path" \
    'Do not edit `/home/ahmed/ardupilot_workspace`.' \
    "Phase 2 explicitly forbids editing the production reference" && return 0

  allow_exact "$file" "$label" "$text" \
    ".ai/issues/open.md" \
    "legacy compatibility path" \
    '- Production nested `src/SIM_ARD_GAW` is dirty with 115 status entries.' \
    "records a Phase 0 production dirty-state blocker" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/operations/launch_targets.md" \
    "legacy compatibility path" \
    '  `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help`' \
    "documents Phase 2 read-only production launch-surface comparison command" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/full_migration_plan.md" \
    "legacy compatibility path" \
    '| 8 | Compatibility Retirement | Remove legacy compatibility paths safely | No runtime depends on `src/SIM_ARD_GAW` |' \
    "defines the compatibility retirement exit gate" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_8_compatibility_retirement.md" \
    "legacy compatibility path" \
    '1. Inventory `src/SIM_ARD_GAW/{config,models,worlds,missions,scripts,logs}`,' \
    "Phase 8 compatibility inventory task" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_8_compatibility_retirement.md" \
    "legacy compatibility path" \
    '   dependencies: `src/SIM_ARD_GAW`, `SIM_ARD_GAW_DIR`, `compat_scripts`,' \
    "Phase 8 dependency scan task" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_8_compatibility_retirement.md" \
    "legacy compatibility path" \
    '6. Remove `src/SIM_ARD_GAW` compatibility links only when no runtime code,' \
    "Phase 8 retirement order" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_8_compatibility_retirement.md" \
    "legacy compatibility path" \
    '`src/SIM_ARD_GAW` may be removed only when:' \
    "Phase 8 removal gate" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_8_compatibility_retirement.md" \
    "legacy compatibility path" \
    '- remaining compatibility-reference scan for `src/SIM_ARD_GAW`,' \
    "Phase 8 validation scan" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_8_compatibility_retirement.md" \
    "legacy compatibility path" \
    'the old-workspace modification statement, whether `src/SIM_ARD_GAW` still' \
    "Phase 8 evidence contract" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "legacy compatibility path" \
    '/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help' \
    "Phase 2 read-only production launch-surface comparison command" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "legacy compatibility path" \
    '    `/home/ahmed/ardupilot_workspace/src/SIM_ARD_GAW/scripts/launch.sh help`' \
    "Phase 2 read-only production launch-surface comparison command" && return 0

  allow_exact "$file" "$label" "$text" \
    ".ai/issues/open.md" \
    "retired launch target" \
    '- `wind-check-altitude` retired until a real validator is implemented.' \
    "tracks retired launch-target follow-up" && return 0

  allow_exact "$file" "$label" "$text" \
    ".ai/current.md" \
    "retired launch target" \
    '  difference: `wind-check-altitude` is retired in `workspace_next`.' \
    "records Phase 2 retired-target result" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/operations/launch_targets.md" \
    "retired launch target" \
    '- `wind-check-altitude` is retired because the historical target referenced a' \
    "documents retired target status" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/operations/launch_targets.md" \
    "retired launch target" \
    '  `wind-check-altitude` behavior change described below.' \
    "documents Phase 2 target-surface difference" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/operations/launch_targets.md" \
    "retired launch target" \
    '| `wind-check-altitude` | PASS for retired behavior | Exits with code 2 and explains the target is retired. |' \
    "records Phase 2 retired-target evidence" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "retired launch target" \
    '- Verify `wind-check-altitude` is intentionally retired and documented.' \
    "Phase 2 parity task for retired target" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "retired launch target" \
    '- Verify `wind-check-altitude` is intentionally retired and returns a' \
    "Phase 2 retired-target behavior check" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/runbooks/migration/phase_2_runtime_parity.md" \
    "retired launch target" \
    'scripts/ops/launch.sh wind-check-altitude' \
    "Phase 2 minimum validation command for retired target" && return 0

  allow_exact "$file" "$label" "$text" \
    "README.md" \
    "deprecated production claim" \
    'Do not treat this workspace as production until the shadow parity checklist in' \
    "explicitly says this workspace is not production" && return 0

  allow_exact "$file" "$label" "$text" \
    "governance/standards/change_control.md" \
    "deprecated production claim" \
    'Do not write `WORKING`, `VERIFIED`, or `READY FOR CUTOVER` without a dated' \
    "evidence rule preventing unsupported readiness claims" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/architecture/simulation_lanes.md" \
    "retired launch target" \
    '  `./launch.sh wind-check-altitude`. That target is **retired** in' \
    "Phase 3 errata qualifying the retired altitude-wind scoring target" && return 0

  allow_exact "$file" "$label" "$text" \
    "docs/architecture/simulation_lanes.md" \
    "retired script or world" \
    '  production validator `wind_altitude_log_check.py` did not exist. Do not rely' \
    "Phase 3 errata explaining why wind-check-altitude is retired" && return 0

  return 1
}

allow_exact() {
  local actual_file="$1"
  local actual_label="$2"
  local actual_text="$3"
  local expected_file="$4"
  local expected_label="$5"
  local expected_text="$6"
  local reason="$7"

  if [[ "$actual_file" == "$expected_file" &&
        "$actual_label" == "$expected_label" &&
        "$actual_text" == "$expected_text" ]]; then
    printf '%s\n' "$reason"
    return 0
  fi

  return 1
}

check_workspace_status_links() {
  section "workspace-status links"
  local required_refs=(
    "governance/standards/change_control.md"
    "docs/operations/workspace_status.md"
  )
  local required_sources=(
    "README.md"
    ".ai/index.md"
    ".ai/current.md"
    "docs/onboarding/quick_start.md"
    "docs/operations/workspace_status.md"
  )
  local failed=0
  local path source

  for path in "${required_refs[@]}"; do
    if [[ -f "$path" ]]; then
      printf 'target ok: %s\n' "$path"
    else
      printf 'target missing: %s\n' "$path"
      failed=1
    fi
  done

  for source in "${required_sources[@]}"; do
    if [[ ! -f "$source" ]]; then
      printf 'source missing: %s\n' "$source"
      failed=1
      continue
    fi
    for path in "${required_refs[@]}"; do
      if rg -q --fixed-strings "$path" "$source"; then
        printf 'ref ok: %s -> %s\n' "$source" "$path"
      else
        printf 'ref missing: %s -> %s\n' "$source" "$path"
        failed=1
      fi
    done
  done

  if [[ "$failed" -eq 0 ]]; then
    pass "required workspace-status targets and entry-point references exist"
  else
    fail "required workspace-status targets or entry-point references are missing"
  fi
}

check_naming_policy_guidance() {
  section "naming policy guidance"
  local failed=0
  local path
  local required=(
    "governance/standards/naming.md"
    "docs/README.md"
    ".ai/README.md"
    "governance/runbooks/README.md"
    "governance/runbooks/features/README.md"
    "governance/audits/README.md"
    "evidence/reports/README.md"
    "evidence/templates/README.md"
    "evidence/indexes/README.md"
    "scripts/README.md"
    "tests/README.md"
  )

  for path in "${required[@]}"; do
    if [[ -f "$path" ]] && rg -qi --fixed-strings "naming" "$path"; then
      printf 'naming guidance ok: %s\n' "$path"
    else
      printf 'naming guidance missing or incomplete: %s\n' "$path"
      failed=1
    fi
  done

  if [[ "$failed" -eq 0 ]]; then
    pass "required naming policy and directory guidance files exist"
  else
    fail "required naming policy or directory guidance is missing"
  fi
}

check_required_homes
check_broken_symlinks
check_raw_log_leakage
check_nested_private
check_private_policy
check_gitignore
check_stale_references
check_workspace_status_links
check_naming_policy_guidance

printf '\n'
if [[ "$failures" -eq 0 ]]; then
  echo "STRUCTURE VALIDATION PASSED"
else
  echo "STRUCTURE VALIDATION FAILED: $failures check group(s) failed"
fi

exit "$failures"
