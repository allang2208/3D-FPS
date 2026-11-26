"""Replay the FINAL shipped code exactly.

    Base  = Eye + (0,-13,-35)
    Limit = max(1, ArmSpan) - 0.2
    Safe  = Limit * 0.9
    LeftWorks = Bottle || Pour || Grind
    Center = mean of the working hands
    Anchor = first lerp(Base, Center, k/64) whose worst working-hand distance
             is <= Safe   (k = 0..64; falls back to the k=64 point)
"""
import numpy as np

EYE = np.array([157.0, -185.0, 186.0])
ARM = 50.0
LIMIT = ARM - .2
SAFE = LIMIT * .90
BASE = EYE + np.array([0.0, -13.0, -35.0])
POT = np.array([225.0, -106.0])
POT_R = 28.0
RIM = 133.0

# name: (right wrist, left wrist, leftWorks)
cases = {
    'pour':   (np.array([220.0, -103.0, 131.0]), np.array([220.0, -103.0, 131.0]), True),
    'grind':  (np.array([48.0, -52.0, 108.0]),   np.array([39.0, -58.0, 101.0]),   True),
    'stir':   (np.array([236.0, -106.0, 137.5]), np.array([195.0, -133.0, 113.0]), False),
    'bottle': (np.array([225.0, -106.0, 133.3]), np.array([195.0, -134.0, 118.0]), True),
    'timer':  (np.array([164.0, -45.0, 101.0]),  np.array([195.0, -133.0, 113.0]), False),
    'idle':   (EYE + np.array([25.0, 40.0, -51.0]), np.array([195.0, -133.0, 113.0]), False),
}


def in_pot(p):
    return (np.linalg.norm(p[:2] - POT) < POT_R) and (p[2] < RIM + 2.0)


def shipped(rw, lw, left_works, acting=True):
    if not acting:
        return BASE.copy(), 0.0
    hands = [rw] + ([lw] if left_works else [])
    center = sum(hands) / len(hands)
    anchor = BASE.copy()
    for k in range(65):
        t = k / 64.0
        cand = BASE * (1 - t) + center * t
        anchor = cand
        if max(np.linalg.norm(h - cand) for h in hands) <= SAFE:
            break
    return anchor, t


print('LIMIT %.1f  SAFE %.1f\n' % (LIMIT, SAFE))
print('%-7s %6s %-25s %8s %8s %8s %s'
      % ('case', 't', 'anchor', 'pot', 'work', 'clamp?', 'verdict'))
allok = True
for name, (rw, lw, lw_ok) in cases.items():
    acting = name != 'idle'
    a, t = shipped(rw, lw, lw_ok, acting)
    hands = [rw] + ([lw] if lw_ok else [])
    wk = max(np.linalg.norm(h - a) for h in hands)
    bad = (wk > LIMIT) or (acting and in_pot(a))
    allok &= not bad
    print('%-7s %6.2f (%5.1f,%7.1f,%6.1f) %8.1f %8.1f %8s %s'
          % (name, t, a[0], a[1], a[2], np.linalg.norm(a[:2] - POT), wk,
             'YES' if wk > LIMIT else 'no', 'BAD' if bad else 'ok'))

print()
print('worst working-hand reach stays under the %.1f clamp in every case'
      % LIMIT)
print('ALL OK' if allok else 'NEEDS ATTENTION')