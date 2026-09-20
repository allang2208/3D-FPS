"""Read only the two installed overhead clips and an existing live sword pose."""
import unreal as u,json,hashlib,math
from pathlib import Path
P=Path(__file__).parent;P.mkdir(exist_ok=True);ROOT=Path(u.Paths.project_dir()).resolve()
def unpack(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
folders={'Standard':('/Game/Weapons/AzureRunesword20260913','/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny'),
 'LongGrip':('/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations','/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms')}
summary={}
for variant,(folder,mp) in folders.items():
 mesh=u.load_asset(mp);component=u.SkeletalMeshComponent();component.set_skeletal_mesh_asset(mesh)
 names=[str(component.get_bone_name(i)) for i in range(component.get_num_bones())]
 parents={n:str(component.get_parent_bone(n)) for n in names}
 options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
 asset=u.load_asset(folder+'/A_RuneSword_Overhead');frames=u.AnimationLibrary.get_num_frames(asset);seconds=asset.get_play_length();rows=[]
 for i in range(frames+1):
  t=i*seconds/frames;pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
  rows.append({'seconds':t,'world':{n:unpack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in names}})
 disk=ROOT/'Content'/((folder+'/A_RuneSword_Overhead').removeprefix('/Game/')+'.uasset')
 data={'variant':variant,'mesh':mp,'asset':asset.get_path_name(),'parents':parents,'intervals':frames,'seconds':seconds,'sha256':hashlib.sha256(disk.read_bytes()).hexdigest(),
  'revision':u.EditorAssetLibrary.get_metadata_tag(asset,'SwordElbow.Revision'),'samples':rows}
 (P/(variant+'_input.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
 summary[variant]={k:data[k] for k in ('asset','revision','seconds','intervals')}
live={}
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
 pawn=u.GameplayStatics.get_player_character(world,0)
 if pawn:
  for component in pawn.get_components_by_class(u.SkeletalMeshComponent):
   if component.get_name()!='RuneSwordViewmodel':continue
   live={'mesh':component.get_skeletal_mesh_asset().get_path_name(),'position':component.get_position()}
   playback=component.get_editor_property('animation_data')
   asset=playback.get_editor_property('anim_to_play')
   live['asset']=asset.get_path_name() if asset else None
   live['bones']={n:unpack(component.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in ['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','WPN_root']}
summary['existing_live_pose']=live
(P/'input_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
u.log('SWORD_DOWNCUT_INPUTS '+str({v:summary[v] for v in folders}))
u.log('SWORD_LIVE_CLIP '+str({k:v for k,v in live.items() if k!='bones'}))
