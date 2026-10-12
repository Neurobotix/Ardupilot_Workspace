# GPS-Denied Paper Notes

Moved on 2026-10-12 from `docs/presentations/ekf_gps_denied/paper_notes.md`,
where it served the EKF deck. The two source PDFs are not stored in the
workspace; the SHA-256 values below identify them.

Research notes for the GPS-denied section of the EKF presentation. These
notes summarize only the two supplied primary sources. A statement under
**Reported** is a claim made by the paper; a statement under
**Interpretation** is our reading of the evidence and must not be presented as
the authors' result.

## Source and citation convention

1. Sky Seliquini, *Implementation of an Extended Kalman Filter Using Inertial
   Sensor Data for UAVs During GPS Denied Applications*, M.S. thesis, Old
   Dominion University, May 2022, DOI `10.25777/f3f4-b307`.
   Local source: `Implementation of an Extended Kalman Filter Using Inertial
   Sensor.pdf`; SHA-256
   `1db179f2cc95ea81301ee9d264b84f6e3bfedf64c86054e48de779034f0d816c`.
2. Xiaoyu Ye, Yifan Zeng, Qinghua Zeng, and Yijun Zou,
   “Airspeed-Aided State Estimation Algorithm of Small Fixed-Wing UAVs in
   GNSS-Denied Environments,” *Sensors*, vol. 22, no. 9, article 3156, 2022,
   DOI `10.3390/s22093156`.
   Local source: `Airspeed-Aided_State_Estimation_Algorithm_of_Small.pdf`;
   SHA-256
   `888cc6c659137bb0213e785239b5f9458304c9320f9ca2986347ea015fac24ec`.

For the thesis, `PDF p. N / thesis p. M` distinguishes the file page from the
number printed on the page. The main text begins on PDF page 14 as thesis page
1. For the *Sensors* article, PDF and printed page numbers are the same.

## Executive synthesis

### Reported across the two sources

- An IMU-only position estimate suffers from bias, scale-factor,
  misalignment, vibration, and integration-drift errors. In Seliquini's flight
  experiment, covariance tuning improved one recorded trajectory, but the
  tuned filter was ineffective on additional flights. The work concludes that
  a reliable GPS-denied solution needs more sensed measurements and a better
  representation of error states. [Seliquini, PDF pp. 91–100 / thesis
  pp. 78–87]
- Ye et al. add independent constraints from true airspeed, a magnetometer,
  and a barometer to inertial propagation. Their proposed cascade reports
  horizontal position error below 30 m after 30 s and below 50 m after 90 s,
  with 0.5 m average altitude error in the evaluated flight. [Ye et al., PDF
  pp. 13, 17]

### Interpretation

The strongest presentation story is not “choose a better filter.” It is:

> Once GNSS is removed, the estimator loses an absolute horizontal reference.
> Filtering the same inertial data cannot manufacture the missing information;
> another sensor or constraint must make the drifting states observable again.

The thesis supplies the failure case. The fixed-wing article supplies a
candidate constraint stack and bounded short-duration results. Neither source
proves indefinite, closed-loop GPS-denied autonomous navigation.

---

## Paper 1 — Seliquini thesis

### Research problem

**Reported.** The thesis asks whether a higher-quality external ADIS16475 IMU
and an EKF using the “MMM” sensor-fusion arrangement can estimate a
quadcopter's inertial position well enough to substitute artificial GPS data
for the autopilot during GPS loss, jamming, or spoofing. The intended
architecture is an external IMU feeding a companion-computer estimator, whose
position output is converted to latitude, longitude, and altitude and sent to
an ArduPilot-based autopilot with MAVLink `GPS_INPUT`. [Seliquini, PDF p. 3;
PDF pp. 17, 36, 90, 96–100 / thesis pp. 4, 23, 77, 83–87]

### State, process model, and measurements

**Reported state.** The filter uses a 15-element state:

\[
\mathbf{x}=
\begin{bmatrix}
\mathbf{s}&\mathbf{v}&\mathbf{a}&\boldsymbol{\delta}&\boldsymbol{\omega}
\end{bmatrix}^{T},
\]

where each bold term has three axes: position, velocity, acceleration,
attitude, and angular rate. [Seliquini, PDF pp. 41–43 / thesis pp. 28–30]

