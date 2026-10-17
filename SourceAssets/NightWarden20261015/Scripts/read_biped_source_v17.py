"""Read the existing Rampage biped source for motion authoring; no asset writes."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'RecoveryInputs/RampageBiped'
for folder in ['Source','Motion','Records','Authoring']:(P/folder).mkdir(parents=True,exist_ok=True)
mesh=u.load_asset('/Game/ParagonRampage/Characters/Heroes/Rampage/Meshes/Rampage')
clip=u.load_asset('/Game/ParagonRampage/Characters/Heroes/Rampage/Animations/Jog_Biped_Fwd')
component=u.new_object(u.SkeletalMeshComponent);component.set_skeletal_mesh_asset(mesh)
bones=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.RAW;opts.optional_skeletal_mesh=mesh
def pack(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
frames=[];duration=clip.get_play_length()
for i in range(round(duration*60)+1):
    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,min(i/60,duration),opts)
    frames.append({n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones})
reference={n:pack(u.AnimPoseExtensions.get_ref_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in bones}
(P/'Source/rampage_biped_source.json').write_text(json.dumps({'asset':clip.get_path_name(),'mesh':mesh.get_path_name(),'fps':60,'duration':duration,'reference':reference,'frames':frames}),encoding='utf-8')
pie=u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
bp=u.load_asset('/Game/Monsters/NightWarden/BP_NightWarden');cdo=u.get_default_object(bp.generated_class())
info={'stage':'source_read_for_authoring','pie':pie,'source':clip.get_path_name(),'duration':duration,'frames':len(frames),'active_walk':cdo.get_editor_property('walk_clip').get_path_name(),'source_mesh':mesh.get_path_name()}
(P/'Records/source_read.json').write_text(json.dumps(info,indent=2),encoding='utf-8');print('NW17_SOURCE '+json.dumps(info))
