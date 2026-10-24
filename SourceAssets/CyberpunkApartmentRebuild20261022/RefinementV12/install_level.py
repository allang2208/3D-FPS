"""Install only the requested TV, apartment door policy and fixture lighting."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));MAP=C['MAP'];PROJECT=C['PROJECT']
AA=u.get_editor_subsystem(u.EditorActorSubsystem)

def fixture_owner(key):
 if key.startswith('Dining_') or key=='Balcony':return 'AP_PracticalLights'
 if key=='Landing':return 'AP_EntryLanding'
 if key.startswith('Gym_'):return 'AP_Gym_Fixtures'
 if key.startswith('BathV5_'):return 'AP_BathLighting'
 if key.startswith('Corridor_'):return None
 return 'AP_Lighting_'+key

def tag(a):
 a.modify();tags=list(a.get_editor_property('tags'))
 if u.Name(C['OWNER']) not in tags:tags.append(u.Name(C['OWNER']))
 a.set_editor_property('tags',tags)

def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong apartment map')
 assets=json.loads((R/'assets_saved.json').read_text());compiled=json.loads((R/'material-compilation.json').read_text())
 if assets['stage']!='assets_saved' or compiled['stage']!='compiled_and_saved':raise RuntimeError('Finish fixture asset production before map save')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 report=dict(tv={},doors=[],lights=[],fixture_meshes=[],preserved_external_light_bindings=[],game_run=False,visual_acceptance=False,performance_measured=False)
 # Absolute dimensions derived from the existing 340 x 191.25 cm body.
 tv=actors[C['TV']['actor']];tag(tv)
 report['tv']['before']=dict(location=list(tv.get_actor_location().to_tuple()),scale=list(tv.get_actor_scale3d().to_tuple()))
 tv.static_mesh_component.set_mobility(u.ComponentMobility.MOVABLE)
 tv.set_actor_location(u.Vector(*C['TV']['location']),False,False);tv.set_actor_rotation(u.Rotator(yaw=C['TV']['yaw']),False);tv.set_actor_scale3d(u.Vector(*C['TV']['scale']))
 tv.static_mesh_component.set_mobility(u.ComponentMobility.STATIC)
 report['tv']['after']=C['TV'];report['tv']['reused_mesh']=tv.static_mesh_component.static_mesh.get_path_name()
 # The shared native fix gives zero its documented 'remain open' meaning.
 for row in C['SOURCE']['doors']:
  a=actors[row['actor']];tag(a);a.set_editor_property('auto_close_seconds',0.)
  report['doors'].append(dict(actor=a.get_actor_label(),auto_close_seconds=a.get_editor_property('auto_close_seconds'),manual_toggle_retained=True))
 atmosphere=actors['AP7_Atmosphere'];tag(atmosphere)
 bindings=[]
 for b in atmosphere.get_editor_property('lights'):
  a=b.get_editor_property('actor')
  if a and not a.get_actor_label().startswith('AP_Light_'):
   bindings.append(b);report['preserved_external_light_bindings'].append(a.get_actor_label())
 for row in C['LIGHTS']:
  owner=fixture_owner(row['key']);old_fixture=actors.get(owner) if owner else None
  if owner and not old_fixture:raise RuntimeError('Missing physical fixture '+owner)
  if row['cover']:
   key=row['key'].replace('.','p').replace('-','m');mesh=assets['meshes'][key]
   a=actors.get(row['fixture'])
   if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(row['fixture']);actors[row['fixture']]=a
   tag(a);a.set_folder_path('Apartment20261022/PrecisionLighting');c=a.static_mesh_component
   c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(u.load_asset(mesh['path']));c.set_editor_property('override_materials',[])
   a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));c.set_mobility(u.ComponentMobility.STATIC)
   c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);a.set_actor_enable_collision(False)
   c.set_visibility(True);c.set_hidden_in_game(False);a.set_actor_hidden_in_game(False);c.set_editor_property('cast_shadow',True)
   # The authored RectLight supplies the emission, avoiding extra emissive GI noise.
   c.set_editor_property('affect_dynamic_indirect_lighting',False);c.set_editor_property('affect_distance_field_lighting',False)
   c.set_editor_property('visible_in_ray_tracing',True)
   report['fixture_meshes'].append(a.get_actor_label())
  a=actors.get(row['actor'])
  if not a:a=AA.spawn_actor_from_class(u.RectLight,u.Vector());a.set_actor_label(row['actor']);actors[row['actor']]=a
  tag(a);a.set_folder_path('Apartment20261022/Lighting');c=a.get_component_by_class(u.RectLightComponent)
  if not c:raise RuntimeError('Expected directional rectangular source '+row['actor'])
  # UE +X emits, source width uses local Y: yaw=90 places the long axis on world X.
  c.set_mobility(u.ComponentMobility.MOVABLE)
  c.set_world_location(u.Vector(*(v*100 for v in row['source'])),False,False)
  c.set_world_rotation(u.Rotator(pitch=-90.,yaw=90.,roll=0.),False,False)
  c.set_world_scale3d(u.Vector(1,1,1))
  c.set_editor_property('source_width',row['width']*100);c.set_editor_property('source_height',row['depth']*100)
  c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(row['power'])
  c.set_light_color(u.LinearColor(1,1,1,1));c.set_editor_property('use_temperature',True);c.set_editor_property('temperature',row['temperature'])
  c.set_editor_property('cast_shadows',True);c.set_editor_property('attenuation_radius',row['radius'])
  c.set_editor_property('barn_door_angle',70.);c.set_editor_property('barn_door_length',8.)
  c.set_editor_property('indirect_lighting_intensity',.85);c.set_editor_property('volumetric_scattering_intensity',.15)
  c.set_editor_property('max_draw_distance',2400.);c.set_editor_property('max_distance_fade_range',450.)
  c.set_visibility(True);c.set_hidden_in_game(False);a.set_actor_hidden_in_game(False)
  b=u.ApartmentLightBinding();b.set_editor_property('actor',a);b.set_editor_property('base_intensity',row['power']);b.set_editor_property('day_factor',row['day']);b.set_editor_property('night_factor',row['night']);bindings.append(b)
  # Requested per-light source inspection, read from the final components.
  r=dict(actor=a.get_actor_label(),original_fixture=owner,new_fixture=row['fixture'] if row['cover'] else None,
         source_cm=list(c.get_world_location().to_tuple()),forward=list(c.get_forward_vector().to_tuple()),width_axis=list(c.get_right_vector().to_tuple()),
         source_width_cm=c.get_editor_property('source_width'),source_height_cm=c.get_editor_property('source_height'),
         emitter_bottom_cm=row['diffuser_bottom']*100,emitter_gap_cm=row['diffuser_bottom']*100-c.get_world_location().z,
         lumens=c.get_editor_property('intensity'),temperature=c.get_editor_property('temperature'),radius_cm=c.get_editor_property('attenuation_radius'),
         shadows=c.get_editor_property('cast_shadows'),day_factor=row['day'],night_factor=row['night'],new_light=row['new'])
  if old_fixture:r['original_fixture_scale']=list(old_fixture.get_actor_scale3d().to_tuple())
  if row['old']:r['before']={k:row['old'].get(k) for k in ['location','right','up','source_width','source_height','cast_shadows','temperature','attenuation_radius']}
  report['lights'].append(r)
 atmosphere.set_editor_property('lights',bindings)
 report.update(new_lights=2,total_apartment_lights=len(C['LIGHTS']),new_tick_actors=0,new_textures=0,global_exposure_changed=False,
               exterior_weather_water_ads_changed=False,source_geometry='final UE world metres; 1.0 actor scale',reused_textures=assets['reused_textures'])
 next_revision=R.parent/'RefinementV13'
 if (next_revision/'installed.json').exists():report['v13']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report

def main():
 report=dict(stage='preparing',map=MAP,game_run=False)
 try:
  s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if s and s.get_game_world():raise RuntimeError('Preserve active play world')
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
  backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
  shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
  world=s.get_editor_world() if s else None
  if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
  report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Apartment map save failed')
  report.update(stage='map_saved',backup=str(backup),saved_at=datetime.now().astimezone().isoformat())
  (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print('AP12_MAP_SAVED',len(report['lights']),len(report['doors']))
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();raise
 finally:(R/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':main()
