"""Generate assets/models/shahin_e/model.sdf for the GPS-denied navigation study.

Every number traces to
governance/runbooks/features/gps_denied_navigation/shahin_e_model_sources.md

Run from the workspace root:  python scripts/dev/gen_shahin_e_model.py
Only the two KNOBs may change during Gate 3 calibration; sign flips only at Gate 1.
"""
import math
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "assets" / "models" / "shahin_e" / "model.sdf"

# ---------------- inputs (see model_sources.md) ----------------
MASS = 11.0                     # kg, middle of 9-13 (engineers)
IXX, IYY, IZZ = 1.4, 1.2, 2.5   # kg m^2, estimate (sources sec. 3)
SPAN, AREA = 2.5, 0.63          # engineers
CHORD = AREA / SPAN             # 0.252 m, rectangular wing (photos)
WING_Z = 0.08                   # high wing above CG (photos)
ROOT, FLAP, AIL = 0.27, 0.53, 0.45   # half-span split: root / flap / aileron (engineers)
INNER = ROOT + FLAP             # 0.80 m inner panel (root + flap)
CLA_W = round(2 * math.pi * (SPAN**2 / AREA) / (SPAN**2 / AREA + 2), 2)  # 3D lift slope
A0_W = 0.116                    # KNOB 1 initial: pitch 4.1 deg at 17 m/s, 11 kg (calm-window target)
CDA_W = 0.60                    # drag slope: L/D ~ 8.6 at cruise (assumption, glide-checked later)
ALPHA_STALL_W = 0.25            # CLmax ~1.3
HT_SPAN, HT_CHORD, HT_X = 0.60, 0.15, -1.00     # estimate from photos
VT_H, VT_CHORD, VT_X, VT_Z = 0.33, 0.20, -1.05, 0.235
HT_AREA_HALF = HT_SPAN * HT_CHORD / 2
VT_AREA = VT_H * VT_CHORD
CLA_HT = round(2 * math.pi * (HT_SPAN**2 / (2*HT_AREA_HALF)) / (HT_SPAN**2 / (2*HT_AREA_HALF) + 2), 2)
A0_HT = -0.06                   # approximates wing downwash at the tail
MOTOR_Y, MOTOR_X, MOTOR_Z = 0.30, 0.19, 0.06    # wing leading edge, next to fuselage (photos)
MOTOR_MULT = 1310               # KNOB 2 initial: rad/s at full throttle -> ~54% at cruise
SMALL = 0.01                    # mass of each control-surface link
MOTOR_MASS = 0.025
BASE_MASS = round(MASS - 7 * SMALL - 2 * MOTOR_MASS - 0.001, 3)   # 7 control-surface links

def box(name, size, pose, color="0.6 0.6 0.6 1", collision=False):
    kind = "collision" if collision else "visual"
    mat = "" if collision else f"<material><ambient>{color}</ambient><diffuse>{color}</diffuse></material>"
    fr = ("<surface><friction><ode><mu>0.05</mu><mu2>0.05</mu2></ode></friction></surface>" if collision else "")
    return (f'      <{kind} name="{name}"><pose>{pose}</pose><geometry><box><size>{size}</size></box></geometry>'
            f'{mat}{fr}</{kind}>\n')

def sphere_col(name, r, pose):
    return (f'      <collision name="{name}"><pose>{pose}</pose><geometry><sphere><radius>{r}</radius></sphere></geometry>'
            '<surface><friction><ode><mu>0.05</mu><mu2>0.05</mu2></ode></friction></surface></collision>\n')

def tiny_inertial(m=SMALL):
    return (f"      <inertial><mass>{m}</mass><inertia><ixx>1e-5</ixx><ixy>0</ixy><ixz>0</ixz>"
            "<iyy>1e-5</iyy><iyz>0</iyz><izz>1e-5</izz></inertia></inertial>\n")

def surface_link(name, pose, size):
    return (f'    <link name="{name}_link">\n      <pose>{pose}</pose>\n{tiny_inertial()}'
            + box(f"{name}_visual", size, "0 0 0 0 0 0", "0.8 0.3 0.2 1") + "    </link>\n")

def revolute(name, axis, lo=-0.7, hi=0.7):
    return (f'    <joint name="{name}_joint" type="revolute">\n      <parent>base_link</parent><child>{name}_link</child>\n'
            f'      <axis><xyz>{axis}</xyz><limit><lower>{lo}</lower><upper>{hi}</upper></limit>'
            '<dynamics><damping>0.01</damping></dynamics></axis>\n    </joint>\n')

