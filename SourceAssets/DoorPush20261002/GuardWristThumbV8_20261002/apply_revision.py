"""Compose the local thumb revision into the existing full guard and runtime table."""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

HERE = Path(__file__).resolve().parent
ACTIVE = HERE.parent
PROJECT = ACTIVE.parents[1]
REVISION = 2026100209


def compose(thumb_path):
    patch = json.loads(Path(thumb_path).read_text(encoding="utf-8"))
    data = json.loads((HERE / "BeforeAuthored/full-pose.json").read_text(encoding="utf-8"))
    rotations = patch["local_rotation_xyzw"]
    for pose in data["poses"][1:-1]:
        local = {name: np.array(matrix, dtype=float) for name, matrix in pose["local"].items()}
        for name, quaternion in rotations.items():
            if name not in ("thumb_01_l", "thumb_02_l", "thumb_03_l"):
                raise RuntimeError("Only the three authored thumb locals belong to this revision")
            local[name][:3, :3] = Rotation.from_quat(quaternion).as_matrix()
        world = {name: np.array(matrix, dtype=float) for name, matrix in data["rest"].items()}
        for name in data["order"]:
            world[name] = world[data["parent"][name]] @ local[name]
        pose["local"] = {name: matrix.tolist() for name, matrix in local.items()}
        pose["component"] = {name: world[name].tolist() for name in pose["component"]}
        pose["source_key"] = "GuardWristThumbV8::Prepare"
    prepare = data["poses"][1]
    data.update(
        revision=REVISION,
        source_keys=["idle[0]"] + ["GuardWristThumbV8::Prepare"] * 5 + ["idle[0]"],
        guard_pose_source="SourceAssets/DoorPush20261002/GuardWristThumbV8_20261002/authored-guard.json::Prepare",
        guard_pose_source_revision=REVISION,
        fist_local={name: prepare["local"][name] for name in data["fist_bones"]},
        thumb_opposition="Locally authored three-bone opposition/curl with reduced CMC axial twist; distal pad rests on the existing closed index/middle exterior",
        thumb_revision_source=str(Path(thumb_path)),
        wrist_contract="Existing complete neutral hand_l and forearm helpers retained; excessive thumb influence at the M16 wrist is corrected in mesh weights",
        fist_source="Existing full guard arm and four-finger fist, with revised three-bone thumb opposition",
        fist_source_json="SourceAssets/DoorPush20261002/GuardWristThumbV8_20261002/authored-guard.json::Prepare",
        full_action_transfer="Existing complete raised guard placement and rigid sway; only three thumb local rotations revised; recover to current live grip",
        fist_acceptance="Wrist/thumb revision authored from the user's reported defects; not runtime-tested or accepted yet",
        runtime_tested=False, rendered=False,
    )
    data["fist_clock"]["source"] = data["fist_source"]
    data["door_guard_thumb_patch"] = patch
    data["guard_sway"]["finger_locals_unchanged"] = False
    data["guard_sway"]["finger_locals_constant_during_hold"] = True
    spec = importlib.util.spec_from_file_location("door_author", ACTIVE / "author_motion.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.REVISION = REVISION
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    (HERE / "authored-guard.json").write_text(text, encoding="utf-8")
    (ACTIVE / "full-pose.json").write_text(text, encoding="utf-8")
    (ACTIVE / "authored-parameters.json").write_text(json.dumps({
        key: value for key, value in data.items()
        if key not in ("rest", "parent", "poses", "example_base_component")
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    header = module.header(data).replace(
        "// Existing raised guard, 300ms subtle rigid whole-arm sway, then current live grip recovery.",
        "// Raised guard with revised thumb opposition, 300ms rigid sway and live grip recovery.")
    (PROJECT / "Source/FPSGAME/Movement/DoorPushAuthored20261002.h").write_text(header, encoding="utf-8")
    print("Composed revised thumb into the existing full guard and runtime header.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--thumb-patch", required=True)
    compose(parser.parse_args().thumb_patch)
