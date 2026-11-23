"""Author the torch sequence in the official project using the existing arm skeleton."""
import json
import os
from pathlib import Path
import unreal as u

root = Path(os.environ["FPS_PROJECT_ROOT"])
data = json.loads((root/"SourceAssets/WoodenTorch20261122/ReachGaitR5/Export/Carry.json").read_text("utf8"))
dest = "/Game/Weapons/WoodenTorch20261122/ReachGaitR5"
name = "A_HandheldTorch_Carry_R5"
lib = u.EditorAssetLibrary
skeleton = lib.load_asset("/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny_Skeleton")
factory = u.AnimSequenceFactory()
factory.set_editor_property("target_skeleton",skeleton)
arms = lib.load_asset("/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms")
factory.set_editor_property("preview_skeletal_mesh",arms)
seq = lib.load_asset(dest+"/"+name) if lib.does_asset_exist(dest+"/"+name) else u.AssetToolsHelpers.get_asset_tools().create_asset(name,dest,u.AnimSequence,factory)
rate = u.FrameRate(numerator=data["fps"],denominator=1)
seq.get_editor_property("platform_target_frame_rate").set_editor_property("default",rate)
ctrl = seq.get_editor_property("controller")
if ctrl is None:
    ctrl = u.AnimDataController()
    ctrl.set_model(seq.get_editor_property("data_model_interface"))
ctrl.open_bracket("Wooden torch equip and carry",False)
try:
    ctrl.remove_all_bone_tracks(False)
    ctrl.set_frame_rate(rate,False)
    ctrl.set_number_of_frames(u.FrameNumber(value=len(data["frames"])-1),False)
    for bone in data["bones"]:
        if not ctrl.add_bone_curve(bone,False): raise RuntimeError("Missing bone "+bone)
        keys = [f[bone] for f in data["frames"]]
        if not ctrl.set_bone_track_keys(bone,[u.Vector(*k[0]) for k in keys],
                [u.Quat(k[1][1],k[1][2],k[1][3],k[1][0]) for k in keys],[u.Vector(*k[2]) for k in keys],False):
            raise RuntimeError("Failed to set "+bone)
finally:
    ctrl.close_bracket(False)
seq.set_preview_skeletal_mesh(arms)
seq.set_editor_property("enable_root_motion",False)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(seq) or not lib.save_loaded_asset(seq,False):
    raise RuntimeError("Could not finalize and save "+name)
(Path(os.environ["TORCH_BATCH"])/"animation-saved.json").write_text(json.dumps(dict(asset=seq.get_path_name(),
    fps=data["fps"],frames=len(data["frames"]),raise_frames=data["raise_frames"])),encoding="utf8")
