"""thrust_camera.json (camera_thrust.py) -> KukriRhythm.h DualThrust camera curve (30 Hz on the AUTHOR clock, degrees).

R7 ran the clip at the reference's own pace (author time = reference time x TIME_SCALE, the combo's base play rate).
R8 (user: "slow the thrust a little") stretches the clip's phases (author_dual_attack.THRUST): WARP maps each R8 author
time onto the R7 one piecewise linearly between the phase boundaries, so the camera's lunge drift, the jolt at the hit
and the return stay on the same beats of the arm motion.  Values are the direct fits to the stance frame 2525 (84.167 s); the two
burst frames 2537-2538 that keep only 20-28 inliers are replaced by the mean of their neighbours.  Scaling:
  yaw x0.75, pitch x0.92, roll x1 -- the screen-equivalent scaling of the accepted kukri swing curves (curve_atk1.py)
  before the impact the player lunges ~2-3 m at the dummy: the zoom-in (FOV -7) and the downward pitch (-9) of that
  stretch are mostly the dolly (the 15-30 m scenery expands and rises in the frame); the game lunges 1 m for real
  (KukriRhythm::DualThrustLungeCM), so that stretch keeps half its FOV and half its pitch
  from the impact on: the camera jolt -- a hard turn left (-7), the view punched wide (+10..+12 FOV) and a clockwise /
  counter-clockwise roll rattle -- is kept in full; the roll rattle after the first jolt is smoothed (3-tap) because the
  confirmed hit adds its own damped shake (KukriRhythm::HitShake x DualThrustHitRoll)
After 0.44 s (reference) the direct fits drift with the player's own aim (pitch -5..-8 while the arms are gone), so the
curve fades to zero by RETURN_END and stays at the stance.
"""
import json
import os

import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025"
TIME_SCALE = 38 / 30 / 0.8          # author s per reference s (KukriRhythm::AttackSeconds / attack_seconds 0.8)
LENGTH = 2.05                       # DualAttack3 author length (R8)
IMPACT_REF = 0.300                  # reference s after the stance frame (2534)
# R8 author s -> R7 author s at the phase boundaries (in, coil, drive, impact, press, settle, drop, hang, end).
WARP = ((0.0, 0.0), (0.22, 0.18), (0.50, 0.42), (0.60, 0.475), (0.66, 0.52), (0.84, 0.68), (1.00, 0.82), (1.14, 0.95),
        (2.05, 1.85))
RETURN = (0.44, 0.62)               # reference s: fade window
data = json.load(open(os.path.join(d, "thrust_camera.json")))
frames = {f['frame']: f for f in data['frames']}
start = data['clip_start']
# The direct fits (camera_thrust.py prints them; recomputed here from the json's direct entries and the listed values).
DIRECT = {  # frame: yaw, pitch, roll, fov  (direct fits to 2525)
    2525: (0, 0, 0, 0), 2526: (1.10, -1.10, -1.24, -1.62), 2527: (1.87, -2.54, -2.58, -2.98), 2528: (2.31, -4.92, -3.82, -4.44),
    2529: (2.59, -7.46, -4.87, -5.67), 2530: (2.68, -8.62, -5.30, -5.83), 2531: (2.69, -9.14, -5.30, -6.17),
    2532: (3.26, -9.22, -2.83, -7.38), 2533: (0.38, -9.35, -0.62, -6.73), 2534: (-6.91, -4.55, -5.32, 9.68),
    2535: (-4.11, -1.05, 3.58, 11.68), 2536: (-3.26, -3.93, 1.21, 7.14), 2539: (-4.15, -0.54, -1.38, 1.13),
    2540: (-2.81, -2.09, 2.78, 1.41), 2541: (-2.09, -3.44, 0.63, 1.90), 2542: (-2.08, -5.11, 0.18, 1.87),
}
# 2537-2538: 20-28 inliers in the burst -> neighbours' mean.
DIRECT[2537] = tuple(np.array(DIRECT[2536]) * 2 / 3 + np.array(DIRECT[2539]) / 3)
DIRECT[2538] = tuple(np.array(DIRECT[2536]) / 3 + np.array(DIRECT[2539]) * 2 / 3)
ref_t = np.array(sorted((f - start) / 30 for f in DIRECT))
ref_v = np.array([DIRECT[start + int(round(t * 30))] for t in ref_t])
SCALE = np.array([.75, .92, 1.0, 1.0])
N = int(round(LENGTH * 30)) + 1
out = np.zeros((N, 4))
for i in range(N):
    tr = np.interp(i / 30, *zip(*WARP)) / TIME_SCALE           # reference seconds
    if tr > RETURN[1]:
        continue
    v = np.array([np.interp(tr, ref_t, ref_v[:, k]) for k in range(4)]) * SCALE
    if tr < IMPACT_REF - 1e-6:
        v[1] *= 0.5                                            # lunge stretch: half the dolly-driven pitch and FOV
        v[3] *= 0.5
    if tr > RETURN[0]:
        x = (tr - RETURN[0]) / (RETURN[1] - RETURN[0])
        v *= 1 - x * x * (3 - 2 * x)
    out[i] = v
# Roll rattle after the first jolt: 3-tap smoothing (the hit adds its own shake).
new_t, old_t = zip(*WARP)
imp = int(round(np.interp(IMPACT_REF * TIME_SCALE, old_t, new_t) * 30))   # the R8 impact sample (0.60 s)
roll = out[:, 2].copy()
for i in range(imp + 1, N - 1):
    out[i, 2] = 0.25 * roll[i - 1] + 0.5 * roll[i] + 0.25 * roll[i + 1]
out[0] = 0
out[-1] = 0
names = ('DualThrustYaw', 'DualThrustPitch', 'DualThrustRoll', 'DualThrustFov')
print('    inline constexpr int32 DualThrustSamples=%d;' % N)
for k, n in enumerate(names):
    print('    inline constexpr float %s[DualThrustSamples]={%s};' % (n, ','.join('%.2ff' % v for v in out[:, k])))
for k, n in enumerate(names):
    i, j = int(np.argmax(out[:, k])), int(np.argmin(out[:, k]))
    print('// %s max %.2f at %.3f s, min %.2f at %.3f s (author)' % (n, out[i, k], i / 30, out[j, k], j / 30))
