"""Incremental V13 map binding. Keep existing furniture/container IDs and scenery."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));MAP=C['MAP'];PROJECT=C['PROJECT']
AA=u.get_editor_subsystem(u.EditorActorSubsystem)

def tag(a):
 a.modify();tags=list(a.get_editor_property('tags'))
 if u.Name(C['OWNER']) not in tags:tags.append(u.Name(C['OWNER']))
 a.set_editor_property('tags',tags)

def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong V13 apartment target')
 assets=json.loads((R/'assets_saved.json').read_text());compiled=json.loads((R/'material-compilation.json').read_text())
 if assets['stage']!='assets_saved' or compiled['stage']!='compiled_and_saved':raise RuntimeError('Finish V13 assets and shader production')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 meshes={k:u.load_asset(v['path']) for k,v in assets['meshes'].items()};mats={k:u.load_asset(v) for k,v in assets['materials'].items()}
 report=dict(actors=[],controls=[],light_bindings=[],rooms=[],portals=[],screen_slots=[],game_run=False,rendered=False,performance_measured=False)
 def static(label,key):
  a=actors.get(label)
  if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector());a.set_actor_label(label);actors[label]=a
  tag(a);a.set_folder_path('Apartment20261022/ExperienceV13');c=a.static_mesh_component
  c.set_mobility(u.ComponentMobility.MOVABLE);c.set_static_mesh(meshes[key]);c.set_editor_property('override_materials',[])
  a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(1,1,1));c.set_mobility(u.ComponentMobility.STATIC)
  c.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);a.set_actor_enable_collision(False)
  c.set_visibility(True);c.set_hidden_in_game(False);a.set_actor_hidden_in_game(False)
  c.set_editor_property('cast_shadow',key!='TVDisplay');c.set_editor_property('visible_in_ray_tracing',True)
  c.set_editor_property('affect_dynamic_indirect_lighting',key not in ('TVDisplay','Soundbar','TVBackdrop','LivingCeiling','WindowHead','GymCeiling'))
  c.set_editor_property('affect_distance_field_lighting',key!='TVDisplay');report['actors'].append(label);return a
 old=actors['AP_Living_TV'];report['previous_tv']=dict(mesh=old.static_mesh_component.static_mesh.get_path_name(),location=list(old.get_actor_location().to_tuple()),scale=list(old.get_actor_scale3d().to_tuple()))
 for key in meshes:
  if key=='PowerControl':continue
  static('AP_Living_TV' if key=='TVBody' else 'AP13_'+key,key)
 atmosphere=actors['AP7_Atmosphere'];tag(atmosphere)
 # Device bindings keep their existing fan rotors and established station identities.
 previous={b.get_editor_property('station').get_actor_label():b.copy() for b in atmosphere.get_editor_property('devices') if b.get_editor_property('station')}
 bindings=[]
 for d in C['DEVICES']:
  station=actors[d['station']];label='AP13_Control_'+d['key'];control=actors.get(label)
  if not control:control=AA.spawn_actor_from_class(u.ApartmentDeviceControl,u.Vector());control.set_actor_label(label);actors[label]=control
  tag(control);control.set_folder_path('Apartment20261022/DeviceControls')
  control.set_editor_property('device_name',u.Text(d['label']));control.set_editor_property('workout',d['workout'])
  panel=control.get_editor_property('panel');panel.set_static_mesh(meshes['PowerControl']);panel.set_editor_property('override_materials',[])
  if 'world' in d:p=u.Vector(*(v*100 for v in d['world']));yaw=d['yaw']
  else:
   p=u.MathLibrary.transform_location(station.get_actor_transform(),u.Vector(*(v*100 for v in d['offset'])));yaw=station.get_actor_rotation().yaw+180.
  control.set_actor_location(p,False,False);control.set_actor_rotation(u.Rotator(yaw=yaw),False);scale=d.get('scale',1.);control.set_actor_scale3d(u.Vector(scale,scale,scale))
  b=previous.get(d['station'],u.ApartmentDeviceBinding());b.set_editor_property('station',station);b.set_editor_property('control',control);b.set_editor_property('workout',d['workout']);b.set_editor_property('wake_radius',d['radius'])
  extras=[]
  if d['key']=='TV':extras.append(actors['AP13_TVDisplay'])
  elif d['key']=='Treadmill':extras.append(actors['AP7_TrainingBelt'])
  elif d['key'] in ('Office','Bed2','Bed3'):
   pc=actors.get(d['station']+'_PC')
   if pc:extras.append(pc)
  b.set_editor_property('material_actors',extras);bindings.append(b)
  if d['key']!='TV':
   key='TreadmillUI' if d['key']=='Treadmill' else 'RowerUI' if d['key']=='Rower' else 'OfficeUI'
   for comp in station.get_components_by_class(u.StaticMeshComponent):
    if not comp.static_mesh:continue
    for i,slot in enumerate(comp.static_mesh.get_editor_property('static_materials')):
     role=str(slot.material_slot_name);oldmat=comp.get_material(i);name=oldmat.get_name() if oldmat else ''
     if any(v in role or v in name for v in ('OfficeUI','WorkoutUI')):
      comp.set_material(i,mats[key]);report['screen_slots'].append(dict(actor=d['station'],slot=i,material=key))
  report['controls'].append(dict(actor=label,station=d['station'],position=list(p.to_tuple()),scale=scale,radius=d['radius'],workout=d['workout'],server_power_replicated=True))
 atmosphere.set_editor_property('devices',bindings)
 rooms=[]
 for name,lo,hi,keep in C['ROOMS']:
  r=u.ApartmentRoom();r.set_editor_property('name',u.Name(name));r.set_editor_property('minimum',u.Vector(*(v*100 for v in lo)));r.set_editor_property('maximum',u.Vector(*(v*100 for v in hi)));r.set_editor_property('keep_lit',keep);rooms.append(r)
  report['rooms'].append(dict(name=name,minimum_m=lo,maximum_m=hi,keep_lit=keep))
 atmosphere.set_editor_property('rooms',rooms);portals=[]
 def portal(a,b,center,door=None):
  p=u.ApartmentPortal();p.set_editor_property('room_a',a);p.set_editor_property('room_b',b);p.set_editor_property('center',center);p.set_editor_property('door',door);portals.append(p)
  report['portals'].append(dict(room_a=a,room_b=b,center_cm=list(center.to_tuple()),door=door.get_actor_label() if door else None))
 for name,(a,b) in C['DOOR_ROOMS'].items():
  door=actors['Door_'+name];tag(door);door.set_editor_property('auto_close_seconds',0.)
  portal(a,b,door.get_actor_location()+u.Vector(0,0,175),door)
 for a,b,p in C['OPEN_PORTALS']:portal(a,b,u.Vector(*(v*100 for v in p)))
 atmosphere.set_editor_property('portals',portals);atmosphere.set_editor_property('balcony_door',actors['Door_Balcony']);atmosphere.set_editor_property('harbor_room_index',1)
 light_array=list(atmosphere.get_editor_property('lights'))
 for light_index,light in enumerate(light_array):
  a=light.get_editor_property('actor')
  if not a:continue
  label=a.get_actor_label()
  if not label.startswith('AP_Light_'):continue
  key=label.removeprefix('AP_Light_')
  room=9 if key.startswith('Gym_') else 10 if key.startswith('BathV5_') else 6 if key.startswith('Corridor') else 4 if key.startswith('Dining') else C['LIGHT_ROOM'][key]
  light.set_editor_property('room_index',room);fixtures=[]
  old_label='AP12_Fixture_'+key.replace('.','p').replace('-','m');f=actors.get(old_label)
  if f:
   tag(f);fixtures.append(f);comp=f.static_mesh_component
   for i,m in enumerate(comp.get_materials()):
    n=m.get_name() if m else ''
    for source,target in [('DiffuserWarm','FixtureWarm'),('DiffuserNeutral','FixtureNeutral'),('DiffuserCool','FixtureCool'),('GuideCyan','EdgeLight')]:
     if source in n or target in n:comp.set_material(i,mats[target]);break
  if key=='Living':fixtures += [actors['AP13_'+k] for k in ['LivingCeiling','WindowHead','TVBackdrop','Soundbar']]
  if key=='Gym_-1.8_14.15':fixtures.append(actors['AP13_GymCeiling'])
  if key=='Dining_7.85':
   f=actors['AP_PracticalLights'];tag(f);comp=f.static_mesh_component;fixtures.append(f)
   for i,m in enumerate(comp.get_materials()):
    if m and 'Warm' in m.get_name():comp.set_material(i,mats['PendantWarm'])
  light.set_editor_property('fixtures',fixtures);report['light_bindings'].append(dict(actor=label,room_index=room,fixtures=[x.get_actor_label() for x in fixtures]))
  light_array[light_index]=light
 atmosphere.set_editor_property('lights',light_array)
 report.update(total_local_lights=21,new_lights=0,new_capture_actors=0,manual_devices=6,room_count=len(rooms),portal_count=len(portals),tv=C['TV'],sound='existing harbor loop with actual aperture / room transmission',new_textures=assets['textures'])
 next_revision=R.parent/'RefinementV14'
 if (next_revision/'installed.json').exists():report['v14']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
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
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('V13 map save failed')
  report.update(stage='map_saved',backup=str(backup),saved_at=datetime.now().astimezone().isoformat())
  (R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP13_MAP_SAVED',len(report['controls']),len(report['light_bindings']))
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();raise
 finally:(R/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':main()
