"""Extend the R2 torch reach along both native arm chains, retaining palm orientation and the fitted grip."""
import json
import os
import sys
from pathlib import Path

import numpy as np

root = Path(os.environ["FPS_PROJECT_ROOT"])
family = root / "SourceAssets/WoodenTorch20261122"
sys.path.insert(0, str(root / "SourceAssets/Kukri20261020"))
from kmath import Rig, T, cam_to_mesh, load_dump, mesh_to_cam, qbetween, qfrommat, qmul, qrot
from kukri_rig import frame_mat

rig = Rig(load_dump())
parent = dict(zip(rig.names, rig.parents))
take = json.loads((family / "FabHandheldR2/Export/Carry.json").read_text("utf8"))
settled = {}


def extend_arm(pose, side, offset):
    upper, lower, hand = (pose[name + "_" + side] for name in ("upperarm", "lowerarm", "hand"))
    a = lower.p - upper.p
    b = hand.p - lower.p
    reach = hand.p + offset - upper.p
    distance = np.linalg.norm(reach)
    axis = reach / distance
    # Transport the original elbow plane to the new line of reach. Both links keep their lengths.
    old_normal = np.cross(a, b)
    normal = qrot(qbetween(hand.p - upper.p, reach), old_normal)
    pole = np.cross(axis, normal)
    pole /= np.linalg.norm(pole)
    along = (np.dot(a, a) - np.dot(b, b) + distance**2) / (2 * distance)
    radius_sq = np.dot(a, a) - along**2
    if radius_sq <= 0:
        raise ValueError(f"{side} wrist is outside its two-bone reach")
    elbow = upper.p + along * axis + np.sqrt(radius_sq) * pole
    new_hand = hand.p + offset
    for bone, old_dir, new_dir in ((upper, a, elbow - upper.p), (lower, b, new_hand - elbow)):
        change = frame_mat(new_dir, normal) @ frame_mat(old_dir, old_normal).T
        bone.q = qmul(qfrommat(change), bone.q)
    lower.p = elbow
    hand.p = new_hand


previous = {}
for i, keys in enumerate(take["frames"]):
    pose = rig.world({name: T(*key) for name, key in keys.items()})
    u = min(i / take["raise_frames"], 1.)
    blend = u**3 * (10 + u * (-15 + 6 * u))
    for side, sign in (("r", 1), ("l", -1)):
        offset = cam_to_mesh((5., sign * 3.5, 0.)) * blend
        hand = pose["hand_" + side]
        before = mesh_to_cam(hand.p)
        extend_arm(pose, side, offset)
        changed = ["upperarm_" + side, "lowerarm_" + side, "hand_" + side]
        markers = ["ik_hand_" + side]
        if side == "r":
            markers.append("WPN_root")
        for name in markers:
            pose[name].p += offset
        # Leave all digit keys and the socket-to-palm relation from the Fab fit intact.
        for name in changed + markers:
            local = pose[name].relative_to(pose[parent[name]])
            if name in previous and np.dot(previous[name], local.q) < 0:
                local.q = -local.q
            previous[name] = local.q
            keys[name] = [local.p.tolist(), local.q.tolist(), local.s.tolist()]
        if i == take["raise_frames"]:
            settled[side] = {"from": before.round(3).tolist(), "to": mesh_to_cam(hand.p).round(3).tolist(),
                             "elbow": mesh_to_cam(pose["lowerarm_" + side].p).round(3).tolist()}

out = family / "ReachGaitR5/Export"
out.mkdir(parents=True, exist_ok=True)
(out / "Carry.json").write_text(json.dumps(take, separators=(",", ":")), encoding="utf8")
print(json.dumps({"units": "camera axes in cm before viewmodel mount", "settled": settled}))
