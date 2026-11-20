"""Save the in-place walk onto the installed herbalist skeleton."""
import json
import os
from pathlib import Path

import unreal as ue


PROJECT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT / "SourceAssets/VillageHerbalist/FullBody/WalkR1/motion.json"
FOLDER = "/Game/Characters/VillageHerbalist"
NAME = "A_VillageHerbalist_Walk"
motion = json.loads(SOURCE.read_text(encoding="utf-8"))
mesh = ue.load_asset(FOLDER + "/SK_VillageHerbalist")
skeleton = ue.load_asset(FOLDER + "/SK_VillageHerbalist_Skeleton")
if not mesh or not skeleton or mesh.skeleton != skeleton:
    raise RuntimeError("Missing the herbalist's published mesh and skeleton")
factory = ue.AnimSequenceFactory()
factory.set_editor_property("target_skeleton", skeleton)
factory.set_editor_property("preview_skeletal_mesh", mesh)
sequence = ue.AssetToolsHelpers.get_asset_tools().create_asset(NAME, FOLDER, ue.AnimSequence, factory)
controller = sequence.get_editor_property("controller")
controller.open_bracket("Fit a slow indoor walk to Lin Zhi", False)
try:
    controller.set_frame_rate(ue.FrameRate(motion["rate"], 1), False)
    controller.set_number_of_frames(ue.FrameNumber(motion["frames"]), False)
    for name, keys in motion["tracks"].items():
        controller.add_bone_curve(name, False)
        if not controller.set_bone_track_keys(name, [ue.Vector(*k[:3]) for k in keys],
                [ue.Quat(*k[3:7]) for k in keys], [ue.Vector(*k[7:]) for k in keys], False):
            raise RuntimeError("Could not write walk track " + name)
finally:
    controller.close_bracket(False)
# The native pelvis is the first bone. Locking it would remove weight shift
# and the vertical travel used to fit the stance foot to the ground.
sequence.set_editor_property("force_root_lock", False)
sequence.set_editor_property("enable_root_motion", False)
sequence.set_editor_property("loop", True)
ue.AnimationLibrary.add_animation_notify_track(sequence, "FootContacts")
for marker, seconds in motion["contacts"].items():
    ue.AnimationLibrary.add_animation_sync_marker(sequence, marker, seconds, "FootContacts")
ue.EditorAssetLibrary.set_metadata_tag(sequence, "GaitSpeedCmPerSecond", str(motion["speed_cm_s"]))
ue.EditorAssetLibrary.set_metadata_tag(sequence, "GaitStrideCm", str(motion["stride_cm"]))
if not ue.EditorAssetLibrary.save_loaded_asset(sequence, False):
    raise RuntimeError("Could not save " + sequence.get_path_name())
receipt = {key: value for key, value in motion.items() if key != "tracks"}
receipt.update(asset=sequence.get_path_name(), skeleton=skeleton.get_path_name())
Path(os.environ["HERBALIST_WALK_RECEIPT"]).write_text(json.dumps(receipt, indent=2), encoding="utf-8")
