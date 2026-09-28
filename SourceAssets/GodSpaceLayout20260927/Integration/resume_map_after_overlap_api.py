"""Resume this batch's unsaved layout after the first component API error."""
import json,runpy
from pathlib import Path
import unreal as u
root=Path(__file__).parent
data=json.loads((root/'placements.json').read_text(encoding='utf8'))
first=data['placements'][0];off=data['world_offset_cm']
target=u.Vector(*(first['location_m'][i]*100+off[i] for i in range(3)))
e=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if e.get_game_world():raise RuntimeError('PIE restarted; preserve the unsaved layout')
w=e.get_editor_world()
api=u.get_editor_subsystem(u.EditorActorSubsystem)
for a in u.GameplayStatics.get_all_actors_of_class(w,u.StaticMeshActor):
    c=a.static_mesh_component;p=a.get_actor_location()
    if not a.tags and c.static_mesh and c.static_mesh.get_path_name()==first['mesh'] and (p-target).length()<.1:
        api.destroy_actor(a)
runpy.run_path(str(root/'apply_map.py'),run_name='__main__',init_globals={'RESUME_OWNED_MAP':True})
