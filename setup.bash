#!/usr/bin/env bash
# Source this file: source /home/ahmed/ardupilot_workspace_next/setup.bash

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ARDUPILOT_WORKSPACE="$WORKSPACE"

export ARDUPILOT_HOME="$WORKSPACE/src/ardupilot"
if [ -d "$ARDUPILOT_HOME/Tools/autotest" ]; then
  export PATH="$ARDUPILOT_HOME/Tools/autotest:$PATH"
fi

export GZ_SIM_RESOURCE_PATH="\
$WORKSPACE/assets/models:\
$WORKSPACE/assets/worlds:\
$WORKSPACE/src/SITL_Models/Gazebo/models:\
$WORKSPACE/src/SITL_Models/Gazebo/worlds:\
$WORKSPACE/src/ardupilot_gazebo/models:\
$WORKSPACE/src/ardupilot_gazebo/worlds:\
/usr/local/share/ardupilot_gazebo/models:\
/usr/local/share/ardupilot_gazebo/worlds"

# Workspace policy forbids falling back to an installed Gazebo plugin build.
export GZ_SIM_SYSTEM_PLUGIN_PATH="$WORKSPACE/build/ardupilot_gazebo"
export ARDUPILOT_BUILD="$WORKSPACE/build"
export ARDUPILOT_LOGS="$WORKSPACE/var/logs"
export CCACHE_DIR="$WORKSPACE/var/cache/ccache"
export MPLCONFIGDIR="$WORKSPACE/var/cache/matplotlib"
export PYTHONPATH="$WORKSPACE/src:$WORKSPACE/src/sim_ard_gaw/compat_scripts${PYTHONPATH:+:$PYTHONPATH}"

mkdir -p "$CCACHE_DIR" "$MPLCONFIGDIR" "$ARDUPILOT_LOGS"

if [ -f "$WORKSPACE/env/bin/activate" ]; then
  # shellcheck source=/dev/null
  source "$WORKSPACE/env/bin/activate"
fi

alias wsnext='cd "$ARDUPILOT_WORKSPACE"'
alias wslaunch='"$ARDUPILOT_WORKSPACE/scripts/ops/launch.sh"'

echo "ArduPilot workspace_next loaded"
echo "  Workspace: $ARDUPILOT_WORKSPACE"
echo "  Assets:    $ARDUPILOT_WORKSPACE/assets"
echo "  Runtime:   $ARDUPILOT_WORKSPACE/src/sim_ard_gaw"
echo "  Logs:      $ARDUPILOT_WORKSPACE/var/logs"
echo "  Cache:     $ARDUPILOT_WORKSPACE/var/cache"
