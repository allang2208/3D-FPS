"""Author the carry from exported UE skin.json (v/t/w/b) and grip.json (v/t/offset, cm)."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "Source/FPSGAME"
ASSETS = ROOT / "SourceAssets"
args = argparse.ArgumentParser(description=__doc__)
args.add_argument("skin", type=Path)
args.add_argument("grip", type=Path)
inputs = args.parse_args()
mesh = json.loads(inputs.skin.read_text())
grip = json.loads(inputs.grip.read_text())
seed = json.loads((ASSETS / "KukriDualWhirlwind20261026/native-left-grip.json").read_text())


def unit(v):
    return v / np.linalg.norm(v)


donor = {name: (Rotation.from_quat(t[3:7]), np.array(t[:3])) for name, t in seed["bones"].items()}
hand_q, hand_p = donor["hand_l"]
axe_q = hand_q * Rotation.from_quat(seed["blade_rotation_xyzw"])
axe_p = hand_p + hand_q.apply(seed["blade_position_cm"])
donor = {k: (axe_q.inv() * q, axe_q.inv().apply(t - axe_p)) for k, (q, t) in donor.items()}
bind = mesh["b"]
positions = np.asarray(mesh["v"])
weights = mesh["w"]
dominant = np.array([max(w, key=w.get) if w else "" for w in weights])

# Support planes of the assembled factory grip. Slicing the UE triangles
# preserves the flattened sides and the shoulder of the grip under the thumb.
handle = np.asarray(grip["v"]) + grip["offset"]
triangles = np.asarray(grip["t"])
edges = np.unique(np.sort(triangles[:, [0, 1, 1, 2, 2, 0]].reshape(-1, 2), axis=1), axis=0)
lo, hi = handle[edges[:, 0]], handle[edges[:, 1]]
heights = np.arange(-7.5, 10.51, .25)
angles = np.linspace(0, 2*np.pi, 48, endpoint=False)
normals = np.stack((np.cos(angles), np.sin(angles))).T
sections = []
for z in heights:
    crossing = (np.minimum(lo[:, 2], hi[:, 2]) <= z) & (np.maximum(lo[:, 2], hi[:, 2]) > z)
    start, end = lo[crossing], hi[crossing]
    xy = start[:, :2] + (end[:, :2]-start[:, :2]) * ((z-start[:, 2])/(end[:, 2]-start[:, 2]))[:, None]
    sections.append(np.max(xy @ normals.T, axis=0))
sections = np.asarray(sections)


def handle_gap(skin):
    cell = np.clip((skin[:, 2]-heights[0])/.25, 0, len(heights)-1.00001)
    row = cell.astype(int)
    radius = sections[row]+(cell-row)[:, None]*(sections[row+1]-sections[row])
    return np.max(skin[:, :2] @ normals.T-radius, axis=1)


def contributions(ids):
    out = []
    for bone in sorted({b for i in ids for b in weights[i]}):
        w = np.array([weights[i].get(bone, 0.) for i in ids])
        rest = bind[bone][1]
        local = Rotation.from_quat(rest[3:7]).inv().apply(positions[ids]-rest[:3])
        out.append((bone, w[:, None], local))
    return out


def deform(parts, fitted):
    skin = np.zeros_like(parts[0][2])
    for bone, w, points in parts:
        q, t = fitted.get(bone, donor[bone])
        skin += (q.apply(points)+t)*w
    return skin


# Fingertips may touch the palm, but must stop at the skin. Find the outer
# palmar faces directed towards the wrapped tips, omitting the back of the hand.
palm_labels = {"hand_l", *(f"{f}_metacarpal_l" for f in ("index","middle","ring","pinky"))}
palm_faces = np.asarray(mesh["t"])
palm_faces = palm_faces[np.isin(dominant[palm_faces], list(palm_labels)).all(axis=1)]
palm_ids, inverse = np.unique(palm_faces, return_inverse=True)
palm_skin = deform(contributions(palm_ids), {})
palm_tri = palm_skin[inverse.reshape(-1, 3)]
centres = palm_tri.mean(axis=1)
surface_n = np.cross(palm_tri[:, 1]-palm_tri[:, 0], palm_tri[:, 2]-palm_tri[:, 0])
surface_n /= np.maximum(np.linalg.norm(surface_n, axis=1, keepdims=True), 1e-10)
# Infer the winding from the two sides instead of assuming a DCC convention.
radial = centres[:, :2]-centres[:, :2].mean(axis=0)
if np.median((surface_n[:, :2]*radial).sum(axis=1)) < 0:
    surface_n = -surface_n
palmar = (surface_n[:, 1] > .32) & (centres[:, 1] > -3)
palmar_points, palmar_normals = centres[palmar], surface_n[palmar]
palm_tree = cKDTree(palmar_points)


def fit(digit, tip_height, lane):
    joints = [f"{digit}_0{i}_l" for i in (1, 2, 3)]
    parent = bind[joints[0]][0]
    donors = [donor[n] for n in [parent, *joints]]
    q0, q1, q2, q3 = [v[0] for v in donors]
    p0, p1, p2, p3 = [v[1] for v in donors]
    hinge = unit(np.cross(p2 - p1, p3 - p2))
    spread_axis = unit(np.cross(p2 - p1, hinge))
    ids = np.flatnonzero(np.isin(dominant, joints))
    parts = contributions(ids)
    groups = [dominant[ids] == n for n in joints]

    def pose(angles):
        a, b, c, s, opposition = np.radians(angles)
        a1 = (Rotation.from_rotvec(spread_axis * s) * Rotation.from_rotvec(hinge * a) *
              Rotation.from_rotvec(unit(p2-p1) * opposition))
        a2 = a1 * Rotation.from_rotvec(hinge * b)
        a3 = a2 * Rotation.from_rotvec(hinge * c)
        new2 = p1 + a1.apply(p2 - p1)
        return {joints[0]: (a1 * q1, p1), joints[1]: (a2 * q2, new2),
                joints[2]: (a3 * q3, new2 + a2.apply(p3 - p2))}

    def residual(angles):
        skin = deform(parts, pose(angles))
        gap = handle_gap(skin)
        touch = [np.percentile(gap[group], 5)-target for group, target in zip(groups, (.14, .06, .055))]
        tips = skin[groups[2]]
        dist, near = palm_tree.query(tips)
        palm_gap = np.sum((tips-palmar_points[near])*palmar_normals[near], axis=1)
        palm_contact = np.where(dist < 1.5, np.minimum(palm_gap-.05, 0.), 0.)
        # Each digit wraps at its own height along the shaft. The index and
        # little finger fan apart; the opposing thumb sits above the index.
        z = skin[groups[1] | groups[2], 2]
        spilling = np.minimum(z-lane[0], 0.) + np.maximum(z-lane[1], 0.)
        return np.r_[np.minimum(gap+.055, 0.)*8/np.sqrt(len(gap)), touch,
                     palm_contact*6/np.sqrt(len(tips)), spilling*5/np.sqrt(len(z)),
                     tips[:, 2].mean()-tip_height, np.asarray(angles)*.006]

    twist = 35 if digit == "thumb" else 12
    result = least_squares(residual, np.zeros(5), bounds=([-34, -33, -28, -25, -twist], [36, 32, 28, 25, twist]))
    final = pose(result.x)
    rotations = [q0, *[final[n][0] for n in joints]]
    return [f'    {{TEXT("{joint}"),FQuat(' + ",".join(f"{v:.9f}" for v in
            (rotations[i].inv() * rotations[i + 1]).as_quat()) + ")}," for i, joint in enumerate(joints)]


rows = []
for digit, height, lane in (("index", 3.55, (2.25, 4.85)), ("middle", 1.05, (-.13, 2.2)),
                            ("ring", -1.55, (-2.65, -.2)), ("pinky", -3.85, (-5.4, -2.7)),
                            ("thumb", 5.9, (4.9, 7.5))):
    rows.extend(fit(digit, height, lane))
header = ["#pragma once", '#include "CoreMinimal.h"', "", "// Generated by PistolHatchetCarry20261107/fit_fingers.py.",
          "namespace PistolHatchetCarry", "{", "struct FDigitJoint { FName Bone; FQuat Local; };",
          "inline const FDigitJoint FingerPose[]={", *rows, "};", "}", ""]
(SRC / "Weapons/Kukri/PistolHatchetFingerPose.h").write_text("\n".join(header), encoding="utf-8")
