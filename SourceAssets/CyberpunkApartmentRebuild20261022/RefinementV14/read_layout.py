"""Read saved apartment furniture geometry for layout and motion authoring."""
import json
from pathlib import Path
import unreal as u
R=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
def xyz(v):return [v.x,v.y,v.z]
def rot(r):return dict(pitch=r.pitch,yaw=r.yaw,roll=r.roll)
rows={}
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 label=a.get_actor_label()
 if not (label.startswith(('AP_Bed','AP_Living','AP_Container_Bed','AP_Container_Living','AP_Planter','AP_Foliage','Door_','AP7_Bed'))):continue
 cs=[]
 for c in a.get_components_by_class(u.StaticMeshComponent):
  if not c.static_mesh:continue
  b=c.static_mesh.get_bounding_box()
  cs.append(dict(name=c.get_name(),mesh=c.static_mesh.get_path_name(),min=xyz(b.min),max=xyz(b.max),position=xyz(c.get_world_location()),rotation=rot(c.get_world_rotation()),scale=xyz(c.get_world_scale()),materials=[m.get_path_name() if m else None for m in c.get_materials()]))
 origin,extent=a.get_actor_bounds(False)
 rows[label]=dict(position=xyz(a.get_actor_location()),rotation=rot(a.get_actor_rotation()),scale=xyz(a.get_actor_scale3d()),bounds_center=xyz(origin),bounds_extent=xyz(extent),components=cs)
 if label=='AP_Living_Sofa':
  dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(a.static_mesh_component.static_mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
  if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Sofa source geometry unavailable')
  _,pv,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
  _,tv,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
  (R/'sofa_geometry.json').write_text(json.dumps(dict(positions=[xyz(v) for v in u.GeometryScript_List.convert_vector_list_to_array(pv)],triangles=[xyz(t) for t in u.GeometryScript_List.convert_triangle_list_to_array(tv)])))
(R/'layout_before.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('AP14_LAYOUT_READ',len(rows))
