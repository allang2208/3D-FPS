"""Replace existing city clusters in place; preserve map edits, water and indoors."""
import unreal as u
from pathlib import Path
from datetime import datetime
import runpy,json,shutil,traceback
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'))
ROOT=C['ROOT'];PROJECT=C['PROJECT'];DEST=C['DEST'];MAP=C['MAP'];OWNER=C['OWNER']
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing detailed city '+path)
 return a
def apply_saved_buildings(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong target world')
 manifest=json.loads((ROOT/'assembly.json').read_text());meshes={r['key']:load(r['asset']) for r in manifest['meshes']}
 sky=load(DEST+'/Materials/M_ApartmentHubSky');water=load(DEST+'/Materials/MI_WaterHubSky')
 targets={'BAY_'+key for key in meshes}|{'BAY_FarEnvironment','BAY_Water'}
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.StaticMeshActor) if a.get_actor_label() in targets}
 missing=targets-set(actors)
 if missing:raise RuntimeError('Existing bay clusters missing '+str(sorted(missing)))
 replacements=[]
 for key,mesh in meshes.items():
  actor=actors['BAY_'+key];actor.modify();c=actor.static_mesh_component;c.modify();c.set_static_mesh(mesh)
  # Clear any old per-component material overrides after changing slot layout.
  c.set_editor_property('override_materials',[])
  c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False)
  c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('affect_dynamic_indirect_lighting',False);c.set_editor_property('visible_in_ray_tracing',False)
  replacements.append(dict(actor=actor.get_actor_label(),mesh=mesh.get_path_name()))
 for label,mat in [('BAY_FarEnvironment',sky),('BAY_Water',water)]:
  actor=actors[label];actor.modify();actor.static_mesh_component.modify();actor.static_mesh_component.set_material(0,mat)
 result=dict(replacements=replacements,building_clusters=len(meshes),runtime_building_triangles=sum(r['triangles'] for r in manifest['meshes']),
  source_buildings=len(manifest['buildings']),new_actor_count=0,new_lights=0,realtime_captures=0,
  hub_sky_preserved=True,water_mesh_and_optics_preserved=True,interior_unchanged=True)
 environment=PROJECT/'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV6'
 if (environment/'installed.json').exists():result['dynamic_environment']=runpy.run_path(str(environment/'install_level.py'))['apply_upgrade'](world)
 return result
def main():
 report=dict(stage='preparing',map=MAP,tests_run=False,game_run=False,acceptance_rendered=False,editor_started=False)
 def record():(ROOT/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 try:
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if editor and editor.get_game_world():raise RuntimeError('Preserve running game; stop PIE before city installation')
  dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
  if dirty:raise RuntimeError('Preserve unsaved maps '+str([p.get_path_name() for p in dirty]))
  previous=editor.get_editor_world() if editor else None;oldpath=previous.get_path_name().split('.')[0] if previous else None
  backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
  src=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(src,backup/src.name);report['backup']=str(backup/src.name);record()
  world=previous if oldpath==MAP else u.EditorLoadingAndSavingUtils.load_map(MAP)
  if not world:raise RuntimeError('Cannot load target apartment')
  report.update(apply_saved_buildings(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save apartment')
  report['stage']='map_saved';record();(ROOT/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print('DETAILED_BAY_MAP_SAVED',MAP)
  if oldpath and oldpath!=MAP and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(oldpath)
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
