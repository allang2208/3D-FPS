"""Read saved clothing, section/cloth metadata and compressed idle poses."""
import json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/ChapelNun20261115/IdleBackReviewR2'
(R/'Inputs').mkdir(parents=True,exist_ok=True)
helper=(P/'Tools/ChapelNun/capture_sources.py').read_text(encoding='utf-8-sig')
block=helper[helper.index('G=u.GeometryScript'):helper.index("head=capture(")]
exec(compile(block,'<native mesh capture>','exec'))
robe=capture('robe','/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_BlackRobe')
body=capture('body','/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_Body')
ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
meta=dict(robe=robe.get_path_name(),cloth_assets=[a.get_path_name() for a in robe.mesh_clothing_assets],lods=[])
for lod in range(ss.get_lod_count(robe)):
    meta['lods'].append(dict(lod=lod,sections=[dict(section=s,material=ss.get_lod_material_slot(robe,lod,s)) for s in range(ss.get_num_sections(robe,lod))]))
(R/'Inputs/robe_metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
rig=json.loads((P/'SourceAssets/ChapelNun20261115/IdleHandsFrontR1/native_rig.json').read_text())
names=rig['names']
idle=u.load_asset('/Game/Characters/ChapelNun20261115/Animations/A_Nun_Idle_HandsFront_R1')
opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=body
opts.evaluation_type=u.AnimDataEvalType.COMPRESSED;opts.should_retarget=False
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
frames=[]
for i in range(361):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(idle,i/30,opts)
    frames.append([pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in names])
rig.update(asset=idle.get_path_name(),frames=frames,rate=30,duration=idle.get_play_length())
(R/'Inputs/saved_idle.json').write_text(json.dumps(rig,separators=(',',':')),encoding='utf-8')
print('NUN_IDLE_REVIEW_INPUTS_SAVED',len(frames),flush=True)