**Reported process model.** Translational propagation uses constant
acceleration,

\[
\mathbf{s}_k=\mathbf{s}_{k-1}+\Delta t\,\mathbf{v}_{k-1}
 +\tfrac12\Delta t^2\mathbf{a}_{k-1},\qquad
\mathbf{v}_k=\mathbf{v}_{k-1}+\Delta t\,\mathbf{a}_{k-1},
\]

with acceleration and angular rate held constant between samples. The
appendix implementation propagates attitude with the angular-rate states.
[Seliquini, PDF pp. 42–43 / thesis pp. 29–30; appendix code at PDF
pp. 120–121 / thesis pp. 107–108]

**Reported measurements.** Accelerometer and gyroscope readings are both
measurement updates, with no control input. The measurement Jacobian selects
only the acceleration states (elements 7–9) and angular-rate states (elements
13–15); position, velocity, and attitude are not directly measured by the
external IMU. Process- and measurement-noise Jacobians are identities. The
prior and posterior covariance matrices are initialized as identities.
[Seliquini, PDF pp. 41–43 / thesis pp. 28–30; appendix code at PDF
pp. 119–122 / thesis pp. 106–109]

**Interpretation.** This is a clean observability visual: six IMU channels
directly touch only 6 of 15 states. Position and velocity are produced through
integration, so the update has no independent absolute-position residual to
arrest their drift.

### Algorithm and implementation path

**Reported.** The processing path is:

1. calibrate the external accelerometer and estimate gyro bias from stationary
   data;
2. remove gravity and rotate body-frame acceleration/angular rate into the
   inertial frame using the current attitude estimate;
3. perform a covariance update with the 15-state filter;
4. tune the 15×15 process and measurement covariance matrices with simulated
   annealing against the Cube autopilot's GPS-aided navigation output; and
5. demonstrate, separately in SITL, that a MAVLink `GPS_INPUT` message can be
   accepted as an artificial GPS source. [Seliquini, PDF pp. 61, 92–100 /
   thesis pp. 48, 79–87; appendix code at PDF pp. 115–136 / thesis
   pp. 102–123]

The simulated-annealing cost is the sum of squared 3-D position differences
between the filter output and autopilot output. It was run four times for
30,000 iterations, retaining the best inputs every 100 iterations. Both noise
covariances began at `0.001 I(15)`. [Seliquini, PDF pp. 92–95 / thesis
pp. 79–82]

### Experimental setup

**Reported.** The test vehicle is an approximately 450-size quadcopter built
around a Cube Black/Pixhawk controller, Raspberry Pi 3B+ companion computer,
ADIS16475 six-DOF external IMU, Teensy 3.6 acquisition board, Here3 GNSS, and
telemetry radio. The external IMU logged at an average rate of about 300 Hz.
[Seliquini, PDF pp. 51–56 / thesis pp. 38–43; PDF p. 61 / thesis p. 48]

The flight path was a roughly rectangular four-waypoint trajectory, with
waypoints about 15 m apart at 15 m altitude, commanded speed 5 m/s, and a
10-second position hold at each waypoint. The path was deliberately not highly
nonlinear. Autopilot logs, including its GPS-aided fused navigation values,
served as the comparison reference. [Seliquini, PDF pp. 62–64 / thesis
pp. 49–51; PDF pp. 68–71 / thesis pp. 55–58]

The thesis first validates the filter on synthetic one-dimensional
constant-acceleration motion corrupted with Gaussian white noise, then applies
it post-flight to real IMU data. [Seliquini, PDF pp. 65–67, 90–91 / thesis
pp. 52–54, 77–78]

### Results actually reported

**Reported.** Untuned real-flight inertial integration produced physically
unusable velocity and position curves, reaching hundreds of metres per second
and kilometres of apparent displacement during an approximately 120-second
record. [Seliquini, Figures 35–36, PDF pp. 77–78 / thesis pp. 64–65]

**Reported.** After covariance tuning, the estimated trajectory followed the
shape of the GPS-aided autopilot trajectory more closely, but visible
discrepancies remained. The thesis provides plots rather than RMSE, MAE,
confidence intervals, or a summarized numerical position error. [Seliquini,
Figures 42–45, PDF pp. 84–87 / thesis pp. 71–74]

