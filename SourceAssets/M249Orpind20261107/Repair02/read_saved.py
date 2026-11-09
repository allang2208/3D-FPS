"""Read back the saved M249 surfaces and compressed clips for the requested inspection."""
from pathlib import Path
import pickle
import json
import unreal as u
root=Path(__file__).resolve().parent
script=root.parent/"ReloadReview/export_poses.py"
exec(compile(script.read_text(encoding="utf8"),str(script),"exec"),{"__file__":str(script)})
mesh=u.load_asset("/Game/Weapons/M249/SK_M249_V7")
dm,result=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=u.GeometryScript_BoneWeights.get_all_bones_info(dm)
bones=sorted(bones,key=lambda b:b.index)
def tr(t):return [*t.translation.to_tuple(),t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,*t.scale3d.to_tuple()]
rig=dict(names=[str(b.name) for b in bones],parent=[b.parent_index for b in bones],bind=[tr(b.world_transform) for b in bones])
with (root/"after_rig.pkl").open("wb") as f:pickle.dump(rig,f)
opts=u.AnimPoseEvaluationOptions()
opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
for role in ("idle","reload","reload_empty"):
    clip=u.load_asset("/Game/Weapons/M249/Animations/A_M249_"+role)
    count=u.AnimationLibrary.get_num_frames(clip);frames=[]
    for i in range(count+1):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,u.AnimationLibrary.get_time_at_frame(clip,i),opts)
        frames.append([tr(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in rig["names"]])
    with (root/("after_"+role+".pkl")).open("wb") as f:pickle.dump(dict(duration=clip.get_play_length(),frames=frames),f)
materials=[]
for slot in mesh.materials:
    m=slot.material_interface
    materials.append(dict(slot=str(slot.material_slot_name),material=m.get_path_name() if m else None))
(root/"saved_materials.json").write_text(json.dumps(materials,indent=2))
glass=u.load_asset('/Game/Weapons/M249/Materials/M_M249_Glass')
opacity=u.MaterialEditingLibrary.get_material_property_input_node(glass,u.MaterialProperty.MP_OPACITY)
(root/'saved_glass.json').write_text(json.dumps(dict(blend_mode=str(glass.get_editor_property('blend_mode')),
    two_sided=glass.get_editor_property('two_sided'),opacity=float(opacity.get_editor_property('r'))),indent=2))
print("M249_REPAIR02_READBACK",len(bones),len(materials),flush=True)
