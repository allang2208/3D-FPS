"""Read only the active SVCH assembly; do not change PIE or save assets."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result={'game_world':world.get_path_name() if world else None,'actors':[]}
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
  meshes=actor.get_components_by_class(u.MeshComponent)
  if not any('/Weapons/SVCH/' in str(c.get_editor_property('skeletal_mesh').get_path_name() if isinstance(c,u.SkeletalMeshComponent) and c.get_editor_property('skeletal_mesh') else '') for c in meshes):continue
  row={'actor':actor.get_path_name(),'components':[]}
  for c in meshes:
   parent=c.get_attach_parent();asset=c.get_editor_property('static_mesh') if isinstance(c,u.StaticMeshComponent) else c.get_editor_property('skeletal_mesh') if isinstance(c,u.SkeletalMeshComponent) else None
   row['components'].append({'name':c.get_name(),'asset':asset.get_path_name() if asset else None,'visible':c.is_visible(),'hidden':c.get_editor_property('hidden_in_game'),'parent':parent.get_name() if parent else None,'socket':str(c.get_attach_socket_name()),'relative':str(c.get_relative_transform())})
  result['actors'].append(row)
(O/'live_components.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True)
