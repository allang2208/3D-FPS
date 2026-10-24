"""Install only the owned exterior layer, preserving the furnished apartment."""
from pathlib import Path
from datetime import datetime
import sys,json,shutil,traceback
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
E=u.EditorAssetLibrary
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)

def load(path):
 obj=u.load_asset(path)
 if not obj:raise RuntimeError('Missing saved bay asset '+path)
 return obj

def apply_saved_background(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong map')
 assets=json.loads((ROOT/'assets_saved.json').read_text())
 if assets['stage']!='assets_saved':raise RuntimeError('Finish asset import before map installation')
 # Resolve all dependencies before altering the existing exterior.
 manifest=json.loads((ROOT/'assembly.json').read_text())
 meshes={row['key']:load(row['asset']) for row in manifest['meshes']}
 sky=load(DEST+'/Materials/M_Bay_FarSky')
 actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
 retired=[]
 for actor in actors:
  if actor.actor_has_tag(OWNER):
   AA.destroy_actor(actor)
   continue
  if actor.get_actor_label() in {'Bay_NightEnvironment','CITY_blocks','CITY_bridges','CITY_fog','CITY_ground','CITY_horizon','CITY_signs','CITY_traffic'}:
   actor.modify();actor.set_actor_hidden_in_game(True);actor.set_actor_enable_collision(False)
   for c in actor.get_components_by_class(u.PrimitiveComponent):
    c.set_visibility(False);c.set_hidden_in_game(True);c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
   retired.append(actor.get_actor_label())
 placements=[]
 for row in manifest['meshes']:
  a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(),u.Rotator())
  a.set_actor_label('BAY_'+row['key']);a.set_folder_path('Apartment20261022/LayeredBay')
  a.set_editor_property('tags',[u.Name(OWNER)]);a.set_actor_enable_collision(False)
  c=a.static_mesh_component;c.set_static_mesh(meshes[row['key']]);c.set_mobility(u.ComponentMobility.STATIC)
  c.set_collision_profile_name('NoCollision');c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
  c.set_editor_property('cast_shadow',False)
  c.set_editor_property('affect_distance_field_lighting',False)
  c.set_editor_property('affect_dynamic_indirect_lighting',False)
  # Opposite-bank geometry retains screen-space reflections; offline city radiance
  # supplies the out-of-screen reflection without adding distant RT instances.
  c.set_editor_property('visible_in_ray_tracing',False)
  if row['key']=='Water':c.set_editor_property('bounds_scale',1.01)
  placements.append(dict(label=a.get_actor_label(),mesh=meshes[row['key']].get_path_name(),triangles=row['triangles']))
 a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(1000,0,170),u.Rotator())
 a.set_actor_label('BAY_FarEnvironment');a.set_folder_path('Apartment20261022/LayeredBay');a.set_editor_property('tags',[u.Name(OWNER)])
 a.set_actor_scale3d(u.Vector(120000,120000,120000));a.set_actor_enable_collision(False)
 c=a.static_mesh_component;c.set_static_mesh(load('/Engine/BasicShapes/Sphere.Sphere'));c.set_material(0,sky)
 c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name('NoCollision');c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
 c.set_editor_property('cast_shadow',False);c.set_editor_property('affect_distance_field_lighting',False)
 c.set_editor_property('affect_dynamic_indirect_lighting',False);c.set_editor_property('visible_in_ray_tracing',True)
 apartment_v3=PROJECT/'SourceAssets/CyberpunkApartmentRebuild20261022/RefinementV3'
 if (apartment_v3/'installed.json').exists():
  import runpy
  runpy.run_path(str(apartment_v3/'install_sky.py'))['apply_saved_sky'](world)
 return dict(placements=placements,sky=a.get_actor_label(),old_backdrop_disabled=retired,water_source=WATER_PARENT,
  far_cube_size=4096,reflection_cube_size=1024,new_light_actors=0,scene_captures=0,water_actor_tick=False,
  triangles=sum(row['triangles'] for row in manifest['meshes']),tests_run=False,game_run=False)

def main():
 report=dict(stage='preparing',map=MAP,tests_run=False,game_run=False,acceptance_rendered=False,editor_opened=False)
 def record():(ROOT/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 try:
  if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if editor and editor.get_game_world():raise RuntimeError('Preserve running game')
  dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
  if dirty:raise RuntimeError('Preserve unsaved maps '+str([p.get_path_name() for p in dirty]))
  previous=editor.get_editor_world() if editor else None
  previous_path=previous.get_path_name().split('.')[0] if previous else None
  backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
  src=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(src,backup/src.name)
  report['backup']=str(backup/src.name);record()
  world=previous if previous_path==MAP else u.EditorLoadingAndSavingUtils.load_map(MAP)
  if not world:raise RuntimeError('Cannot load apartment')
  report.update(apply_saved_background(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Map save failed')
  report['stage']='map_saved';record()
  (ROOT/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print('LAYERED_BAY_MAP_SAVED',MAP)
  if previous_path and previous_path!=MAP and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
   u.EditorLoadingAndSavingUtils.load_map(previous_path)
 except Exception:
  report['error']=traceback.format_exc();report['stage']='failed';record();raise
if __name__=='__main__':main()