**Reported.** The improvement was specific to the flight trajectory used for
tuning and was ineffective for additional flights. The physical implementation
did not run the estimator in real time; the external-IMU data were
post-processed. MAVLink GPS substitution was only functionally demonstrated in
SITL. [Seliquini, PDF pp. 96–100 / thesis pp. 83–87]

**Reported conclusion.** The IMU-only state estimator was a “limited success.”
The thesis recommends, in order of claimed impact, adding measurements from
additional sensors, increasing acquisition rate, and using a more complete
calibration/error-state model. It explicitly concludes that a reliable
GPS-denied solution needs more sensed measurements and better error-state
representation. [Seliquini, PDF pp. 98–100 / thesis pp. 85–87]

### Quality, ambiguity, and limitations

- **No quantitative navigation score.** The thesis never reports an RMSE,
  terminal error, or repeatability statistic for the flight trajectory. A
  presentation must not infer a metre-level performance claim from Figure 45.
- **Training and evaluation are not separated.** The GPS-aided autopilot
  trajectory is used both to tune the covariance matrices and to judge the
  tuned output. The admitted failure on additional flights is evidence of
  trajectory-specific overfitting, not a general navigation solution.
  [Seliquini, PDF pp. 92–100 / thesis pp. 79–87]
- **Reference is not independent ground truth.** “Truth” is the Cube
  autopilot's own multi-sensor, GPS-aided estimate. [Seliquini, PDF
  pp. 92–93 / thesis pp. 79–80]
- **Not a closed-loop GPS-denied flight test.** The estimation and MAVLink
  injection demonstrations are separate. The appendix's `GPS_INPUT` example
  sends hard-coded coordinates, not live filter output. [Seliquini, PDF
  pp. 96–97 / thesis pp. 83–84; appendix code at PDF pp. 112–113 / thesis
  pp. 99–100]
- **The state model omits the main diagnosed errors.** Bias, scale factor, and
  misalignment are corrected outside the state or not modeled, although the
  discussion identifies them as root causes. [Seliquini, PDF pp. 91–92,
  98–100 / thesis pp. 78–79, 85–87]
- **Model/code inconsistencies.** Equation 42 prints attitude as
  `delta_t = T omega_(t-1)` without the previous attitude term, while the
  appendix transition matrix carries attitude forward. In the tuned script,
  velocity and attitude coupling terms use `dt/2`, unlike Equation 42 and the
  untuned script's `dt`. [Seliquini, PDF p. 42 / thesis p. 29; appendix code
  at PDF pp. 120–121 and 131 / thesis pp. 107–108 and 118]
- **Figure-label error.** Figures 24 and 25 have position/velocity plot titles
  that conflict with their captions. [Seliquini, PDF pp. 66–67 / thesis
  pp. 53–54]
- **Sample-rate explanation is weak.** The discussion attributes remaining
  integration drift largely to an inconsistent average rate of 300 Hz, while
  the conclusion also recommends a higher rate. The paper does not isolate
  rate irregularity from bias/model error experimentally. [Seliquini, PDF
  pp. 96, 99 / thesis pp. 83, 86]

### Safe and valuable presentation use

Use this paper as a **negative result with engineering value**, not as a
working GPS replacement:

- Safe: “A better IMU plus an EKF reduced noise, but did not create an
  absolute position reference.”
- Safe: “Tuning one recorded path made the plot look better; it failed to
  generalize to other flights.”
- Safe: “The authors' own conclusion was: add independent sensors and model
  the error states.”
- Unsafe: “The quadcopter flew autonomously without GPS using the proposed
  estimator.”
- Unsafe: quoting a numerical position accuracy from the thesis.

The strongest visual is a two-state comparison using the paper's own scales:
untuned double-integration exploding to kilometre-scale apparent displacement
versus the tuned, trajectory-specific path that still visibly departs from the
GPS-aided reference. Label both as post-processed.

---

## Paper 2 — Ye et al.

### Research problem

**Reported.** Ye et al. target a small fixed-wing UAV, for which high speed,
vibration, and a broad camera field of view make direct transfer of common
rotorcraft visual-navigation techniques difficult. Their goal is a low-cost,
low-computation state estimator for attitude, velocity, and position after
GNSS loss using sensors already practical on a fixed-wing aircraft. [Ye et
al., PDF pp. 1–3]

