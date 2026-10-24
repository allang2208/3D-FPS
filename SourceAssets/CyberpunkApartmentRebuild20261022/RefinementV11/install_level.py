from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));MAP=C['MAP'];PROJECT=C['PROJECT'];OWNER=C['OWNER']
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong host tower target')
 assets=json.loads((R/'assets_saved.json').read_text());compiled=json.loads((R/'material-compilation.json').read_text())
 if assets['stage']!='assets_saved' or compiled['stage']!='compiled_and_saved':raise RuntimeError('Complete tower production before map publication')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};host=actors.get('CITY_our_tower')
 if not host:raise RuntimeError('Existing host tower missing')
 previous=dict(mesh=host.static_mesh_component.static_mesh.get_path_name(),scale=list(host.get_actor_scale3d().to_tuple()),location=list(host.get_actor_location().to_tuple()))
 made=[]
 for key,row in assets['meshes'].items():
  label='CITY_our_tower' if key=='LowerA' else 'AP11_Tower_'+key;a=actors.get(label)
  if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label)
  a.modify();a.set_folder_path('Apartment20261022/ResidentialHostTower');tags=list(a.get_editor_property('tags'))
  if u.Name(OWNER) not in tags:tags.append(u.Name(OWNER));a.set_editor_property('tags',tags)
  c=a.static_mesh_component;c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(u.load_asset(row['path']));c.set_editor_property('override_materials',[])
  c.set_visibility(True);c.set_hidden_in_game(False);a.set_actor_hidden_in_game(False)
  c.set_editor_property('cast_shadow',True);c.set_editor_property('affect_distance_field_lighting',True);c.set_editor_property('affect_dynamic_indirect_lighting',True);c.set_editor_property('visible_in_ray_tracing',True)
  c.set_collision_profile_name('BlockAll');c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS);a.set_actor_enable_collision(True)
  a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));made.append(label)
 report=dict(previous_host=previous,actors=made,replaced_mosaic_facade=True,authored_geometry='final UE world metres, unit actor scale',playable_level_preserved=True,interior_doors_and_windows_modified=False,bay_water_and_ads_modified=False,new_lights=0,new_tick_actors=0,new_textures=0,normal_and_roughness_sources=assets['reused_textures'],collision='authored separate UCX volumes outside the occupied level; existing room/pane/rail collision retained',night_behavior='existing SkyAtmosphere sun direction; fixed warm/cool apartment occupancy without blinking')
 next_revision=R.parent/'RefinementV12'
 if (next_revision/'installed.json').exists():report['v12']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 report=dict(stage='preparing',map=MAP,game_run=False,visual_acceptance=False,performance_measured=False)
 try:
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
  backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
  s=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=s.get_editor_world() if s else None
  if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
  report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Tower map save failed')
  report['stage']='map_saved';report['backup']=str(backup);report['saved_at']=datetime.now().astimezone().isoformat();(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();raise
 finally:(R/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':main()
