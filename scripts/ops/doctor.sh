#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

"$ROOT/scripts/maintenance/validate_structure.sh"
"$ROOT/scripts/maintenance/validate_evidence.sh"