### Sensor set and cascade architecture

**Reported.** The proposed system is not one monolithic EKF. It is a cascade
using:

- three-axis gyroscope and accelerometer;
- three-axis magnetometer;
- pitot-tube true airspeed (TAS); and
- barometric pressure.

Gyroscope and accelerometer data are low-pass filtered; a second-order
tracking differentiator filters and differentiates airspeed and barometer
signals. The cascade then has an airspeed-aided nonlinear complementary
attitude filter, an adaptive horizontal-velocity complementary filter, and a
four-state linear Kalman filter for the vertical channel. [Ye et al., Figure
1 and Section 2, PDF pp. 4–10]

### Attitude and nongravitational-acceleration model

**Reported.** The earlier centripetal-only model estimates body-frame
nongravitational acceleration as

\[
\hat{\mathbf a}_{n}^{b}=\boldsymbol\omega_{ib}^{b}
\times\hat{\mathbf V}_{TAS}^{b}.
\]

Ye et al. add the differentiated TAS term to represent linear acceleration:

\[
\hat{\mathbf a}^{b}=\boldsymbol\omega_{ib}^{b}
\times\hat{\mathbf V}_{TAS}^{b}
+\frac{d\hat{\mathbf V}_{TAS}^{b}}{dt}.
\]

This estimated external acceleration is used to avoid treating all measured
specific force as gravity during maneuvers. [Ye et al., Equations 1–6, PDF
pp. 4–6]

The paper maps the difference between predicted nongravitational acceleration
and measured specific force into a horizontal attitude-misalignment
correction. That relationship has rank two, so heading is not observable from
it; yaw is separately corrected with the magnetometer. A PI feedback term is
applied to gyro integration in a quaternion-based nonlinear complementary
filter. [Ye et al., Equations 7–19, PDF pp. 6–8]

**Interpretation.** This is a strong observability example: airspeed plus the
dynamics recover two attitude-error directions, while yaw still requires a
different reference. One sensor does not repair every missing state.

### Horizontal velocity and position

**Reported.** Inertial velocity is integrated from transformed specific
force. A complementary update gradually pulls east/north inertial velocity
toward an airspeed-derived local-frame velocity. Its gain is zero until a
time threshold `t0`, then transitions smoothly toward gain `G`; the test uses
`t0 = 30 s`, `t1 = 10`, `G = 1`, and a listed TAS complementary-filter gain
of 0.9. [Ye et al., Equations 20–23, PDF p. 8; Table 4, PDF p. 12]

**Interpretation.** This adaptive weighting embodies a useful presentation
principle: trust short-term inertial propagation first; as its error grows,
shift weight toward an independent, non-integrating constraint.

### Vertical-channel Kalman filter

**Reported state.** The only explicit Kalman-filter state vector in the
proposed cascade is

\[
\mathbf X(t)=
\begin{bmatrix}
\delta v_U & \delta v_{baro} & \delta H_{INS} & \delta H_{baro}
\end{bmatrix}^{T}.
\]

It models inertial vertical-velocity/height error and correlated barometer
vertical-rate/height error as first-order Markov processes. The observation
is the difference between inertial and barometric vertical rate and height,
with closed-loop corrections applied to inertial vertical velocity and
altitude. [Ye et al., Equations 24–30, PDF pp. 9–10]

The selected parameters are `Q = diag([0.1, 0.5, 0.1, 2])^2`,
`R = diag([1, 10])^2`, and
`P0 = diag([0.1, 1, 0.1, 10])^2`; the table lists feedback gains 0.2 for lift
rate and 0.8 for altitude, although both rows are labeled `K1`. [Ye et al.,
Table 4, PDF p. 12]

### Assumptions

**Reported.** The method:

- neglects transport and Earth-rate terms over the short flight span;
- assumes accelerometer measurement error is negligible in its external-
  acceleration relation;
- sets the unobservable vertical-axis attitude-misalignment component to
  zero in the two-direction acceleration correction;
- ignores sideslip, arguing that a 10-degree sideslip would introduce about
  1.52% velocity error;
