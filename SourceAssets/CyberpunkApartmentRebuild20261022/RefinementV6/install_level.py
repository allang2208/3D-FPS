"""Reuse hub weather, scale the saved scene once, and bind stable bay presentation."""
from pathlib import Path
from datetime import datetime
import json,runpy,shutil,traceback
import unreal as u
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'));ROOT=C['ROOT'];PROJECT=C['PROJECT'];BASE=C['BASE'];MAP=C['MAP'];HUB=C['HUB'];OWNER=C['OWNER'];SCALE_TAG=C['SCALE_TAG'];FACTOR=C['FACTOR']
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
WEATHER_CLASSES={
 '/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky.Ultra_Dynamic_Sky_C':'AP6_UDS_Sky',
 '/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Weather.Ultra_Dynamic_Weather_C':'AP6_UDS_Weather'}

def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing apartment environment '+path)
 return a
def add_tag(a,tag):
 tags=list(a.get_editor_property('tags'))
 if u.Name(tag) not in tags:tags.append(u.Name(tag))
 a.set_editor_property('tags',tags)
def scale_subject(a):
 return isinstance(a,u.PlayerStart) or a.get_actor_label().startswith(('AP_','Door_','BAY_')) or a.get_actor_label()=='CITY_our_tower'
def transform_scale(a,factor):
 p=a.get_actor_location();a.modify()
 a.set_actor_location(u.Vector(p.x*factor,p.y*factor,p.z if isinstance(a,u.PlayerStart) else p.z*factor),False,False)
 if not isinstance(a,u.PlayerStart):a.set_actor_scale3d(a.get_actor_scale3d()*factor)
 for c in a.get_components_by_class(u.LocalLightComponent):
  c.set_intensity(c.get_editor_property('intensity')*factor*factor)
  for name in ['attenuation_radius','max_draw_distance','max_distance_fade_range']:
   value=c.get_editor_property(name)
   if value>0:c.set_editor_property(name,value*factor)
  if isinstance(c,u.RectLightComponent):
   for name in ['source_width','source_height']:c.set_editor_property(name,c.get_editor_property(name)*factor)
def restore_before_refinement(world):
 """Older layout installers author at the pre-V6 scale; normalize before they patch."""
 next_revision=ROOT.parent/'RefinementV7'
 if (next_revision/'installed.json').exists():runpy.run_path(str(next_revision/'install_level.py'))['restore_before_refinement'](world)
 restored=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  if a.actor_has_tag(SCALE_TAG) and scale_subject(a):
   transform_scale(a,1/FACTOR);a.set_editor_property('tags',[t for t in a.get_editor_property('tags') if str(t)!=SCALE_TAG]);restored.append(a.get_actor_label())
 return restored
def apply_scale(world):
 changed=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  if not scale_subject(a) or a.actor_has_tag(SCALE_TAG) or isinstance(a,u.PostProcessVolume):continue
  transform_scale(a,FACTOR);add_tag(a,SCALE_TAG);changed.append(a.get_actor_label())
 settings=world.get_world_settings()
 settings.set_editor_property('kill_z',min(settings.get_editor_property('kill_z'),-26250.))
 return dict(relative_factor=FACTOR,interior_authored_actor_scale=1.50,scaled_actors=changed,player_size_changed=False,player_start_height_preserved=True)
