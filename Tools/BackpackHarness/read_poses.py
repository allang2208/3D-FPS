"""Capture native reference matrices and a small movement/upper-body pose set."""
import json
from pathlib import Path
import unreal as u

P = Path("D:/FPS3D/FPSGAME")
R = P / "SourceAssets/BackpackHarnessRebuild20261020"
cfg = json.loads((P/"Content/ColdSteelData/player_body.json").read_text(encoding="utf-8-sig"))
mesh = u.load_asset(cfg["body_mesh"])
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.COMPRESSED
options.incorporate_root_motion_into_pose = False
dm, status = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
    mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS:
    raise RuntimeError("Cannot read reference bones")
_, bones = u.GeometryScript_BoneWeights.get_all_bones_info(dm)


def pack(t):
    return [getattr(t.translation,c) for c in "xyz"]+[getattr(t.rotation,c) for c in "xyzw"]+[getattr(t.scale3d,c) for c in "xyz"]


names = [str(b.name) for b in bones]
report = {"reference": {str(b.name):pack(b.world_transform) for b in bones}, "clips":{}, "mesh_references":{}}
outfits=json.loads((P/"Content/ColdSteelData/modular_outfits.json").read_text(encoding="utf-8-sig"))["items"]
for name,item in outfits.items():
    path=item.get("rig_meshes",{}).get("Jason")
    if item.get("slot")!=7 or not path:continue
    garment=u.load_asset(path)
    native,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(
        garment,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError("Cannot read garment reference "+name)
    _,gb=u.GeometryScript_BoneWeights.get_all_bones_info(native)
    report["mesh_references"][name]={str(b.name):pack(b.world_transform) for b in gb}
keys = ["Unarmed.Idle","Unarmed.Walk.Fwd","Unarmed.Jog.Fwd","Crouch.Idle","Rifle.Idle","Staff.FullBody.CastRelease"]
for key in keys:
    path = cfg["clips"].get(key)
    if not path:
        continue
    clip = u.load_asset(path)
    if not clip:
        raise RuntimeError("Missing routed clip "+key)
    rows = []
    for fraction in (0., .25, .5, .75):
        time = fraction*clip.get_play_length()
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,options)
        rows.append({"time":time,"bones":{name:pack(u.AnimPoseExtensions.get_bone_pose(pose,name,u.AnimPoseSpaces.WORLD)) for name in names}})
    report["clips"][key] = {"asset":path,"frames":rows}
(R/"Inputs/poses.json").write_text(json.dumps(report,separators=(",",":")),encoding="utf-8")
print("HARNESS_NATIVE_POSES",list(report["clips"]),flush=True)