- approximates angle of attack from pitch and flight-path angle; and
- says the wind effect is ignored because the tested small aircraft is not
  suited to high wind and wind is difficult to estimate. [Ye et al., PDF
  pp. 5–9]

### Experimental setup

**Reported.** The aircraft is a 6.9 kg electric fixed-wing UAV with 2.1 m
wingspan and 1.62 m body length. The flight-control computer is an OMAP-L138
C6000 target generated from MATLAB/Simulink. The ADIS16488B supplies gyro,
accelerometer, magnetometer, and barometer data; the experiment's maximum wind
speed is reported as 3 m/s. Sample period is 0.005 s. [Ye et al., PDF
pp. 10–12]

The vehicle performed turns, circling, climb, and descent. The proposed
TAS/INS/barometer output was stored in the flight log. GNSS/INS remained the
navigation source in the UAV control loop and was treated as truth for the
error comparisons. The competing offline solutions were ACF, airspeed-aided
EKF (`EKF/TAS`), and centripetal-only nonlinear complementary filtering
(`NCF/TAS`). [Ye et al., PDF pp. 11–12]

### Quantitative results actually reported

**Reported attitude over the evaluated interval.** Proposed-filter MAE/RMSE:

| Axis | MAE | RMSE | EKF/TAS MAE | EKF/TAS RMSE |
| --- | ---: | ---: | ---: | ---: |
| Roll | 1.1388° | 1.4195° | 1.2389° | 1.5633° |
| Pitch | 1.1114° | 1.4672° | 1.8450° | 3.1493° |
| Yaw | 4.7935° | 5.5443° | 7.0168° | 8.4507° |

The paper attributes the weaker yaw result to magnetometer calibration and
electromagnetic disturbance. It also reports that a descent around 200 s made
the centripetal-only models' pitch error rise rapidly, with an instantaneous
maximum near 11°. [Ye et al., Table 5 and surrounding text, PDF pp. 13–14]

**Reported navigation.** Horizontal velocity error is within 2 m/s; maximum
vertical-rate error is 0.5 m/s; horizontal position error is below 30 m after
30 s (about 600 m flown) and below 50 m after 90 s (about 1800 m flown); and
average altitude error is 0.5 m. The paper notes that north-position error is
worse than ACF and NCF/TAS during part of the flight, linking this to a roll
error from wind disturbance. [Ye et al., PDF pp. 13–14, 17]

**Reported computation benchmark.** For 200 s of data at 0.005 s steps on a
3.2 GHz AMD Ryzen 7 5800H using MATLAB 2021A: ACF takes 4.2402 s (2.12% of
real time), EKF/TAS 12.6251 s (6.31%), NCF/TAS 6.4150 s (3.21%), and the
proposed cascade 8.1774 s (4.09%). [Ye et al., Table 6, PDF p. 17]

### Quality, ambiguity, and limitations

- **No closed-loop GNSS-denied control proof.** The proposed algorithm was
  deployed/logged, but GNSS/INS remained in the navigation control loop and
  supplied the reference. The comparative results were produced offline.
  [Ye et al., PDF pp. 11–12]
- **Limited condition coverage.** The paper presents one described flight
  sequence and reports maximum wind of 3 m/s. It gives no repetitions,
  uncertainty intervals, or sensitivity sweep. The result should be qualified
  as this evaluated flight, not a general guarantee.
- **Wind-model ambiguity.** Section 2.1 explicitly says wind is ignored, yet
  Equation 21 includes east/north wind terms without explaining how they are
  obtained. This matters because the paper later identifies wind-driven roll
  error as a source of position error. [Ye et al., PDF pp. 5, 8, 14]
- **Airspeed is not ground speed.** The approach is most credible in the
  low-wind test regime. Its horizontal correction can inherit wind and heading
  error; the paper's own curves and discussion show this coupling.
- **Altitude result needs careful wording.** The barometer specification table
  lists about 40 m absolute measurement error and about 0.2 m noise, while the
  fused result reports 0.5 m average error against GNSS/INS. This supports
  short-term relative tracking in the evaluated flight, not necessarily
  0.5 m absolute altitude accuracy everywhere. [Ye et al., Table 1, PDF p. 9;
  PDF pp. 13, 17]
