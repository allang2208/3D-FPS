from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));MAP=C['MAP'];PROJECT=C['PROJECT'];BASE=C['BASE'];TAG='Apartment.V16.Streets'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong apartment target')
 assets=json.loads((R/'assets_saved.json').read_text());actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)};aa=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
 if assets['stage']!='assets_saved':raise RuntimeError('Finish V16 assets first')
 def mark(a):
  a.modify();ts=list(a.get_editor_property('tags'))
  if u.Name(TAG) not in ts:ts.append(u.Name(TAG));a.set_editor_property('tags',ts)
 for b in C['BOARDS']:
  a=actors['AP8_Advertisement_'+b['key']];mark(a);c=a.static_mesh_component;c.set_material(0,u.load_asset(assets['materials']['MI_AP16_'+b['key']]));c.set_editor_property('streaming_distance_multiplier',2.)
 actors['BAY_Water'].modify();actors['BAY_Water'].static_mesh_component.set_material(0,u.load_asset(assets['materials']['MI_AP16_Water']))
 motion=[]
 for b in C['SEARCH']:
  for suffix in ['Base','Head','Beam']:
   a=actors['AP9_'+b['key']+'_'+suffix];mark(a);c=a.static_mesh_component
   for i,old in enumerate(c.get_materials()):
    if not isinstance(old,u.MaterialInstanceConstant) or not any(k in old.get_name() for k in ['Yoke','Head','Lens','Beam']):continue
    name='MI_AP16_'+b['key']+'_'+suffix+'_'+str(i);p=BASE+'/Materials/'+name
    m=u.load_asset(p) if E.does_asset_exist(p) else A.duplicate_asset(name,BASE+'/Materials',old)
    values=dict(Tilt=b['tilt'],TiltSweep=b['tilt_sweep'],Yaw=b['yaw'],YawSweep=b['yaw_sweep'],Period=b['period'],Phase=b['phase'])
    if suffix=='Base':values.update(Tilt=0,TiltSweep=0)
    for k,v in values.items():L.set_material_instance_scalar_parameter_value(m,k,float(v))
    L.update_material_instance(m)
    if not E.save_loaded_asset(m,False):raise RuntimeError('Motion material save')
    c.set_material(i,m)
   if suffix=='Beam':c.set_editor_property('bounds_scale',1.35)
   motion.append(a.get_actor_label())
 made=[]
 for key,row in assets['meshes'].items():
  label='AP16_'+key;a=actors.get(label)
  if not a:a=aa.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label)
  mark(a);a.set_folder_path('Apartment20261022/HarborStreets');a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));a.set_actor_enable_collision(False)
  c=a.static_mesh_component;c.set_static_mesh(u.load_asset(row['path']));c.set_editor_property('override_materials',[]);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False);c.set_editor_property('visible_in_ray_tracing',False);c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('receives_decals',False)
  if row['traffic']:c.set_editor_property('bounds_scale',1.08)
  made.append(label)
 report=dict(actors=made,searchlight_components=motion,searchlight_trajectories=C['SEARCH'],advertisement_materials=[assets['materials']['MI_AP16_'+b['key']] for b in C['BOARDS']],cars=36,car_types=3,trees=94,junctions=3,traffic_speed_mps=C['TRAFFIC_SPEED'],traffic_cpu_tick=False,additional_dynamic_lights=0,display_sampling='gradient sampling; bounded resident shared atlas; reduced camera-unrelated UV motion',water_emitter_motion_synchronized=True)
 next_revision=R.parent/'RefinementV17'
 if (next_revision/'installed.json').exists():report['v17']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if s and s.get_game_world():raise RuntimeError('Preserve play session; stop and save first')
 if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
 backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
 world=u.EditorLoadingAndSavingUtils.load_map(MAP);report=apply_upgrade(world)
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Map save failed')
 report.update(stage='map_saved',saved_at=datetime.now().astimezone().isoformat(),game_tested=False,backup=str(backup));(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP16_MAP_SAVED')
if __name__=='__main__':main()
