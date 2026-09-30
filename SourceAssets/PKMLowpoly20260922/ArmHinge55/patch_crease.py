"""ArmHinge55b: calibrate the anatomical elbow frame to the skin's modelled crease.

Elbow close views of the 201 reload (Diagnostics/elbow/roll_fine.jpg): with the upper-arm
helpers exactly on the bind bend axis the flexed elbow (>100 deg) folds the proximal forearm
into a crescent; rolling the elbow pair +15..+30 deg about the limb axes leaves only the
normal inner-elbow fold.  Use +20 deg, faded in with the bend (0 below 30 deg, full above 70),
inside the reference frame, so the forearm cap / remainder logic is unchanged."""
from pathlib import Path
p = Path(__file__).with_name('author.py')
s = p.read_text(encoding='utf8')
rep = [
    # undo the sweep hook
    ("""        fe = axis_angle(f, tu[k] + ROLL_OFFSET * w_roll[k]) @ Dl""", """        fe = axis_angle(f, tu[k]) @ Dl"""),
    ("""    bends = np.array([np.degrees(np.arctan2(np.linalg.norm(np.cross(r[1], r[2])), r[1] @ r[2])) for r in rows])
    w_roll = np.clip((bends - 30.0) / 40.0, 0, 1)
    w_roll = w_roll * w_roll * (3 - 2 * w_roll)
    tf = tf - ROLL_OFFSET * w_roll   # the offset is taken back out of the forearm, so the hand is unchanged
""", ""),
    ("""ROLL_OFFSET = 0.0  # rad, elbow-pair roll relative to the bind hinge (applied with the bend weight)""",
     """# The skin's modelled elbow crease sits ~20 deg off the bind bend axis (ArmHinge55b, elbow
# close views): the elbow pair is referenced to that, faded in with the elbow bend.
CREASE_ROLL = np.radians(20.0)


def crease_weight(bend_deg):
    w = np.clip((bend_deg - 30.0) / 40.0, 0.0, 1.0)
    return w * w * (3 - 2 * w)"""),
    ("""        h = unit(h - unit(u) * (unit(u) @ h))
        Dl = frame(f, h) @ bind.FL0.T""",
     """        h = unit(h - unit(u) * (unit(u) @ h))
        Dl = axis_angle(f, CREASE_ROLL * crease_weight(bend)) @ frame(f, h) @ bind.FL0.T"""),
]
for a, b in rep:
    assert a in s, a[:60]
    s = s.replace(a, b)
p.write_text(s, encoding='utf8')
print('patched')