def pos_controller(name):
    return (f'    <plugin filename="gz-sim-joint-position-controller-system" name="gz::sim::systems::JointPositionController">\n'
            f'      <joint_name>{name}_joint</joint_name><initial_position>0.0</initial_position>\n'
            f'      <topic>/shahin_e/{name}_joint/cmd_pos</topic><p_gain>10</p_gain><i_gain>0</i_gain><d_gain>0</d_gain>\n'
            '      <i_max>1</i_max><i_min>-1</i_min><cmd_max>5</cmd_max><cmd_min>-5</cmd_min>\n    </plugin>\n')

def liftdrag(comment, cp, area, cla, a0, cda, stall, upward="0 0 1", link="base_link", forward="1 0 0",
             control=None, rad_to_cl=None, cla_stall=-3.85, cda_stall=-0.9233984055):
    s = (f'    <!-- {comment} -->\n    <plugin filename="gz-sim-lift-drag-system" name="gz::sim::systems::LiftDrag">\n'
         f'      <a0>{a0}</a0><cla>{cla}</cla><cda>{cda}</cda><cma>0</cma>\n'
         f'      <alpha_stall>{stall}</alpha_stall><cla_stall>{cla_stall}</cla_stall><cda_stall>{cda_stall}</cda_stall><cma_stall>0</cma_stall>\n'
         f'      <cp>{cp}</cp><area>{round(area, 4)}</area><air_density>1.2041</air_density>\n'
         f'      <forward>{forward}</forward><upward>{upward}</upward><link_name>{link}</link_name>\n')
    if control:
        s += f'      <control_joint_name>{control}</control_joint_name><control_joint_rad_to_cl>{rad_to_cl}</control_joint_rad_to_cl>\n'
    return s + "    </plugin>\n"

def motor(side, y):
    n = f"{side}_motor"
    return (f'    <link name="{n}_link">\n      <pose degrees="true">{MOTOR_X} {y} {MOTOR_Z} 0 90 0</pose>\n'
            f'      <inertial><mass>{MOTOR_MASS}</mass><inertia><ixx>9.75e-06</ixx><ixy>0</ixy><ixz>0</ixz>'
            '<iyy>0.000166704</iyy><iyz>0</iyz><izz>0.000167604</izz></inertia></inertial>\n'
            '      <visual name="prop_visual"><geometry><cylinder><radius>0.18</radius><length>0.005</length></cylinder></geometry>'
            '<material><ambient>0.1 0.1 0.1 0.6</ambient><diffuse>0.1 0.1 0.1 0.6</diffuse></material></visual>\n'
            f'    </link>\n    <joint name="{n}_joint" type="revolute">\n      <pose degrees="true">0 0 0 0 180 0</pose>\n'
            f'      <parent>base_link</parent><child>{n}_link</child>\n'
            '      <axis><xyz>0 0 1</xyz><limit><lower>-1.0e+16</lower><upper>1.0e+16</upper></limit>'
            '<dynamics><damping>0.004</damping></dynamics></axis>\n    </joint>\n'
            + liftdrag(f"{side} propeller blade A (copied from Mini Talon)", "0.084 0 0", 0.02, 4.25, 0.3, 0.10, 1.4,
                       link=f"{n}_link", forward="0 -1 0", cla_stall=-0.025, cda_stall=0.0)
            + liftdrag(f"{side} propeller blade B (copied from Mini Talon)", "-0.084 0 0", 0.02, 4.25, 0.3, 0.10, 1.4,
                       link=f"{n}_link", forward="0 1 0", cla_stall=-0.025, cda_stall=0.0))

def control(channel, joint, mult, offset, smin, smax, servo_note, kind="COMMAND"):
    s = (f'      <!-- {servo_note} -->\n      <control channel="{channel}">\n        <jointName>{joint}</jointName>\n'
         f'        <multiplier>{mult}</multiplier><offset>{offset}</offset>\n'
         f'        <servo_min>{smin}</servo_min><servo_max>{smax}</servo_max>\n')
    if kind == "COMMAND":
        s += f'        <type>COMMAND</type><cmd_topic>/shahin_e/{joint}/cmd_pos</cmd_topic>\n'
    else:
        s += ('        <type>VELOCITY</type><p_gain>0.20</p_gain><i_gain>0</i_gain><d_gain>0</d_gain>'
              '<i_max>1</i_max><i_min>-1</i_min><cmd_max>5.0</cmd_max><cmd_min>-5.0</cmd_min>\n')
    return s + "      </control>\n"

def off(trim, smin, smax):
    return round(-(trim - smin) / (smax - smin), 4)

ail_y = ROOT + FLAP + AIL / 2
flap_y = ROOT + FLAP / 2
te_x = 0.063 - CHORD

