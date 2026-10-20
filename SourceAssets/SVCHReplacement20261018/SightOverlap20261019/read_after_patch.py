"""Read only: confirm the live SVCh no longer owns independent M4 sights."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report={'world':world.get_path_name() if world else None,'svch_instances':[]}
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for gun in actor.get_components_by_class(u.SkeletalMeshComponent):
   mesh=gun.get_skeletal_mesh_asset()
   if not mesh or not mesh.get_path_name().startswith('/Game/Weapons/SVCH/'):continue
   children=[]
   for c in actor.get_components_by_class(u.StaticMeshComponent):
    if c.get_attach_parent()!=gun:continue
    m=c.static_mesh
    if m and m.get_path_name().startswith('/Game/Weapons/M4FoldingSights/'):
     children.append({'component':c.get_name(),'mesh':m.get_path_name(),'visible':c.is_visible()})
   report['svch_instances'].append({'component':gun.get_path_name(),'mesh':mesh.get_path_name(),'visible':gun.is_visible(),'extra_M4_sights':children})
report['no_duplicate_M4_components']=bool(report['svch_instances']) and all(not r['extra_M4_sights'] for r in report['svch_instances'])
(O/'after_patch.json').write_text(json.dumps(report,indent=2))
u.log('SVCH_SIGHT_DUPLICATE_READ '+json.dumps(report))
