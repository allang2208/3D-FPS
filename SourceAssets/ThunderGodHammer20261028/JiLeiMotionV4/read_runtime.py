"""Read the existing game/editor state only; do not start gameplay."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'game_world':str(world),'actors':[]}
def vec(v):return [v.x,v.y,v.z]
def trans(t):return {'position':vec(t.translation),'rotation':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'scale':vec(t.scale3d)}
if world:
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
  if 'FPSGAMECharacter' not in a.get_class().get_name():continue
  row={'actor':a.get_name(),'meshes':[]}
  for c in a.get_components_by_class(u.SkeletalMeshComponent):
   mesh=c.get_skinned_asset()
   if not mesh:continue
   item={'component':c.get_name(),'mesh':mesh.get_path_name(),'visible':c.is_visible(),'world':trans(c.get_world_transform())}
   item['bones']={n:trans(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in ['clavicle_r','upperarm_r','lowerarm_r','hand_r','WPN_root'] if c.get_bone_index(n)>=0}
   row['meshes'].append(item)
  result['actors'].append(row)
(P/'runtime-context.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('JILEI_EXISTING_WORLD_READ',json.dumps(result),flush=True)
