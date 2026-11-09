"""Capture the complete native hierarchy and saved animation for the requested repair."""
from pathlib import Path
import pickle
import unreal as u

root=Path(__file__).resolve().parent
root.mkdir(exist_ok=True)
def tr(t):
    return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
for label,prefix,meshname,animprefix,roles in (
    ("before","/Game/Weapons/M249","SK_M249_V7","/Animations/A_M249_",("idle","reload","reload_empty")),
    ("donor","/Game/Weapons/PKMLowpoly20260922/Accessories14","SK_PKM_Manny_Modular","/Animations/vertical/A_PKM_vertical_",
     ("idle","reload","reload_empty","fire","equip","inspect","sprint_enter","sprint_loop","sprint_exit","quick_melee"))):
    mesh=u.load_asset(prefix+"/"+meshname)
    dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    _,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
    bones=sorted(bones,key=lambda b:b.index)
    names=[str(b.name) for b in bones]
    data={"names":names,"parent":[b.parent_index for b in bones],"bind":[tr(b.world_transform) for b in bones]}
    with (root/(label+"_rig.pkl")).open("wb") as f:pickle.dump(data,f)
    opts=u.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh=mesh
    opts.evaluation_type=u.AnimDataEvalType.COMPRESSED if label=="before" else u.AnimDataEvalType.RAW
    for role in roles:
        clip=u.load_asset(prefix+animprefix+role)
        count=u.AnimationLibrary.get_num_frames(clip)
        frames=[]
        for i in range(count+1):
            t=u.AnimationLibrary.get_time_at_frame(clip,i)
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opts)
            frames.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names])
        with (root/(label+"_"+role+".pkl")).open("wb") as f:
            pickle.dump({"duration":clip.get_play_length(),"frames":frames},f)
        print("M249_REPAIR_INPUT",label,role,count,flush=True)