out = []
out.append(f'''<?xml version="1.0"?>
<sdf version="1.9">
  <!--
    Shahin-E (electric, twin tractor motors) for the GPS-denied navigation study.
    Generated by scripts/dev/gen_shahin_e_model.py (do not hand-edit). Every number is listed with its source in
    governance/runbooks/features/gps_denied_navigation/shahin_e_model_sources.md
    Origin = CG. x forward, y left, z up.
    Calibration knobs (the only values tuned at Gate 3):
      KNOB 1: <a0> of the four wing panels   (now {A0_W})
      KNOB 2: <multiplier> of both motors     (now {MOTOR_MULT})
  -->
  <model name="shahin_e">
    <link name="base_link">
      <enable_wind>true</enable_wind>
      <inertial><pose>0 0 0 0 0 0</pose><mass>{BASE_MASS}</mass>
        <inertia><ixx>{IXX}</ixx><ixy>0</ixy><ixz>0</ixz><iyy>{IYY}</iyy><iyz>0</iyz><izz>{IZZ}</izz></inertia>
      </inertial>
''')
out.append(box("fuselage_visual", "1.80 0.14 0.14", "-0.25 0 0 0 0 0", "0.35 0.38 0.42 1"))
out.append(box("wing_visual", f"{CHORD:.3f} {SPAN} 0.03", f"{0.063 - CHORD/2:.4f} 0 {WING_Z} 0 0 0", "0.55 0.57 0.6 1"))
out.append(box("htail_visual", f"{HT_CHORD} {HT_SPAN} 0.01", f"{HT_X - HT_CHORD/4:.4f} 0 0 0 0 0", "0.55 0.57 0.6 1"))
out.append(box("fin_visual", f"{VT_CHORD} 0.01 {VT_H}", f"{VT_X - VT_CHORD/4:.4f} 0 {VT_Z} 0 0 0", "0.3 0.33 0.38 1"))
out.append(box("fuselage_collision", "1.80 0.14 0.14", "-0.25 0 0 0 0 0", collision=True))
out.append(sphere_col("nose_gear_collision", 0.04, "0.55 0 -0.22 0 0 0"))
out.append(sphere_col("left_main_gear_collision", 0.04, "-0.08 0.25 -0.22 0 0 0"))
out.append(sphere_col("right_main_gear_collision", 0.04, "-0.08 -0.25 -0.22 0 0 0"))
out.append('''      <sensor name="imu_sensor" type="imu">
        <pose degrees="true">0 0 0 180 0 0</pose><always_on>1</always_on><update_rate>1000.0</update_rate>
      </sensor>
      <sensor name="navsat_sensor" type="navsat"><always_on>1</always_on><update_rate>1</update_rate></sensor>
    </link>

    <link name="pitot_link">
      <enable_wind>true</enable_wind>
      <pose>0.70 0 0 0 0 0</pose>
      <inertial><mass>0.001</mass><inertia><ixx>1e-7</ixx><ixy>0</ixy><ixz>0</ixz><iyy>1e-7</iyy><iyz>0</iyz><izz>1e-7</izz></inertia></inertial>
      <sensor name="air_speed_sensor" type="air_speed">
        <always_on>1</always_on><update_rate>50</update_rate><topic>/airspeed</topic>
        <air_speed><pressure><noise type="gaussian"><mean>0</mean><stddev>0.0</stddev></noise></pressure></air_speed>
      </sensor>
    </link>
    <joint name="pitot_joint" type="fixed"><parent>base_link</parent><child>pitot_link</child></joint>

''')
# control-surface links + joints
for side, sgn in (("left", 1), ("right", -1)):
    out.append(surface_link(f"{side}_aileron", f"{te_x:.4f} {sgn*ail_y:.4f} {WING_Z} 0 0 0", f"0.06 {AIL} 0.01"))
    out.append(revolute(f"{side}_aileron", "0 1 0"))
    out.append(surface_link(f"{side}_flap", f"{te_x:.4f} {sgn*flap_y:.4f} {WING_Z} 0 0 0", f"0.06 {FLAP} 0.01"))
    out.append(revolute(f"{side}_flap", "0 1 0"))
    out.append(surface_link(f"{side}_elevator", f"{HT_X - 0.1:.3f} {sgn*0.165:.3f} 0 0 0 0", "0.05 0.25 0.01"))
    out.append(revolute(f"{side}_elevator", "0 1 0"))
out.append(surface_link("rudder", f"{VT_X - 0.15:.3f} 0 {VT_Z} 0 0 0", "0.07 0.01 0.25"))
out.append(revolute("rudder", "0 0 1"))
out.append(motor("left", MOTOR_Y))
out.append(motor("right", -MOTOR_Y))
out.append('    <plugin filename="gz-sim-joint-state-publisher-system" name="gz::sim::systems::JointStatePublisher"></plugin>\n')
for n in ("left_aileron", "right_aileron", "left_flap", "right_flap", "left_elevator", "right_elevator", "rudder"):
    out.append(pos_controller(n))

