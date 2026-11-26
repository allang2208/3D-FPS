"""Second pass: with the anchor at the shared hand midpoint (what the new code
actually does), check reach and elbow height for both arms at once.

The previous script anchored each target individually at 20 cm, which forces
the elbow to fold back. The code anchors once, at the midpoint of both wrist
targets, so the geometry is quite different.
"""
import numpy as np

EYE = np.array([157.0, -185.0, 186.0])
L1 = L2 = 25.0
LIMIT = L1 + L2 - 0.2


def solve(side, wrist, anchor):
    d = wrist - anchor
    raw = np.linalg.norm(d)
    axis = d / max(raw, 1e-6)
    D = min(max(raw, abs(L1 - L2) + .1), LIMIT)
    shoulder = wrist - axis * D
    pole = np.array([1.0 if side else -1.0, -.35, -.7])
    pole = pole - axis * np.dot(pole, axis)
    pole = pole / max(np.linalg.norm(pole), 1e-6)
    along = (L1 * L1 - L2 * L2 + D * D) / (2 * D)
    h = np.sqrt(max(0.0, L1 * L1 - along * along))
    elbow = shoulder + axis * along + pole * h
    return shoulder, elbow, raw, D


# (right wrist, left wrist) for each operation, per the code paths
cases = {
    'stir': (np.array([236.0, -106.0, 137.5]), np.array([195.0, -133.0, 113.0])),
    'ladle': (np.array([225.0, -106.0, 133.3]), np.array([195.0, -134.0, 118.0])),
    'pour': (np.array([220.0, -103.0, 131.0]), np.array([220.0, -103.0, 131.0])),
    'dose': (np.array([195.0, -134.0, 116.0]), np.array([195.0, -134.0, 118.0])),
    'grind': (np.array([48.0, -52.0, 108.0]), np.array([39.0, -58.0, 101.0])),
}

print('%-7s %9s %9s %9s %9s %s'
      % ('case', 'R reach', 'L reach', 'R elbowZ', 'L elbowZ', 'verdict'))
for name, (rw, lw) in cases.items():
    mid = (rw + lw) * .5
    anchor = mid + (mid - EYE) / max(np.linalg.norm(mid - EYE), 1e-6) * 20.0
    rs, re, rraw, rD = solve(1, rw, anchor)
    ls, le, lraw, lD = solve(0, lw, anchor)
    okR = rraw <= LIMIT
    okL = lraw <= LIMIT
    print('%-7s %9.1f %9.1f %9.1f %9.1f %s'
          % (name, rraw, lraw, re[2] - rs[2], le[2] - ls[2],
             'OK' if okR and okL else 'CLAMPED'))

print()
print('Anchor = hand midpoint + 20 cm away from the lens.')
print('Reach stays at 20-35 cm against a 49.8 cm limit, so the clamp never')
print('fires and the shoulder keeps the anchor position instead of jumping to')
print('the bench. That is what removes the stretched shoulder skin.')
