"""Explain the requested ASH12 arm discrepancy from saved, read-only binding data.

This reproduces only the current Capture arm-chain equations. It does not run
the game, mutate UE assets, or serve as a runtime acceptance test.
"""
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
bindings = json.loads((OUT / "current-bindings.json").read_text(encoding="utf-8"))
motion = json.loads((ROOT / "SourceAssets/DoorPush20261002/full-pose.json").read_text(encoding="utf-8"))
donor = bindings["sources"]["M4Donor"]["bones"]
target = bindings["sources"]["ASH12"]["bones"]


def r(transform):
    return Rotation.from_quat(transform["rotation_xyzw"]).as_matrix()


def angle(matrix):
    return float(np.degrees(Rotation.from_matrix(matrix).magnitude()))


def parent_name(bones, name):
    index = bones[name]["parent"]
    return next((n for n, b in bones.items() if b["index"] == index), None)


def authored_donor_components(key):
    # Match the C++ FK and parent-scale normalization, using current native refs.
    result = {}
    for name, bone in sorted(donor.items(), key=lambda item: item[1]["index"]):
        parent = parent_name(donor, name)
        local = bone["local"]
        lr, lt, ls = r(local), np.array(local["position"]), np.array(local["scale"])
        if name in motion["order"]:
            authored = np.array(key["local"][name])
            lr = authored[:3, :3]
            parent_scale = np.array(donor[parent]["component"]["scale"]) if parent else np.ones(3)
            lt = authored[:3, 3] / parent_scale
        if parent:
            pr, pt, ps = result[parent]
            result[name] = (pr @ lr, pt + pr @ (ps * lt), ps * ls)
        else:
            result[name] = (lr, lt, ls)
    return result


chain = ("clavicle_l", "upperarm_l", "lowerarm_l", "hand_l")
rest_differences = {}
for name in chain:
    parent = parent_name(target, name)
    target_length = np.array(target[name]["local"]["position"]) * np.array(target[parent]["component"]["scale"])
    donor_length = np.array(donor[name]["local"]["position"]) * np.array(donor[parent]["component"]["scale"])
    rest_differences[name] = {
        "component_rotation_difference_degrees": angle(r(target[name]["component"]) @ r(donor[name]["component"]).T),
        "target_parent_local_offset_cm": target_length.tolist(),
        "donor_parent_local_offset_cm": donor_length.tolist(),
    }

keys = []
for key in motion["poses"][1:6]:
    dc = authored_donor_components(key)
    mapped_r = {name: dc[name][0] @ r(donor[name]["component"]).T @ r(target[name]["component"]) for name in chain}
    camera = {}
    for name in chain:
        local = target[name]["local"]
        ls = np.array(local["scale"])
        if name == "clavicle_l":
            scale = np.array(target[name]["component"]["scale"])
            upper_offset = np.array(target["upperarm_l"]["local"]["position"]) * scale
            camera[name] = (mapped_r[name], np.array(key["contact"]["shoulder_cm"]) - mapped_r[name] @ upper_offset, scale)
        else:
            parent = parent_name(target, name)
            pr, pt, ps = camera[parent]
            local_r = mapped_r[parent].T @ mapped_r[name]
            camera[name] = (pr @ local_r, pt + pr @ (ps * np.array(local["position"])), ps * ls)
    keys.append({
        "key": key["name"],
        "time_seconds": key["time_seconds"],
        "desired_elbow_camera_cm": key["contact"]["elbow_cm"],
        "mapped_elbow_camera_cm": camera["lowerarm_l"][1].tolist(),
        "elbow_position_error_cm": float(np.linalg.norm(camera["lowerarm_l"][1] - np.array(key["contact"]["elbow_cm"]))),
        "desired_wrist_camera_cm": key["contact"]["wrist_cm"],
        "mapped_wrist_camera_cm": camera["hand_l"][1].tolist(),
        "wrist_position_error_cm": float(np.linalg.norm(camera["hand_l"][1] - np.array(key["contact"]["wrist_cm"]))),
        "hand_component_rotation_difference_degrees": angle(camera["hand_l"][0] @ dc["hand_l"][0].T),
    })

report = {
    "scope": "Requested ASH12 whole-left-arm binding/retarget diagnosis",
    "motion_revision": motion["revision"],
    "method": "Reproduce current Capture component-rotation transfer and native arm-length FK from actual exported UE binding data",
    "source_assets": {name: {k: v[k] for k in ("path", "skeleton", "source_sha256")} for name, v in bindings["sources"].items()},
    "rest_differences": rest_differences,
    "guard_keys": keys,
    "runtime_code_changed": False,
    "assets_changed": False,
    "runtime_tested": False,
    "rendered": False,
}
(OUT / "binding-transfer-diagnosis.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"rest_differences": rest_differences, "prepare": keys[0], "report": str(OUT / "binding-transfer-diagnosis.json")}, ensure_ascii=False, indent=2))
