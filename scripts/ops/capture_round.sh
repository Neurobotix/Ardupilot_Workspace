#!/usr/bin/env bash
# Decode one Phase 2 smoke-target tlog into a bounded runtime summary.
#
# Default output is working review material under var/. Reviewed promotion into
# evidence/ is explicit so a decoded tlog summary is not mistaken for a report.
#
# Usage:
#   scripts/ops/capture_round.sh <target>
#   scripts/ops/capture_round.sh --promote-reviewed --evidence-id <id> <target>

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

usage() {
  echo "usage: capture_round.sh <target>" >&2
  echo "       capture_round.sh --promote-reviewed --evidence-id <id> <target>" >&2
}

MODE="working"
EVIDENCE_ID=""
while [[ "$#" -gt 0 ]]; do
  case "$1" in
    --promote-reviewed)
      MODE="promoted"
      shift
      ;;
    --evidence-id)
      EVIDENCE_ID="${2:-}"
      if [[ -z "$EVIDENCE_ID" ]]; then
        echo "ERROR: --evidence-id requires a non-empty ID." >&2
        usage
        exit 2
      fi
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --*)
      echo "ERROR: unknown option '$1'." >&2
      usage
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

if [[ "$#" -ne 1 ]]; then
  usage
  exit 2
fi
TARGET="$1"

if [[ "$MODE" == "promoted" && -z "$EVIDENCE_ID" ]]; then
  echo "ERROR: reviewed promotion requires --evidence-id for a new catalog/report record." >&2
  usage
  exit 2
fi
if [[ "$MODE" == "working" && -n "$EVIDENCE_ID" ]]; then
  echo "ERROR: --evidence-id is only valid with --promote-reviewed." >&2
  usage
  exit 2
fi
if [[ -n "$EVIDENCE_ID" && ! "$EVIDENCE_ID" =~ ^[a-z0-9][a-z0-9_-]*$ ]]; then
  echo "ERROR: evidence ID must use lowercase letters, digits, underscores, or hyphens." >&2
  exit 2
fi

PY="$ROOT/env/bin/python3"
DUMP="$ROOT/env/bin/mavlogdump.py"
STAMP="$(date '+%Y%m%dT%H%M%S%z')"
if [[ "$MODE" == "promoted" ]]; then
  OUTDIR="$ROOT/evidence/curated_logs/phase_2_runtime_2026-05-20"
  OUT="$OUTDIR/${TARGET}_evidence_${EVIDENCE_ID}_${STAMP}.txt"
  SUMMARY_KIND="curated reviewed summary"
else
  OUTDIR="$ROOT/var/working/runtime_capture"
  OUT="$OUTDIR/${TARGET}_capture_${STAMP}.txt"
  SUMMARY_KIND="working runtime capture"
fi

mkdir -p "$OUTDIR"
if [[ "$MODE" == "promoted" && -e "$OUT" ]]; then
  echo "ERROR: refusing to replace existing curated artifact: ${OUT#$ROOT/}" >&2
  echo "Use a new evidence ID/output path and update the report/catalog record." >&2
  exit 1
fi

TLOG="$(find "$ROOT/var/logs/mavproxy/$TARGET" -name 'flight.tlog' -printf '%T@ %p\n' 2>/dev/null \
  | sort -nr | head -1 | cut -d' ' -f2-)"

if [[ -z "${TLOG:-}" || ! -f "$TLOG" ]]; then
  echo "ERROR: no flight.tlog found under var/logs/mavproxy/$TARGET" >&2
  echo "Run the '$TARGET' smoke target first." >&2
  exit 1
fi

dump() { "$PY" "$DUMP" --types "$1" "$TLOG" 2>/dev/null; }

{
  echo "# Phase 2 runtime $SUMMARY_KIND: $TARGET"
  echo
  echo "Captured: $(date '+%Y-%m-%dT%H:%M:%S%z')"
  if [[ "$MODE" == "promoted" ]]; then
    echo "Evidence ID: $EVIDENCE_ID"
  fi
  echo "Source tlog (raw, under var/, disposable):"
  echo "  ${TLOG#$ROOT/}"
  echo "tlog size: $(du -h "$TLOG" | cut -f1)"
  echo
  echo "## Handshake proof"
  echo "HEARTBEAT messages received: $(dump HEARTBEAT | grep -c HEARTBEAT || echo 0)"
  echo "First HEARTBEAT:"
  dump HEARTBEAT | head -1 | sed 's/^/  /'
  echo "Last HEARTBEAT:"
  dump HEARTBEAT | tail -1 | sed 's/^/  /'
  echo
  echo "## GPS fix"
  echo "Last GPS_RAW_INT:"
  dump GPS_RAW_INT | tail -1 | sed 's/^/  /'
  echo
  echo "## Boot / EKF / arming status messages"
  dump STATUSTEXT | grep -iE 'ArduPlane|ArduCopter|Ready|EKF3|GPS 1|armed|origin set|Calibrat' \
    | sed 's/^/  /' | head -40
  echo
  echo "## Altitude / speed (proves Gazebo physics coupling)"
  echo "Max relative_alt (mm):"
  dump GLOBAL_POSITION_INT | grep -oE 'relative_alt : -?[0-9]+' | awk '{print $3}' \
    | sort -n | tail -1 | sed 's/^/  /'
  echo "Max VFR_HUD groundspeed (m/s):"
  dump VFR_HUD | grep -oE 'groundspeed : [0-9.]+' | awk '{print $3}' \
    | sort -n | tail -1 | sed 's/^/  /'
  echo
  echo "## End of runtime summary for $TARGET"
} > "$OUT"

if [[ "$MODE" == "promoted" ]]; then
  echo "Reviewed curated summary written: ${OUT#$ROOT/}"
  echo "Update the dated report and evidence catalog for evidence ID '$EVIDENCE_ID'."
else
  echo "Working capture written: ${OUT#$ROOT/}"
  echo "Review before promotion. Use --promote-reviewed with a new --evidence-id only for selected proof."
fi
echo "---"
cat "$OUT"
