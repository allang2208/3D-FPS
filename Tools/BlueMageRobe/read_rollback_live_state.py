import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/BlueMageRobe20261018/ClothRollback20261019'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_game_world();report={'pie':bool(world),'parts':[],'read_only':True}
if world:
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
  for c in a.get_components_by_class(u.SkeletalMeshComponent):
   mesh=c.get_skeletal_mesh_asset()
   if mesh and 'BlueMageRobe' in mesh.get_path_name():
    report['parts'].append({'actor':a.get_name(),'component':c.get_name(),'mesh':mesh.get_path_name(),'visible':c.is_visible(),'hidden':c.get_editor_property('hidden_in_game'),'cloth_suspended':c.is_clothing_simulation_suspended()})
(O/'editor-state-after-rollback.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
