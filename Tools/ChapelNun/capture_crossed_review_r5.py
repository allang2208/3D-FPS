"""Read current saved robe/body geometry and the compressed runtime idle."""
import json,hashlib
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/IdleCrossedR5/Review'
(R/'InputsAfter').mkdir(parents=True,exist_ok=True)
helper=(P/'Tools/ChapelNun/capture_sources.py').read_text(encoding='utf-8-sig')
block=helper[helper.index('G=u.GeometryScript'):helper.index('head=capture(')].replace("'Inputs'","'InputsAfter'")
exec(compile(block,'<saved nun surfaces>','exec'))
robe=capture('robe','/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe')
body=capture('body','/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_Body')
ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)
path=R/'InputsAfter/robe.json';data=json.loads(path.read_text())
group_map=[ss.get_lod_material_slot(robe,0,i) for i in range(ss.get_num_sections(robe,0))]
data['triangle_materials']=[group_map[i] for i in data['triangle_materials']]
data['polygon_group_to_material_slot']=group_map
path.write_text(json.dumps(data,separators=(',',':')))
rig=json.loads((P/'SourceAssets/ChapelNun20261115/IdleHandsFrontR1/native_rig.json').read_text())
idle=u.load_asset('/Game/Characters/ChapelNun20261115/Animations/A_Nun_Idle_Crossed_R5')
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=body
opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.should_retarget=False
def pack(t):
 return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
frames=[]
for i in range(361):
 pose=u.AnimPoseExtensions.get_anim_pose_at_time(idle,i/30,opts)
 frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in rig['names']])
rig.update(asset=idle.get_path_name(),frames=frames,rate=30,duration=idle.get_play_length())
(R/'InputsAfter/saved_idle.json').write_text(json.dumps(rig,separators=(',',':')))
assets={}
for a in (robe,body,idle):
 file=P/'Content'/(a.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
 assets[a.get_path_name()]=hashlib.sha256(file.read_bytes()).hexdigest()
(R/'InputsAfter/assets.json').write_text(json.dumps(assets,indent=2))
print('NUN_RELAXED_REVIEW_INPUTS',len(frames),idle.get_path_name(),flush=True)