# aerodynamic surfaces
for side, sgn in (("left", 1), ("right", -1)):
    out.append(liftdrag(f"{side} inner wing panel (root + flap), {INNER} m", f"0 {sgn*INNER/2:.3f} {WING_Z}",
                        INNER * CHORD, CLA_W, A0_W, CDA_W, ALPHA_STALL_W, control=f"{side}_flap_joint", rad_to_cl=-1.8))
    out.append(liftdrag(f"{side} outer wing panel (aileron), {AIL} m", f"0 {sgn*(INNER + AIL/2):.3f} {WING_Z}",
                        AIL * CHORD, CLA_W, A0_W, CDA_W, ALPHA_STALL_W, control=f"{side}_aileron_joint", rad_to_cl=-1.5))
for side, sgn in (("left", 1), ("right", -1)):
    out.append(liftdrag(f"{side} horizontal tail + elevator", f"{HT_X} {sgn*HT_SPAN/4:.3f} 0", HT_AREA_HALF, CLA_HT,
                        A0_HT, 0.10, 0.30, control=f"{side}_elevator_joint", rad_to_cl=-1.8))
out.append(liftdrag("vertical fin + rudder", f"{VT_X} 0 {VT_Z}", VT_AREA, 3.0, 0.0, 0.10, 0.30, upward="0 1 0",
                    control="rudder_joint", rad_to_cl=-1.5))

# ArduPilot bridge: channel = SERVOn - 1, ranges copied from Shahin params
out.append('''    <plugin name="ArduPilotPlugin" filename="ArduPilotPlugin">
      <fdm_addr>127.0.0.1</fdm_addr><fdm_port_in>9002</fdm_port_in>
      <connectionTimeoutMaxCount>5</connectionTimeoutMaxCount><lock_step>1</lock_step><have_32_channels>0</have_32_channels>
      <modelXYZToAirplaneXForwardZDown>0 0 0 3.141593 0 0</modelXYZToAirplaneXForwardZDown>
      <gazeboXYZToNED>0 0 0 3.141593 0 1.57079632</gazeboXYZToNED>
      <imuName>base_link::imu_sensor</imuName>
      <airspeed_topic>/airspeed</airspeed_topic>
''')
out.append(control(0, "left_aileron_joint", 1.0471976, off(1554, 1100, 1900), 1100, 1900, "SERVO1 Aileron 1100-1900 trim 1554 REVERSED 1 (assumed left)"))
out.append(control(5, "right_aileron_joint", 1.0471976, off(1426, 900, 2150), 900, 2150, "SERVO6 Aileron 900-2150 trim 1426 REVERSED 0 (assumed right)"))
out.append(control(1, "left_elevator_joint", 1.0471976, off(1433, 800, 2200), 800, 2200, "SERVO2 Elevator 800-2200 trim 1433"))
out.append(control(6, "right_elevator_joint", 1.0471976, off(1433, 800, 2200), 800, 2200, "SERVO7 Elevator 800-2200 trim 1433"))
out.append(control(2, "left_flap_joint", 0.7, -1.0, 1300, 1800, "SERVO3 Flap 1300-1800 REVERSED 1: 1800 = retracted, 1300 = full (0.7 rad down)"))
out.append(control(7, "right_flap_joint", 0.7, -1.0, 1300, 1800, "SERVO8 Flap 1300-1800 REVERSED 1"))
out.append(control(4, "rudder_joint", -1.0471976, off(1500, 950, 2200), 950, 2200, "SERVO5 Rudder 950-2200 trim 1500; sign flipped at Gate 1 (2026-10-13): yaw right gave +joint = nose left"))
out.append(control(10, "left_motor_joint", MOTOR_MULT, 0, 1100, 2000, "SERVO11 Throttle Left 1100-2000", kind="VELOCITY"))
out.append(control(11, "right_motor_joint", MOTOR_MULT, 0, 1100, 2000, "SERVO12 Throttle Right 1100-2000", kind="VELOCITY"))
out.append("    </plugin>\n  </model>\n</sdf>\n")
OUT.write_text("".join(out))
print("wrote", OUT)
print("CLA_W", CLA_W, "CLA_HT", CLA_HT, "base mass", BASE_MASS, "chord", CHORD)
print("Vh", round(2*HT_AREA_HALF*abs(HT_X)/(AREA*CHORD),3), "Vv", round(VT_AREA*abs(VT_X)/(AREA*SPAN),4))
