# Test Result: Airspeed Sensor Integration

> Historical note:
> This file captures the initial implementation snapshot.
> For the current end-to-end validation status, use
> `logs/007_Plane_Airspeed_FollowUp/TEST_RESULT_2026-04-02.md`.

---
test_id: 003_Plane_Airspeed
date: 2026-02-04
vehicle: Mini Talon with Airspeed
status: IMPLEMENTATION_COMPLETE
tested_by: Documentation Review
---

## Summary

Airspeed sensor integration for the Mini Talon aircraft has been **fully implemented**.

---

## Implementation Verification

### ✅ Model Created: `mini_talon_with_airspeed`

**Location**: `src/SIM_ARD_GAW/models/mini_talon_with_airspeed/`

**Airspeed Sensor Configuration** (lines 325-340 of model.sdf):
```xml
<sensor name="air_speed_sensor" type="air_speed">
  <pose degrees="true">0.15 0 0 0 0 0</pose>
  <always_on>1</always_on>
  <update_rate>50</update_rate>
  <topic>/airspeed</topic>
  <air_speed>
    <pressure>
      <noise type="gaussian">
        <mean>0</mean>
        <stddev>0.01</stddev>
      </noise>
    </pressure>
  </air_speed>
</sensor>
```

**ArduPilotPlugin Integration** (line 946):
```xml
<airspeed_topic>/airspeed</airspeed_topic>
```

---

### ✅ World Created: `mini_talon_wind_runway.sdf`

**Location**: `src/SIM_ARD_GAW/worlds/mini_talon_wind_runway.sdf`

**Wind Effects System** (native Gazebo Harmonic plugin):
- `gz-sim-wind-effects-system` enabled
- Sinusoidal wind magnitude variation (period: 60s, amplitude: 5%)
- Sinusoidal wind direction variation (period: 20s, amplitude: 5°)
- Gaussian noise on all axes
- Runtime control via gz topic

**Model Include**:
```xml
<include>
  <pose degrees="true">0 0 0.2 0 0 90</pose>
  <uri>model://mini_talon_with_airspeed</uri>
  <enable_wind>true</enable_wind>
</include>
```

---

### ✅ Bridge Script Created: `airspeed_bridge.py`

**Location**: `src/SIM_ARD_GAW/scripts/airspeed_bridge.py`

**Features**:
- Subscribes to Gazebo `/airspeed` topic (AirSpeed message)
- Converts differential pressure to airspeed
- Sends to ArduPilot via MAVLink SCALED_PRESSURE
- Configurable port and update rate
- Graceful shutdown handling

---

## Components Summary

| Component | Status | Location |
|-----------|--------|----------|
| `mini_talon_with_airspeed` model | ✅ Created | `models/mini_talon_with_airspeed/` |
| `air_speed` sensor (50Hz) | ✅ Added | model.sdf lines 325-340 |
| ArduPilotPlugin `<airspeed_topic>` | ✅ Configured | model.sdf line 946 |
| `mini_talon_wind_runway.sdf` | ✅ Created | `worlds/` |
| `gz-sim-wind-effects-system` | ✅ Enabled | world file |
| `airspeed_bridge.py` | ✅ Created | `scripts/` |

---

## Implementation Details

Uses native Gazebo Harmonic components:
- Native `air_speed` sensor type (built into Gazebo Harmonic 9.5.0)
- Native `gz-sim-wind-effects-system` for wind simulation
- Python bridge for Gazebo → MAVLink communication

---

## Next Steps: Flight Testing Required

1. **Start SITL with airspeed enabled**:
   ```bash
   cd ~/ardupilot_workspace/src/SIM_ARD_GAW
   ./scripts/launch.sh plane-airspeed
   ```

2. **Start Gazebo with wind world**:
   ```bash
   ./scripts/launch.sh gazebo-plane-wind
   ```

3. **Run airspeed bridge**:
   ```bash
   python3 scripts/airspeed_bridge.py
   ```

4. **Verify airspeed in MAVProxy**:
   ```
   watch VFR_HUD.airspeed
   ```

5. **Test with dynamic wind**:
   ```bash
   gz topic -t "/world/mini_talon_wind_runway/wind/" -m gz.msgs.Wind \
     -p "linear_velocity:{x:10, y:0, z:0}, enable_wind:true"
   ```

---

## Notes

- Flight testing with varying wind conditions still pending
