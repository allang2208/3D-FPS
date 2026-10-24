"""Read the current saved bay assemblies; no mutation or preview."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
def xyz(v):return [v.x,v.y,v.z]
rows={}
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 label=a.get_actor_label()
 if not label.startswith(('BAY_','Bay_','AP7_Bay','AP8_','AP9_')):continue
 meshes=[]
 for c in a.get_components_by_class(u.StaticMeshComponent):
  if not c.static_mesh:continue
  b=c.static_mesh.get_bounding_box()
  meshes.append(dict(mesh=c.static_mesh.get_path_name(),min=xyz(b.min),max=xyz(b.max),materials=[m.get_path_name() if m else None for m in c.get_materials()],slots=[str(x.material_slot_name) for x in c.static_mesh.get_editor_property('static_materials')],hidden=c.get_editor_property('hidden_in_game')))
 origin,ext=a.get_actor_bounds(False);rot=a.get_actor_rotation()
 rows[label]=dict(position=xyz(a.get_actor_location()),rotation=dict(pitch=rot.pitch,yaw=rot.yaw,roll=rot.roll),scale=xyz(a.get_actor_scale3d()),bounds_center=xyz(origin),bounds_extent=xyz(ext),meshes=meshes)
(R/'bay_before.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('AP15_BAY_READ',len(rows))
