"""Replace the existing three traffic batches in the formal apartment map only."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,shutil
R=Path(__file__).resolve().parent;PROJECT=R.parents[1];MAP='/Game/GameMaps/L_CyberpunkApartment'

def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong target world')
 report=json.loads((R/'assets_saved.json').read_text(encoding='utf8'))
 if report['stage']!='assets_saved':raise RuntimeError('Finish vehicle asset production first')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 labels=['AP16_Traffic_'+k for k in ['Coupe','Shuttle','Freight']]
 if any(k not in actors for k in labels):raise RuntimeError('Existing traffic batch missing; leave scene intact')
 changed=[];prior=[]
 for kind,row in report['meshes'].items():
  label='AP16_Traffic_'+kind if kind!='HeadlightPools' else 'CT_Traffic_HeadlightPools'
  a=actors.get(label)
  if a:prior.append(dict(actor=label,mesh=a.static_mesh_component.static_mesh.get_path_name(),materials=[m.get_path_name() if m else None for m in a.static_mesh_component.get_materials()]))
  else:
   aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
   a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label)
  a.modify();c=a.static_mesh_component;c.modify();c.set_static_mesh(u.load_asset(row['path']));c.set_editor_property('override_materials',[])
  a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_enable_collision(False);a.set_folder_path('Apartment20261022/HarborStreets')
  c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('receives_decals',False);c.set_editor_property('bounds_scale',1.08)
  tags=list(a.get_editor_property('tags'));tag=u.Name('Apartment.TrafficUpgrade20261026')
  if tag not in tags:tags.append(tag);a.set_editor_property('tags',tags)
  changed.append(label)
 return dict(actors=changed,previous_bindings=prior,cars=36,types=['rounded fastback','urban SUV','delivery van'],night_lamps='sun direction dusk fade; white low beam, DRL, red tail, amber side markers',road_lighting='GPU animated soft additive footprints, not shadow-casting light actors',new_cpu_tick_actors=0,new_dynamic_lights=0)

def main(background=False):
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 world=editor.get_editor_world() if editor else None
 if not background:
  level=u.get_editor_subsystem(u.LevelEditorSubsystem)
  if level.is_in_play_in_editor():raise RuntimeError('End current PIE before saving traffic')
  if not world or world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Preserve existing editor map')
 else:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
 backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
 shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
 report=apply_upgrade(world)
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Formal apartment map not saved')
 report.update(stage='map_saved',saved_at=datetime.now().astimezone().isoformat(),map=MAP,backup=str(backup),game_tested=False,rendered=False)
 (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('TRAFFIC_FORMAL_MAP_SAVED',report['actors'])
if __name__=='__main__':main()
