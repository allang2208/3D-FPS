"""Read the active vertical-grip motion as native authoring input."""
import gzip
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
SOURCE = "/Game/Weapons/PKMLowpoly20260922/Accessories14"
mesh = u.load_asset(SOURCE + "/SK_PKM_Manny_Modular")
dm, result = u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh, u.DynamicMesh(), u.GeometryScriptCopyMeshFromAssetOptions(), u.GeometryScriptMeshReadLOD())
_, bones = u.GeometryScript_BoneWeights.get_all_bones_info(dm)
names = {b.index:str(b.name) for b in bones}
parents = {str(b.name):names.get(b.parent_index) for b in bones}
def tr(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
bind = {str(b.name):tr(b.world_transform) for b in bones}
folder=ROOT/"MotionInput"
folder.mkdir(exist_ok=True)
(folder/"rig.json").write_text(json.dumps({"parents":parents,"bind":bind,"skeleton":mesh.skeleton.get_path_name()}))
markers=["WPN_root","WPN_SOCKET_Muzzle","WPN_FrontSight","WPN_RearSight","WPN_SOCKET_Eject","WPN_SOCKET_Magazine","PKM_Cover","PKM_Box","New_PKM_Box","PKM_Charge","PKM_Trigger","PKM_Tray","PKM_Belt_00","New_PKM_Belt_00"]
for prefix in ("PKM_", "New_PKM_"):
    markers.extend(prefix+"Belt_"+str(i).zfill(2) for i in range(9))
    markers.extend(prefix+"Belt_Link_"+str(i).zfill(2) for i in range(8))
arms=[part+"_"+side for side in ("l","r") for part in ("upperarm","lowerarm","hand","middle_01","middle_02","middle_03","index_02","pinky_02")]
keys=list(dict.fromkeys(markers+arms+[parents[n] for n in arms+markers if parents.get(n)]))
opts=u.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh=mesh
opts.evaluation_type=u.AnimDataEvalType.RAW
for role in ("idle","fire","equip","inspect","sprint_enter","sprint_loop","sprint_exit","quick_melee","reload","reload_empty"):
    path=SOURCE+"/Animations/vertical/A_PKM_vertical_"+role
    seq=u.load_asset(path)
    if not seq:raise RuntimeError(path)
    n=u.AnimationLibrary.get_num_frames(seq)
    frames=[]
    for i in range(n+1):
        t=u.AnimationLibrary.get_time_at_frame(seq,i)
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(seq,t,opts)
        frames.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,k,u.AnimPoseSpaces.WORLD)) for k in keys])
    with gzip.open(folder/(role+".json.gz"),"wt",encoding="utf8",compresslevel=1) as out:
        json.dump({"source":path,"duration":seq.get_play_length(),"bones":keys,"frames":frames},out,separators=(",",":"))
    print("M249_SOURCE",role,n,flush=True)
