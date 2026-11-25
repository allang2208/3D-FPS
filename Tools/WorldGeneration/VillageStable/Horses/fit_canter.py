"""Fit the native in-place Warhorse canter to the ridden ground speed, retaining hoof notifies."""
import json
import os
from pathlib import Path

import unreal as ue

folder = "/Game/WorldGeneration/TemperateHills/VillageStable/Horses"
clip = ue.load_asset(folder + "/Animations/A_Warhorse_Canter")
mesh = ue.load_asset(folder + "/SK_StableWarhorse")
out = Path(os.environ["STABLE_CANTER_REVIEW"])
out.mkdir(exist_ok=True, parents=True)
pose_api = ue.AnimPoseExtensions
opts = ue.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh = mesh
opts.set_editor_property("evaluation_type", ue.AnimDataEvalType.SOURCE)
ref = mesh.skeleton.get_reference_pose()
names = list(pose_api.get_bone_names(ref))
length = clip.get_play_length()
total = clip.get_editor_property("data_model_interface").get_number_of_keys() - 1
if total != 20 or ue.EditorAssetLibrary.get_metadata_tag(clip, "StableCanterFit") == "R12":
    raise RuntimeError("Start from the R11 20-frame canter")


def world(pose):
    result = {}
    for name in names:
        tr = pose_api.get_bone_pose(pose, name, ue.AnimPoseSpaces.WORLD)
        result[str(name)] = list(tr.translation.to_tuple()) + list(tr.rotation.to_tuple())
    return result


def snapshot():
    return [world(pose_api.get_anim_pose_at_time(clip, length*i/80, opts)) for i in range(81)]


poses = {"period": length, "bind": world(ref), "before": snapshot()}
# Plant frames are shared with StableHoofContacts. Advance the limb through
# support faster, then give that time back smoothly during swing. Torso, saddle
# and head stay on their native phase. Each chain retains its source bone lengths.
# The canter is asymmetric. The component-space sole measurements also include
# the unchanged pelvis and scapular attachment motion, different for each leg.
chains = [(1, 4, 1.32, "thigh_R calf_R foot_R toe_R"),
          (6, 5, 1.38, "scapula_R upperarm_R forearm_R hand_R finger_R"),
          (7, 4, 1.25, "thigh_L calf_L foot_L toe_L"),
          (11, 5, 1.31, "scapula_L upperarm_L forearm_L hand_L finger_L")]
tracks = {}
for plant, stance, factor, bones in chains:
    for i in range(total + 1):
        phase = (i - plant) % total
        release = stance / factor
        x = max(0., (phase-release) / (total-release))
        native = (plant + factor*phase - (factor-1)*total*x*x*(3-2*x)) % total
        pose = pose_api.get_anim_pose_at_time(clip, length*native/total, opts)
        for name in bones.split():
            tracks.setdefault(name, []).append(pose_api.get_bone_pose(pose, name, ue.AnimPoseSpaces.LOCAL))

ctl = clip.get_editor_property("controller")
ctl.open_bracket("Fit Warhorse canter support and swing", False)
try:
    for name, keys in tracks.items():
        if not ctl.set_bone_track_keys(name, [v.translation for v in keys], [v.rotation for v in keys],
                                       [v.scale3d for v in keys], False):
            raise RuntimeError("Could not write " + name)
finally:
    ctl.close_bracket(False)
poses["after"] = snapshot()
ue.EditorAssetLibrary.set_metadata_tag(clip, "StableCanterFit", "R12")
if not ue.EditorAssetLibrary.save_loaded_asset(clip, only_if_is_dirty=False):
    raise RuntimeError("Could not save " + clip.get_name())
(out / "canter-poses.json").write_text(json.dumps(poses, separators=(",", ":")), encoding="utf-8")
