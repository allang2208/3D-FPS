"""Requested doorway diagnosis: saved LOD0 geometry and actor state, no game/render."""
import json
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem) or u.new_object(u.UnrealEditorSubsystem)
meshes_only=globals().get('MESHES_ONLY',False)
if not meshes_only and (editor.get_game_world() or u.EditorLoadingAndSavingUtils.get_dirty_map_packages()):
 raise RuntimeError('Preserve active play or unsaved maps')
prior=editor.get_editor_world().get_path_name().split('.')[0] if editor.get_editor_world() else None
if meshes_only:
 catalog=json.loads((ROOT.parent/'DungeonFacilityFlow20261007/Config/catalog.json').read_text('utf8'))
else:
 world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
 gen=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)[0]
 catalog=json.loads(gen.get_editor_property('module_catalog_json'))
ids={'MedicalDoctorOffice','AbandonedIsolationWard','AbandonedAnatomyTheatre','Transit','Threshold'}
modules=[m for m in catalog['modules'] if m['id'] in ids]
report=dict(modules=modules,meshes={},maps={},rendered=False,gameplay_tested=False)
paths=set()
for m in modules:
 for p in m['parts']:
  name=p['mesh'].rsplit('/',1)[-1]
  if any(k in name for k in ('_Walls','_Frames','_Trim','_WallFinish','_GlassDoorFrame','_Shell','_Ceilings','_Floor')):
   paths.add(p['mesh'])
 for a in m.get('runtime_actors',[]):
  if a['type'] in ('glass_door','solid_door'):paths.add(a['leaf'])
for path in sorted(paths):
 mesh=u.load_asset(path);handle=u.ModelingService.load_mesh_from_static_mesh(path,0).handle
 if handle<0:raise RuntimeError('Unable to read '+path)
 try:
  dm=u.ModelingService.get_dynamic_mesh(handle);_,indices,_=dm.get_all_triangle_i_ds();tri=[]
  for tid in indices.convert_index_list_to_array():
   ok,a,b,c=dm.get_triangle_positions(int(tid))
   if not ok:raise RuntimeError('Triangle unavailable')
   tri.append([[p.x,p.y,p.z] for p in (a,b,c)])
  bounds=mesh.get_bounding_box()
  report['meshes'][path]=dict(triangles=tri,min=[bounds.min.x,bounds.min.y,bounds.min.z],max=[bounds.max.x,bounds.max.y,bounds.max.z])
 finally:u.ModelingService.release_mesh(handle)
for target in (() if meshes_only else ('/Game/GameMaps/Design/L_MedicalDoctorOffice_Subject','/Game/GameMaps/Design/L_Hospital_Theme_Subject')):
 world=u.EditorLoadingAndSavingUtils.load_map(target);rows=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  label=a.get_actor_label();tags=[str(t) for t in a.tags]
  if not any(k in label.lower() for k in ('door','frame','cap')) and not isinstance(a,u.WardGlassDoor):continue
  row=dict(label=label,tags=tags,position=[a.get_actor_location().x,a.get_actor_location().y,a.get_actor_location().z],components=[])
  for c in a.get_components_by_class(u.StaticMeshComponent):
   mesh=c.static_mesh
   if not mesh:continue
   row['components'].append(dict(name=c.get_name(),mesh=mesh.get_path_name().split('.')[0],visible=c.is_visible()))
  rows.append(row)
 report['maps'][target]=rows
(ROOT/'Receipts'/globals().get('OUTPUT_NAME','doorways-before.json')).write_text(json.dumps(report,ensure_ascii=False),encoding='utf8')
if not meshes_only and prior and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(prior)
print('DOORWAYS_SAVED_SOURCE_READ',len(paths),flush=True)
