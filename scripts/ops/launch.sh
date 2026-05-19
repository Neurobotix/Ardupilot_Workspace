#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export ARDUPILOT_WORKSPACE="${ARDUPILOT_WORKSPACE:-$ROOT}"
exec "$ROOT/src/sim_ard_gaw/launch/launch.sh" "$@"
