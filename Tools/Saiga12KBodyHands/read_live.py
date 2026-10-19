import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KBodyHands20261018/Receipts')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'world':world.get_path_name() if world else None,'actors':[]}
def vec(v):return [v.x,v.y,v.z]
def trans(t):return {'location':vec(t.translation),'scale':vec(t.scale3d),'rotation':str(t.rotation)}
if world:
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
  if 'FPS' not in a.get_class().get_name():continue
  at=a.get_actor_transform();row={'actor':a.get_path_name(),'actor_transform':trans(at),'components':[]}
  for c in a.get_components_by_class(u.SkeletalMeshComponent):
   mesh=c.get_skinned_asset()
   r={'name':c.get_name(),'class':c.get_class().get_name(),'mesh':mesh.get_path_name() if mesh else None,
      'visible':c.is_visible(),'hidden':c.get_editor_property('hidden_in_game'),
      'owner_no_see':c.get_editor_property('owner_no_see'),'only_owner_see':c.get_editor_property('only_owner_see'),
      'transform':trans(c.get_world_transform()),'bones':{}}
   for bone in ('root','spine_03','clavicle_r','upperarm_r','lowerarm_r','hand_r','index_01_r','upperarm_l','lowerarm_l','hand_l','index_01_l','WPN_root','WPN_FrontSight','WPN_RearSight'):
    if c.does_socket_exist(bone):
     bt=c.get_socket_transform(bone,u.RelativeTransformSpace.RTS_WORLD)
     r['bones'][bone]={'actor_local':vec(at.inverse_transform_location(bt.translation)),'scale':vec(bt.scale3d)}
   row['components'].append(r)
  result['actors'].append(row)
(O/'live-before.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('S12K_LIVE_READ',result['world'],len(result['actors']))
