"""Rule with the working-hand set made explicit.

Stir and Timer leave the left hand parked at (195,-133,113); it holds nothing,
so it must not constrain the anchor. With only the right hand constrained, the
lerp from the shipped anchor toward that hand should be feasible everywhere.
"""
import numpy as np

EYE = np.array([157.0, -185.0, 186.0])
LIMIT = 49.8
SAFE = .90
BAND = LIMIT * SAFE
POT = np.array([225.0, -106.0])
POT_R = 28.0
RIM = 133.0
BASE = EYE + np.array([0.0, -13.0, -35.0])

# operation -> (right wrist, left wrist, left hand working?, right working?)
cases = {
    'pour':  (np.array([220.0, -103.0, 131.0]), np.array([220.0, -103.0, 131.0]), True,  True),
    'grind': (np.array([48.0, -52.0, 108.0]),   np.array([39.0, -58.0, 101.0]),   True,  True),
    'stir':  (np.array([236.0, -106.0, 137.5]), np.array([195.0, -133.0, 113.0]), False, True),
    'bottle':(np.array([225.0, -106.0, 133.3]), np.array([195.0, -134.0, 118.0]), True,  True),
    'timer': (np.array([164.0, -45.0, 101.0]),  np.array([195.0, -133.0, 113.0]), False, True),
}


def in_pot(p):
    return (np.linalg.norm(p[:2] - POT) < POT_R) and (p[2] < RIM + 2.0)


print('BAND %.1f  LIMIT %.1f\n' % (BAND, LIMIT))
print('%-7s %6s %-25s %8s %7s %7s %s'
      % ('case', 't', 'anchor', 'pot', 'work', 'park', 'verdict'))
ok_all = True
for name, (rw, lw, left_works, right_works) in cases.items():
    hands = ([rw] if right_works else []) + ([lw] if left_works else [])
    parked = ([lw] if not left_works else []) + ([rw] if not right_works else [])
    mid = sum(hands) / len(hands)
    pick = None
    for t in np.arange(0.0, 1.001, 0.005):
        a = BASE * (1 - t) + mid * t
        if max(np.linalg.norm(h - a) for h in hands) <= BAND and not in_pot(a):
            pick = (a, t)
            break
    if pick is None:
        print('%-7s %6s %-25s %8s %7s %7s %s'
              % (name, '-', 'NO SOLUTION', '-', '-', '-', 'BAD'))
        ok_all = False
        continue
    a, t = pick
    wk = max(np.linalg.norm(h - a) for h in hands)
    pk = max(np.linalg.norm(h - a) for h in parked) if parked else None
    bad = wk > LIMIT or in_pot(a) or (pk is not None and pk > LIMIT)
    ok_all &= not bad
    print('%-7s %6.2f (%5.1f,%7.1f,%6.1f) %8.1f %7.1f %7s %s'
          % (name, t, a[0], a[1], a[2], np.linalg.norm(a[:2] - POT), wk,
             ('%.1f' % pk) if pk is not None else '-',
             'BAD' if bad else 'ok'))

print()
print('ALL OK' if ok_all else 'NEEDS ATTENTION')