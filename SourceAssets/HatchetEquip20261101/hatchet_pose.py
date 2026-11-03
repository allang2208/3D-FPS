"""Hatchet poses from screen read-outs (camera space: x depth, y right, z up; cm) on the kukri rig.

An axe pose is given the way the reference is read: the head point EYE at an NDC position and depth, the handle's
on-screen lean (deg, + head to the right), its tilt along the view ray (deg, + head towards the camera) and the head's
facing about the handle (deg; 0 = flat to the camera with the edge to screen-left, + turns the edge away from the camera).
The fist holds the handle at grip offset s (cm along the handle from the grip centre, + towards the head).
"""
import math
import sys
from pathlib import Path

import numpy as np

KUKRI = Path(__file__).resolve().parent.parent / 'Kukri20261020'
sys.path.insert(0, str(KUKRI))
from kukri_rig import KukriRig, ndc, TAN, ASPECT  # noqa: E402
from kmath import T, mesh_to_cam, cam_to_mesh  # noqa: E402

EYE_Z = 20.0                                   # head point on the handle axis (grip frame cm): top of the handle
SPIKE = np.array([4.0, 0.0, 30.9])             # top of the head
BEARD = np.array([14.0, 0.0, 17.0])            # lower blade corner
EDGE_TOP = np.array([16.35, 0.0, 27.0])
POMMEL = np.array([0.0, 0.0, -11.0])


def ndc_cam(p, depth):
    """Camera point at NDC p (x right, y down) and depth (cm)."""
    return np.array([depth, p[0] * depth * TAN * ASPECT, -p[1] * depth * TAN])


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def axe_axes(eye_cam, lean, tilt, facing):
    """Handle direction d and edge direction e (camera space)."""
    v = unit(eye_cam)
    d0 = np.array([0.0, math.sin(math.radians(lean)), math.cos(math.radians(lean))])
    d0 = unit(d0 - v * np.dot(d0, v))                  # on-screen direction at the eye
    d = unit(d0 * math.cos(math.radians(tilt)) - v * math.sin(math.radians(tilt)))
    L = unit(np.cross(v, d))                           # screen-left, perpendicular to the view ray and the handle
    F = unit(np.cross(d, L))                           # away from the camera
    e = L * math.cos(math.radians(facing)) + F * math.sin(math.radians(facing))
    return d, e


def axe_frame(R, eye_ndc, depth, lean, tilt, facing, eye_z=EYE_Z):
    eye = ndc_cam(eye_ndc, depth)
    d, e = axe_axes(eye, lean, tilt, facing)
    return R.kukri_frame(eye - d * eye_z, d, e)


def hand_on_axe(K_axe, s):
    """The fist's grip frame at offset s along the handle."""
    return T(K_axe.point([0.0, 0.0, s]), K_axe.q, (1, 1, 1))


def axe_in_hand(K_hand, s):
    return T(K_hand.point([0.0, 0.0, -s]), K_hand.q, (1, 1, 1))


def arm_diag(R, K_hand, clav=(0.0, 0.0, 0.0), pole=None, pole_w=0.0):
    """Right-arm diagnostics for the fist K_hand (natural elbow unless a pole is given)."""
    R.reset_twist_memory()
    world, d = R.pose(K_hand, clav_r=tuple(clav), pole_r=pole, pole_r_weight=pole_w)
    r = d['right']
    pts = [mesh_to_cam(world[a].p + (world[b].p - world[a].p) * f) for a, b in
           (('upperarm_r', 'lowerarm_r'), ('lowerarm_r', 'hand_r')) for f in (0.25, 0.5, 0.75, 1.0)]
    vis = [max(ndc(c)[1], abs(ndc(c)[0])) for c in pts if c[0] > 2.0]
    # upper arm and the elbow half of the forearm (the wrist end shows wherever the fist does)
    fpts = pts[:4] + [mesh_to_cam(world['lowerarm_r'].p + (world['hand_r'].p - world['lowerarm_r'].p) * f) for f in (0.2, 0.4, 0.55)]
    fvis = [max(ndc(c)[1], abs(ndc(c)[0])) for c in fpts if c[0] > 2.0]
    return dict(reach=r['reach'], wrist=r['wrist_deg'], ext=r['ext'], uln=r['uln'], twist=r['twist_deg'], rho=r['rho'],
                elbow=d['elbow_ndc'], elbow_cam=mesh_to_cam(r['elbow']), grip=d['grip_ndc'],
                arm_margin=min(vis) if vis else 9.0, forearm_margin=min(fvis) if fvis else 9.0), world


def screen(K_axe):
    out = {}
    for k, v in (('eye', [0.0, 0.0, EYE_Z]), ('spike', SPIKE), ('beard', BEARD), ('edge', EDGE_TOP), ('pommel', POMMEL)):
        out[k] = ndc(mesh_to_cam(K_axe.point(v)))
    return out


def strain(a):
    """Anatomical cost of an arm read-out: wrist away from the accepted hammer grip, forearm twist outside the band
    the accepted clips use, a stretched arm."""
    c = (a['wrist'] / 15.0) ** 2
    c += max(0.0, a['twist'] - 60.0) ** 2 / 400.0 + max(0.0, -70.0 - a['twist']) ** 2 / 400.0
    c += 200.0 * max(0.0, a['reach'] - 0.92) ** 2
    return c


if __name__ == '__main__':
    # probe: python hatchet_pose.py ex ey depth lean s [tilt_lo tilt_hi facing_lo facing_hi]
    R = KukriRig()
    ex, ey, depth, lean, s = (float(v) for v in sys.argv[1:6])
    lims = [float(v) for v in sys.argv[6:10]] if len(sys.argv) > 9 else (-60, 60, -60, 120)
    rows = []
    for tilt in range(int(lims[0]), int(lims[1]) + 1, 10):
        for facing in range(int(lims[2]), int(lims[3]) + 1, 15):
            K = axe_frame(R, (ex, ey), depth, lean, tilt, facing)
            a, _ = arm_diag(R, hand_on_axe(K, s))
            rows.append((strain(a), tilt, facing, a))
    rows.sort(key=lambda r: r[0])
    for c, tilt, facing, a in rows[:12]:
        print('cost %6.2f tilt %4d facing %4d | wrist %5.1f ext %6.1f uln %6.1f twist %6.1f reach %.2f elbow %s grip %s' % (
            c, tilt, facing, a['wrist'], a['ext'], a['uln'], a['twist'], a['reach'],
            np.round(a['elbow'], 2), np.round(a['grip'], 2)))
