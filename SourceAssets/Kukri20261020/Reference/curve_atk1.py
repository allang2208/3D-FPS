"""atk1_camera.json -> KukriRhythm.h diagonal camera curve (stage 2, V11).

Same convention as the accepted first-hit curve (CameraYaw/Pitch/Roll/Fov): the per-frame registration from
camera_atk1.py is scaled like that curve was against its own registration (yaw x0.75, pitch x0.92, roll x1,
fov x0.75), then 3-tap smoothed ([.25 .5 .25]).  The smoothing removes the 30 Hz roll rattle of the reference's
confirmed hit (+6.9/-5.5/+10.4 deg in three frames); our swing curve also plays on misses, and the confirmed hit
adds its own damped shake (KukriRhythm::HitShake).  First and last samples are zero (stance)."""
import json
import os

d = r"D:\FPS3D\FPSGAME\Saved\Reference\KukriBV1CeYUeSE7b20261020"
data = json.load(open(os.path.join(d, "atk1_camera.json")))
frames = {f['frame']: f for f in data['frames'] if f.get('ok')}
start = data['clip_start']
N = 39
SCALE = dict(yaw=.75, pitch=.92, roll=1.0, fov=.75)
out = {}
for k, s in SCALE.items():
    raw = [frames[start + i][k] * s for i in range(N)]
    raw[0] = raw[-1] = 0.0
    sm = [raw[0]] + [.25 * raw[i - 1] + .5 * raw[i] + .25 * raw[i + 1] for i in range(1, N - 1)] + [raw[-1]]
    sm[0] = sm[-1] = 0.0
    out[k] = sm
names = dict(yaw='DiagYaw', pitch='DiagPitch', roll='DiagRoll', fov='DiagFov')
for k, n in names.items():
    print('    inline constexpr float %s[CameraSamples]={%s};' % (n, ','.join('%.2ff' % v for v in out[k])))
