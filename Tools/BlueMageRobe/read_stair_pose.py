import json
from pathlib import Path
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018/StairRepair20261019')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();report={'pie':bool(world),'parts':[]}
names=['root','pelvis','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r','ball_l','ball_r']
def pack(t):
 p,q,s=t.translation,t.rotation,t.scale3d
 return {'p':[p.x,p.y,p.z],'q':[q.x,q.y,q.z,q.w],'s':[s.x,s.y,s.z]}
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
  for c in actor.get_components_by_class(u.SkeletalMeshComponent):
   mesh=c.get_skeletal_mesh_asset()
   if not mesh or not ('OutfitRobeDrape' in [str(t) for t in c.component_tags]):continue
   parent=c.get_attach_parent();leader=parent.get_editor_property('leader_pose_component');source=leader or parent
   row={'component':c.get_name(),'asset':mesh.get_path_name(),'pose_source':source.get_name(),'visible':c.is_visible(),'owner_no_see':c.get_editor_property('owner_no_see'),'cloth_suspended':c.is_clothing_simulation_suspended(),'component_transform':pack(c.get_world_transform()),'source_transform':pack(source.get_world_transform()),'bones':{}}
   for n in names:
    target=c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT);origin=source.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)
    row['bones'][n]={'robe':pack(target),'source':pack(origin),'position_delta_cm':(target.translation-origin.translation).length()}
   mat=c.get_material(4);row['skirt_material']={'path':mat.get_path_name(),'two_sided':mat.get_editor_property('two_sided')}
   report['parts'].append(row)
(O/'live-pose-before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps([{'component':r['component'],'source':r['pose_source'],'suspended':r['cloth_suspended'],'max_bone_position_error':max(v['position_delta_cm'] for v in r['bones'].values()),'skirt_material':r['skirt_material']} for r in report['parts']]))