def ensure_weather(world):
 sky_path='/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky.Ultra_Dynamic_Sky_C'
 weather_path='/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Weather.Ultra_Dynamic_Weather_C'
 desired=WEATHER_CLASSES
 actors=list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor))
 existing={a.get_class().get_path_name():a for a in actors if a.get_class().get_path_name() in desired}
 copied=[]
 if set(existing)!=set(desired):
  if existing:raise RuntimeError('Preserve partial authored weather pair')
  # Runtime level instancing loads a private /Temp copy without editor UI.
  # AActor::Rename transfers the actor and its components between level actor
  # lists. Moving the pair out of this disposable instance preserves all authored
  # properties without touching the source map or relying on GUnrealEd.
  target_level=world.get_world_settings().get_level()
  stream,loaded=u.LevelStreamingDynamic.load_level_instance(world,HUB,u.Vector(),u.Rotator(),load_as_temp_package=True)
  if not loaded or not stream:raise RuntimeError('Cannot instance hub weather donor')
  u.GameplayStatics.flush_level_streaming(world)
  donor_level=stream.get_loaded_level()
  copies=[a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor) if a.get_level()==donor_level and a.get_class().get_path_name() in desired]
  if len(copies)!=2:raise RuntimeError('Cannot load authored hub weather pair')
  print('AP6_HUB_WEATHER_TRANSFERRING')
  for a in copies:
   if not a.rename(desired[a.get_class().get_path_name()],target_level):raise RuntimeError('Cannot transfer hub weather actor')
   cls=a.get_class().get_path_name();existing[cls]=a;a.set_actor_label(desired[cls]);a.set_folder_path('Apartment20261022/Weather');add_tag(a,OWNER)
   a.set_actor_location(u.Vector(),False,False);a.set_actor_scale3d(u.Vector(1,1,1));copied.append(cls)
  stream.set_is_requesting_unload_and_removal(True);u.GameplayStatics.flush_level_streaming(world)
  print('AP6_HUB_WEATHER_INSTALLED')
 sky=existing[sky_path];weather=existing[weather_path]
 sky.set_editor_property('Animate Time Of Day',False);sky.set_editor_property('Time Speed',0.)
 sky.set_editor_property('Replicate Time Of Day To Clients',False)
 weather.set_editor_property('Begin Play Weather Is Random',False)
 # Existing FPSWeatherManager/UDSBridge discovers these authored actors on all maps.
 # No new clock, weather scheduler or global bridge configuration is introduced.
 retired=[]
 for a in actors:
  if isinstance(a,(u.DirectionalLight,u.SkyLight,u.SkyAtmosphere,u.ExponentialHeightFog,u.VolumetricCloud)):
   a.modify();a.set_actor_hidden_in_game(True)
   for c in a.get_components_by_class(u.SceneComponent):c.set_visibility(False,True)
   retired.append(a.get_actor_label())
 return dict(donor_map=HUB,copied_classes=copied,sky=sky.get_path_name(),weather=weather.get_path_name(),
  authority='existing FPSWeatherManager and FPSUDSBridgeComponent',independent_clock=False,retired_environment=retired)
def apply_environment(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong environment target')
 receipt=json.loads((ROOT/'assets_saved.json').read_text());manifest=json.loads((ROOT/'far-assembly.json').read_text())
 if receipt['stage']!='assets_saved':raise RuntimeError('V6 environment assets not saved')
 mats={k:load(path) for k,path in receipt['materials'].items()};water=load(receipt['water']['path'])
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 retired=[]
 for label in ['BAY_FarEnvironment','Bay_NightEnvironment']:
  a=actors.get(label)
  if a:
   a.modify();a.set_actor_hidden_in_game(True);a.set_actor_enable_collision(False)
   for c in a.get_components_by_class(u.PrimitiveComponent):c.set_visibility(False);c.set_hidden_in_game(True)
   retired.append(label)
 for row in manifest['meshes']:
  label='BAY_'+row['key'];a=actors.get(label)
  if not a:
   a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(),u.Rotator());a.set_actor_label(label);actors[label]=a
  a.modify();add_tag(a,OWNER);add_tag(a,'CyberpunkApartment.LayeredBay20261022');a.set_folder_path('Apartment20261022/LayeredBay')
  comp=a.static_mesh_component;comp.set_static_mesh(load(row['asset']));comp.set_editor_property('override_materials',[])
  comp.set_mobility(u.ComponentMobility.STATIC);comp.set_collision_profile_name('NoCollision');comp.set_editor_property('cast_shadow',False)
  comp.set_editor_property('affect_distance_field_lighting',False);comp.set_editor_property('affect_dynamic_indirect_lighting',False);comp.set_editor_property('visible_in_ray_tracing',False)
 changed=0
 for label,a in actors.items():
  if not label.startswith('BAY_') or not isinstance(a,u.StaticMeshActor):continue
  comp=a.static_mesh_component
  if label=='BAY_Water':comp.set_material(0,water);continue
  if label=='BAY_FarEnvironment':continue
  for i,s in enumerate(comp.static_mesh.get_editor_property('static_materials')):
   key=str(s.material_slot_name)
   if key in mats:comp.set_material(i,mats[key]);changed+=1
 return dict(retired_fixed_skies=retired,far_geometry_actors=len(manifest['meshes']),daylight_material_slots=changed,
  water=water.get_path_name(),weather=ensure_weather(world))
def apply_upgrade(world):
 environment=apply_environment(world);scale=apply_scale(world)
 report=dict(environment=environment,scale=scale)
 next_revision=ROOT.parent/'RefinementV7'
 if (next_revision/'installed.json').exists():report['v7']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 report=dict(stage='preparing',map=MAP,game_run=False,rendered=False,performance_measured=False)
 def record():(ROOT/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 try:
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if editor and editor.get_game_world():raise RuntimeError('Preserve running game')
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
  backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
  disk=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(disk,backup/disk.name);report['backup']=str(backup/disk.name);record()
  world=u.EditorLoadingAndSavingUtils.load_map(MAP);report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Apartment V6 map save failed')
  report['stage']='map_saved';record();(ROOT/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print('APARTMENT_V6_MAP_SAVED',len(report['scale']['scaled_actors']))
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
