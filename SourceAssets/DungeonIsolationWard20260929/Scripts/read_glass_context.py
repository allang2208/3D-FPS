"""Read only the reported ward door/glass context; do not load maps or start a game."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=ue.get_game_world() or ue.get_editor_world()
result={'world':world.get_path_name() if world else None,'glass':[],'fixtures':[]}
if world and 'AbandonedIsolationWard' in world.get_path_name():
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh:continue
   mats=[m.get_path_name() if m else None for m in (c.get_material(i) for i in range(c.get_num_materials()))]
   entry=dict(actor=a.get_name(),mesh=c.static_mesh.get_path_name(),materials=mats,collision=str(c.get_collision_enabled()))
   if any(t in str(entry).lower() for t in ('glass','door','portal')):result['glass'].append(entry)
   if 'CeilingLamp' in entry['mesh'] and not result['fixtures']:result['fixtures'].append(entry)
(ROOT/'Receipts/glass-context-v2.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