- **Time-window language is inconsistent.** The paper reports 30- and
  90-second GPS-denied errors, while Figure 11's caption calls the displayed
  tracks “190 s long” even though the plotted result interval in Figures 6–10
  is approximately 130–220 s. Avoid calling the entire GPS-denied interval
  190 s. [Ye et al., PDF pp. 13–16]
- **Data are not public.** The article states that data are available only on
  request and withheld publicly because of project confidentiality. [Ye et
  al., PDF p. 18]
- **Desktop timing is not embedded timing.** The computation comparison is an
  offline MATLAB benchmark on a Ryzen laptop CPU, not a reported timing trace
  from the OMAP target. [Ye et al., PDF p. 17]
- **Table typo/ambiguity.** Table 4 labels both vertical feedback coefficients
  `K1`, although the surrounding equation uses `K1` and `K2`. [Ye et al., PDF
  pp. 10, 12]

### Safe and valuable presentation use

- Safe: “Airspeed supplies a non-integrating speed constraint, not absolute
  position.”
- Safe: “Barometer constrains the vertical channel; magnetometer constrains
  yaw; each sensor restores different information.”
- Safe with test qualifier: “In one low-wind fixed-wing flight, the reported
  horizontal error stayed below 30 m at 30 s and below 50 m at 90 s.”
- Safe: “The error still grew; this was improved dead reckoning, not permanent
  position lock.”
- Unsafe: “Airspeed replaces GPS.”
- Unsafe: “The paper demonstrated closed-loop autonomous flight with GNSS
  removed.”
- Unsafe: transferring these results directly to a multicopter; the model and
  constraints are fixed-wing specific.

The best visual is a sensor-to-state constraint map:

```text
gyro + accel ──> short-term propagation
      TAS ─────> horizontal speed + maneuver acceleration
      mag ─────> yaw reference
     baro ─────> altitude + climb-rate reference
```

Animate the constraints arriving one at a time and show the corresponding
uncertainty axis stop expanding. Do not show TAS as a direct position sensor.

---

## Cross-paper comparison

| Question | Seliquini thesis | Ye et al. |
| --- | --- | --- |
| Vehicle | Quadcopter | 6.9 kg fixed-wing |
| GPS-denied estimator inputs | External 6-DOF IMU only | IMU + TAS + magnetometer + barometer |
| Main filter structure | 15-state IMU-measurement filter | Cascade complementary filters + 4-state vertical KF |
| Absolute horizontal reference | None | None |
| Horizontal stabilizing constraint | None | Airspeed-derived velocity |
| Evaluation truth | GPS-aided Cube estimate | GNSS/INS estimate |
| Real-time estimator in test | No; post-processed | Algorithm deployed/logged, comparisons offline |
| Closed-loop GNSS-denied flight | No | No |
| Quantitative position result | Not reported | <30 m at 30 s; <50 m at 90 s in one low-wind flight |
| Central lesson | IMU-only tuning does not generalize | Extra constraints slow drift but do not provide permanent position lock |

## Recommended deck sequence

These sources support a five-slide GPS-denied bridge after the current
observability/drift slides:

1. **GPS Was More Than A Dot On The Map** — animate removal of GNSS position
   and velocity residuals; covariance expands specifically in the states that
   lose their absolute reference.
2. **Attempt 1: Filter The IMU Harder** — use the thesis as a real failure
   case. Toggle raw integration → trajectory-tuned estimate → another flight,
   ending on “better fit ≠ restored observability.”
3. **Add Information, Not Confidence** — interactive sensor-to-state map:
   TAS→speed, barometer→height, magnetometer→yaw. The point is complementary
   observability, not sensor count.
4. **Airspeed-Aided Dead Reckoning** — animate Ye et al.'s cascade:
   propagation → TAS/magnetometer corrections → vertical KF. Include a visible
   wind switch to show that TAS and ground speed separate as wind rises.
5. **How Long Is The Estimate Useful?** — time ruler with the paper's bounded
   points: 30 s / <30 m and 90 s / <50 m, accompanied by “one low-wind
   fixed-wing flight; GNSS/INS used as reference.” End with the engineering
   question: what error budget and outage duration does the mission allow?

This order moves smoothly from mechanism, to failed attempt, to restored
constraints, to measured performance, and finally to mission-level design.

