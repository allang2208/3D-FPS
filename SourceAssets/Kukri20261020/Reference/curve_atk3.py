"""atk3_camera.json ('far' entries, contact_atk3.py) -> KukriRhythm.h stab camera curve (stage 3, V12).

Same convention as the accepted first-hit and diagonal curves: the per-frame registration is scaled like the first
curve was against its own registration (yaw x0.75, pitch x0.92, roll x1, fov x0.75) and 3-tap smoothed
([.25 .5 .25]); roll gets a 5-tap binomial ([1 4 6 4 1]/16) because the reference's confirmed-hit roll rattle
(about -7/+6/-8 deg on consecutive frames 0.33-0.47 s) survives the 3-tap filter as a 4 deg wobble; our swing curve also plays on misses, and a confirmed hit adds its own damped shake
(KukriRhythm::HitShake, with the stab's larger roll gain).  The reference ends ~0.4 deg off its start (the player has
moved), so the curve is faded out over 0.95-1.17 s and the stance samples are zero.  The clip is 38/30 s (the arm
keeps the first hit's re-raise timing); the curve is back at zero from 1.2 s, the shared 39-sample length.

The lunge (the dummy grows ~2.5x over 0.25-0.33 s: the player covers ~2 m) is not a rotation; it is approximated by a
short camera push along the view (StabPush, cm) on top of the measured FOV widening.  Prints the C++ arrays."""
import json
import os

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
data = json.load(open(os.path.join(d, "atk3_camera.json")))
far = {round(f['t'] * 30): f for f in data['far']}
N = 39
CLIP = 36
SCALE = dict(yaw=.75, pitch=.92, roll=1.0, fov=.75)
NAMES = dict(yaw='StabYaw', pitch='StabPitch', roll='StabRoll', fov='StabFov')


def smoothstep(a, b, x):
    u = min(max((x - a) / (b - a), 0.0), 1.0)
    return u * u * (3 - 2 * u)


out = {}
for k, s in SCALE.items():
    raw = [far[i][k] * s if i in far and i <= CLIP else 0.0 for i in range(N)]
    raw[0] = 0.0
    if k == 'roll':
        pad = [0.0, 0.0] + raw + [0.0, 0.0]
        sm = [(pad[i] + 4 * pad[i + 1] + 6 * pad[i + 2] + 4 * pad[i + 3] + pad[i + 4]) / 16 for i in range(N)]
    else:
        sm = [raw[0]] + [.25 * raw[i - 1] + .5 * raw[i] + .25 * raw[i + 1] for i in range(1, N - 1)] + [0.0]
    sm = [v * (1.0 - smoothstep(0.95, 1.167, i / 30)) for i, v in enumerate(sm)]
    sm[0] = 0.0
    for i in range(CLIP, N):
        sm[i] = 0.0
    out[k] = sm
# Push: rises with the drive (0.30 -> 0.40), held through the extension, eased back by 0.75 s.
push = [9.0 * smoothstep(0.30, 0.40, i / 30) * (1.0 - smoothstep(0.53, 0.75, i / 30)) for i in range(N)]
for k, n in NAMES.items():
    print('    inline constexpr float %s[CameraSamples]={%s};' % (n, ','.join('%.2ff' % v for v in out[k])))
print('    inline constexpr float StabPush[CameraSamples]={%s};' % ','.join('%.2ff' % v for v in push))
