"""heavy_x_camera.json (camera_heavy_x.py) -> the dual heavy camera curves (degrees, 30 Hz on the author clocks).

Charge (KukriHeavyRhythm::DualCharge*, 13 samples over the raise 0-0.40): the reference 0-0.30 s (the X opening and the
wind-up out of the top of the frame) stretched onto the raise: a short lift and widening as the X opens (+1.1 deg pitch,
+2 FOV), then the view sinks and narrows while the arms go up (pitch -3.4, FOV -3, a little left yaw and right roll).
The load (0.40-2.00) eases on from there to DualLoaded* (a bit deeper: the focus of a long charge).
Release (KukriRhythm::DualHeavy*, 31 samples over 0-1.00): from DualLoaded* through the reference 0.30-1.13 s, mapped on
the release keys (KN_A / KN_R below).  The chop frames 2355-2363 sit in the hit burst and only chain (no direct fit):
they are kept but 3-tap smoothed (the confirmed hit adds its own shake), the roll rattle x0.7.  Scaling yaw x0.75,
pitch x0.92 (as the other kukri curves).  After ref 0.633 the direct fits drift with the player's aim: the curve fades to
zero by author 0.70.
"""
import json
import os

import numpy as np

d = r"D:\FPS3D\FPSGAME\Saved\Reference\DualKukriBV19dUqBJECT20261025"
data = json.load(open(os.path.join(d, "heavy_x_camera.json")))
F = {f['frame']: np.array([f['yaw'], f['pitch'], f['roll'], f['fov']]) for f in data['frames']}
START = data['clip_start']
SCALE = np.array([.75, .92, 1.0, 1.0])


def ref(t):
    """Reference camera at ref seconds t (linear between frames)."""
    x = START + t * 30
    i = int(np.floor(x))
    f = x - i
    return F[i] * (1 - f) + F[min(i + 1, max(F))] * f


# Charge raise: author 0-0.40 <- ref 0-0.30.
charge = np.array([ref(i / 30 * 0.75) * SCALE for i in range(13)])
loaded = charge[-1] * np.array([1.25, 1.1, 1.2, 1.25])
# Release: author -> ref seconds.
# R15: the release keys (author_dual_heavy.RELEASE_T) over 0.037 / 0.068 / 0.109 / 0.136 / 0.158 = the reference's
# frames 2355-2359.
KN_A = [0.0, 0.037, 0.068, 0.109, 0.136, 0.158, 0.300, 0.700, 1.000]
KN_R = [0.300, 0.333, 0.367, 0.400, 0.433, 0.467, 0.633, 1.000, 1.133]
N = 31
rel = np.array([ref(np.interp(i / 30, KN_A, KN_R)) * SCALE for i in range(N)])
burst = slice(1, 12)
# R15 (user: the X stutters): 5-tap smoothing through the burst (3-tap left the +5 deg pitch jump in one sample) and an
# ease from the loaded camera into it over the first 0.10 s, so the view swings with the chop instead of snapping.
sm = rel.copy()
k5 = np.array([1, 4, 6, 4, 1], float) / 16
for i in range(2, N - 2):
    sm[i] = k5 @ rel[i - 2:i + 3]
rel[burst] = sm[burst]
rel[burst, 2] *= 0.7
for i in range(N):
    t = i / 30
    if t < 0.10:
        e = (t / 0.10) ** 2 * (3 - 2 * t / 0.10)
        rel[i] = loaded * (1 - e) + rel[i] * e
rel[0] = loaded
for i in range(N):
    t = i / 30
    if t > 0.36:
        x = min(1.0, (t - 0.36) / (0.70 - 0.36))
        rel[i] *= 1 - x * x * (3 - 2 * x)
rel[-1] = 0
names = ('Yaw', 'Pitch', 'Roll', 'Fov')
print('    // KukriHeavyRhythm (charge raise 0-0.40, 30 Hz)')
for k, n in enumerate(names):
    print('    inline constexpr float DualCharge%s[ChargeSamples]={%s};' % (n, ','.join('%.2ff' % v for v in charge[:, k])))
print('    inline constexpr float DualLoadedYaw=%.2ff, DualLoadedPitch=%.2ff, DualLoadedRoll=%.2ff, DualLoadedFov=%.2ff;' % tuple(loaded))
print('    // KukriRhythm (release 0-1.00, 30 Hz)')
print('    inline constexpr int32 DualHeavySamples=%d;' % N)
for k, n in enumerate(names):
    print('    inline constexpr float DualHeavy%s[DualHeavySamples]={%s};' % (n, ','.join('%.2ff' % v for v in rel[:, k])))
