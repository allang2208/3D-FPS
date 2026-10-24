"""Calibrate supported assemblies and bind the apartment-local presentation."""
from pathlib import Path
from datetime import datetime
import json,runpy,shutil,traceback,re
import unreal as u
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'));ROOT=C['ROOT'];PROJECT=C['PROJECT'];BASE=C['BASE'];MAP=C['MAP'];OWNER=C['OWNER']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools();AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
TAG='Apartment.V7.Calibrated'
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing AP7 asset '+path)
 return a
def tag(a,t=OWNER):
 tags=list(a.get_editor_property('tags'))
 if u.Name(t) not in tags:tags.append(u.Name(t));a.set_editor_property('tags',tags)
def transform(a):
 r=a.get_actor_rotation();return dict(p=list(a.get_actor_location().to_tuple()),s=list(a.get_actor_scale3d().to_tuple()),r=dict(pitch=r.pitch,yaw=r.yaw,roll=r.roll))
def position(a,p):return u.MathLibrary.transform_location(a.get_actor_transform(),u.Vector(*p))
def restore_before_refinement(world):
 path=ROOT/'calibration-before.json'
 if not path.exists():return
 rows=json.loads(path.read_text())
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  label=a.get_actor_label()
  if not a.actor_has_tag(TAG) or label not in rows:continue
  b=rows[label];a.set_actor_scale3d(u.Vector(*b['s']));a.set_actor_location(u.Vector(*b['p']),False,False);a.set_actor_rotation(u.Rotator(**b['r']),False)
  a.set_editor_property('tags',[t for t in a.get_editor_property('tags') if str(t)!=TAG])

def calibrate(actors,meshes,report):
 before={};handled=set()
 def snapshot(a):
  label=a.get_actor_label()
  if label not in before:before[label]=transform(a)
 def group(labels,anchor=None,target=1.,main=None):
  labels=[n for n in labels if n in actors and n not in handled]
  if not labels:return
  main=actors[main or labels[0]];ratio=target/main.get_actor_scale3d().x
  if anchor is None:anchor=main.get_actor_location()
  for label in labels:
   a=actors[label];handled.add(label)
   if abs(ratio-1)<.0001:continue
   snapshot(a);p=a.get_actor_location();a.modify();a.set_actor_scale3d(a.get_actor_scale3d()*ratio);a.set_actor_location(anchor+(p-anchor)*ratio,False,False);tag(a,TAG)
   report['calibrated'].append(dict(actor=label,factor=ratio,after=transform(a)))
 def matching(prefix):return [k for k in actors if k.startswith(prefix)]
 def backed(labels,floor=0.):
  labels=[x for x in labels if x in actors and x not in handled]
  if not labels:return
  first=actors[labels[0]];c=first.get_component_by_class(u.StaticMeshComponent);back=c.static_mesh.get_bounding_box().min.y
  offset=position(first,(0,back,0))-first.get_actor_location();centre=sum((actors[n].get_actor_location() for n in labels),u.Vector())/len(labels);anchor=centre+offset;anchor.z=floor;group(labels,anchor)
 for room in ['Bed2','Bed3']:
  bed='AP_'+room+'_Bed';group([bed]+matching('AP_Container_'+room+'_Nightstand'),position(actors[bed],(0,-123,0)),main=bed)
 for room,desk in [('Bed2','Desk'),('Bed3','Desk'),('Office','Workstation')]:
  name=f'AP_{room}_{desk}';group([name,f'AP_{room}_Chair',name+'_PC',name+'_PCGlass',f'AP_Container_{room}_Desk_Drawer'],position(actors[name],(0,-34 if room!='Office' else -40,0)),main=name)
 group(['AP_Living_CoffeeTable','AP_Living_Tray','AP_Living_Magazines']);group(['AP_Living_Sofa'])
 group(['AP_Kitchen_Dining']+matching('AP_Dining_Chair'));group(['AP_Balcony_Table']+matching('AP_Balcony_Chair'))
 group(['AP_Kitchen_Run','AP_Kitchen_Coffee','AP_Kitchen_Kettle']+matching('AP_Container_Kitchen_')+matching('AP_Container_Fridge_'),position(actors['AP_Kitchen_Run'],(0,-34,0)),main='AP_Kitchen_Run')
 group(['AP_Laundry_Washer','AP_Laundry_Hamper'],position(actors['AP_Laundry_Washer'],(0,-32,0)),main='AP_Laundry_Washer')
 for i in range(6):group([f'AP_Planter{i}',f'AP_Foliage{i}'])
 for label in ['AP_Gym_Treadmill','AP_Gym_Bench','AP_Gym_Weights','AP_Gym_CableTrainer','AP_Gym_Rower','AP_Container_Gym_Locker']:group([label])
 group(['AP_Bath1_VanityTop']+matching('AP_Container_Vanity_'),u.Vector(3.575*150,-12.70*150,0),main='AP_Bath1_VanityTop')
 group(['AP_Bath1_Toilet'],position(actors['AP_Bath1_Toilet'],(0,-32,0)));group(['AP_Bath1_Shower'])
 p=actors['AP_Bath1_Towels'].get_actor_location();group(['AP_Bath1_Towels'],u.Vector(p.x,p.y,0))
 group(['AP_BathMirror'],u.Vector(3.601*150,-12.70*150,0))
 for prefix in ['AP_Container_Living_Console_','AP_Container_Entry_Storage_','AP_Container_Bed2_Wardrobe_','AP_Container_Bed3_Wardrobe_','AP_Container_Living_Archive_','AP_Container_Office_Archive_','AP_Container_Bed3_Archive']:
  labels=matching(prefix)
  if prefix=='AP_Container_Living_Console_':labels+=['AP_Living_TV']
  backed(labels)
 for label in matching('AP_Container_Service_Storage_'):backed([label])
 actors['AP_BalconyRail'].static_mesh_component.set_static_mesh(meshes['BalconyRail']);actors['AP_BalconyRail'].static_mesh_component.set_editor_property('override_materials',[])
 for label in ['AP_RailCollision','AP_BalconyRailGlass']:
  a=actors.get(label)
  if a and abs(a.get_actor_scale3d().z-1.)>.0001:
   snapshot(a);s=a.get_actor_scale3d();a.set_actor_scale3d(u.Vector(s.x,s.y,1));tag(a,TAG);report['calibrated'].append(dict(actor=label,after=transform(a)))
 if 'AP_RailCollision' in actors:tag(actors['AP_RailCollision'],'Traversal.GuardrailDrop')
 if before:
  path=ROOT/'calibration-before.json';stored=json.loads(path.read_text()) if path.exists() else {};stored.update(before);path.write_text(json.dumps(stored,indent=2),encoding='utf8')

def surfaces(actors,meshes,mats,report):
 for label,a in actors.items():
  if label.endswith('_PC') and label.startswith('AP_'):a.static_mesh_component.set_static_mesh(meshes['ComputerChassis']);a.static_mesh_component.set_editor_property('override_materials',[])
 if 'AP_WindowGlass' in actors:
  c=actors['AP_WindowGlass'].static_mesh_component;c.set_static_mesh(meshes['WindowGlass']);c.set_editor_property('override_materials',[])
 calibrated={}
 for label,a in actors.items():
  if not label.startswith(('AP_','Door_')):continue
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh or not c.is_visible() or c.get_editor_property('hidden_in_game'):continue
   for i,s in enumerate(c.static_mesh.get_editor_property('static_materials')):
    role=re.sub(r'[._][0-9]{3}$','',str(s.material_slot_name));old=c.get_material(i);key=None
    if label=='AP_WindowGlass' and role in ['AP_WindowGlass','AP_Glass']:key='WindowGlass'
    elif role=='AP_ShowerGlass':key='ShowerGlass'
    elif 'Terry' in role or (label in ['AP_Bath1_Towels','AP_Laundry_Hamper'] and any(k in role for k in ['Fabric','Linen','Hem','Towel'])):key='Terry'
    elif 'Soil' in role:key='Soil'
    elif 'Leather' in role or (label in ['AP_Gym_Bench','AP_Gym_Rower'] and any(k in role for k in ['Fabric','Seam'])):key='Leather'
    elif role in ['AP_OfficeUI','AP_WorkoutUI']:key=role[3:]
    elif role in ['AP_Armor','AP_Teal'] and (label.startswith('AP_Container_') or '_PC' in label):key='Machined'
    if key:c.set_material(i,mats[key]);report['material_slots']+=1
    elif old and isinstance(old,u.MaterialInstanceConstant) and old.get_path_name().startswith('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV4/'):
     tiling=L.get_material_instance_scalar_parameter_value(old,'UVScale');scl=c.get_world_scale();factor=max(abs(scl.x),abs(scl.y),abs(scl.z))/1.2
     if tiling<=0 or abs(factor-1)<.001:continue
     cache=(old.get_path_name(),round(tiling*factor,4))
     if cache not in calibrated:
      name='MI_AP7_'+old.get_name()+'_UV'+str(cache[1]).replace('.','p');path=BASE+'/Calibrated/'+name
      mi=load(path) if E.does_asset_exist(path) else A.duplicate_asset(name,BASE+'/Calibrated',old)
      L.set_material_instance_scalar_parameter_value(mi,'UVScale',cache[1]);L.update_material_instance(mi)
      if not E.save_loaded_asset(mi,False):raise RuntimeError('AP7 surface calibration save')
      calibrated[cache]=mi
     c.set_material(i,calibrated[cache]);report['material_slots']+=1

def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong apartment target')
 receipt=json.loads((ROOT/'assets_saved.json').read_text())
 if receipt['stage']!='assets_saved':raise RuntimeError('AP7 assets incomplete')
 mats={k:load(v) for k,v in receipt['materials'].items()};meshes={k:load(v['path']) for k,v in receipt['meshes'].items()}
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 actors['BAY_Water'].static_mesh_component.set_material(0,load(receipt['water']['path']))
 report=dict(calibrated=[],material_slots=0,detail_actors=[],landmarks=[],preserved_room_shell=True)
 calibrate(actors,meshes,report);surfaces(actors,meshes,mats,report)
 def detail(label,key,parent=None,offset=(0,0,0),moving=False):
  a=actors.get(label)
  if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(),u.Rotator());a.set_actor_label(label);actors[label]=a
  a.modify();tag(a);a.set_folder_path('Apartment20261022/RefinementV7');c=a.static_mesh_component;c.set_static_mesh(meshes[key]);c.set_editor_property('override_materials',[]);c.set_collision_profile_name('NoCollision');c.set_editor_property('cast_shadow',False)
  c.set_mobility(u.ComponentMobility.MOVABLE if moving else u.ComponentMobility.STATIC)
  if parent:
   a.detach_from_actor(u.DetachmentRule.KEEP_WORLD,u.DetachmentRule.KEEP_WORLD,u.DetachmentRule.KEEP_WORLD)
   a.set_actor_location(position(parent,offset),False,False);a.set_actor_rotation(parent.get_actor_rotation(),False);a.set_actor_scale3d(parent.get_actor_scale3d())
   a.attach_to_actor(parent,u.Name('None'),u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)
  report['detail_actors'].append(label);return a
 devices=[]
 for room,desk in [('Bed2','Desk'),('Bed3','Desk'),('Office','Workstation')]:
  label=f'AP_{room}_{desk}';station=actors[label];pc=actors[label+'_PC']
  detail('AP7_'+room+'_KeyLegends','KeyboardLegends',station);detail('AP7_'+room+'_DeskSeams','OfficeSeams' if room=='Office' else 'DeskSeams',station)
  detail('AP7_'+room+'_PCDetail','ComputerDetail',pc)
  rotors=[detail('AP7_'+room+'_Fan'+str(i),'ComputerRotor',pc,(0,22.4,z),True) for i,z in enumerate([19,39])]
  for i,y in enumerate([5.5,-10.5]):
   rotor=detail('AP7_'+room+'_GPUFan'+str(i),'ComputerRotor',pc,(0,y,24),True);r=pc.get_actor_rotation()
   rotor.set_actor_rotation(u.Rotator(pitch=r.pitch,yaw=r.yaw,roll=r.roll+90),False);rotor.set_actor_scale3d(pc.get_actor_scale3d()*.625);rotors.append(rotor)
  binding=u.ApartmentDeviceBinding();binding.set_editor_property('station',station);binding.set_editor_property('rotors',rotors);binding.set_editor_property('wake_radius',230.);devices.append(binding)
 detail('AP7_TrainingBelt','TreadmillBelt',actors['AP_Gym_Treadmill'])
 detail('AP7_WeightMarks','GymWeightMarks',actors['AP_Gym_CableTrainer'])
 for label in ['AP_Gym_Treadmill','AP_Gym_Rower']:
  binding=u.ApartmentDeviceBinding();binding.set_editor_property('station',actors[label]);binding.set_editor_property('wake_radius',180.);binding.set_editor_property('workout',True);devices.append(binding)
 report['retired_actors']=[]
 for label in ['BAY_Landmarks','BAY_FarEnvironment','Bay_NightEnvironment']:
  old=actors.pop(label,None)
  if old:AA.destroy_actor(old);report['retired_actors'].append(label)
 for i in range(5):
  a=detail('AP7_BayLandmark_'+str(i),'Landmark_'+str(i));a.set_actor_location(u.Vector(),False,False);a.set_actor_scale3d(u.Vector(1.25,1.25,1.25))
  a.static_mesh_component.set_editor_property('visible_in_ray_tracing',True);a.static_mesh_component.set_editor_property('affect_distance_field_lighting',False);report['landmarks'].append(a.get_actor_label())
 for label,a in actors.items():
  if not label.startswith('BAY_') or not isinstance(a,u.StaticMeshActor) or not a.static_mesh_component.static_mesh:continue
  c=a.static_mesh_component
  for i,s in enumerate(c.static_mesh.get_editor_property('static_materials')):
   role=str(s.material_slot_name)
   if role in ['Office','Residential','Tech']:
    family='Data' if role=='Tech' else ('Terraces' if label.endswith(('1','3')) else 'Housing') if role=='Residential' else ['Corporate','Financial'][sum(ord(ch) for ch in label)%2]
    c.set_material(i,mats['City'+family])
 ambience=actors.get('AP7_Atmosphere')
 if not ambience:ambience=AA.spawn_actor_from_class(u.ApartmentAtmosphere,u.Vector(),u.Rotator());ambience.set_actor_label('AP7_Atmosphere')
 tag(ambience);ambience.set_folder_path('Apartment20261022/Atmosphere');lights=[]
 for label,a in actors.items():
  if not label.startswith('AP_Light_'):continue
  c=a.get_component_by_class(u.LightComponent)
  if not c:continue
  day=.48 if any(k in label for k in ['Corridor','Bath','Foyer','Laundry','Service']) else .22
  b=u.ApartmentLightBinding();b.set_editor_property('actor',a);b.set_editor_property('base_intensity',c.get_editor_property('intensity'));b.set_editor_property('day_factor',day);b.set_editor_property('night_factor',.86 if 'Living' in label else .95);lights.append(b)
  c.set_light_color(u.LinearColor(1,1,1,1));c.set_editor_property('use_temperature',True);c.set_editor_property('temperature',3400. if 'Living' in label or 'Bed' in label else 4100.)
  c.set_editor_property('max_draw_distance',2400.);c.set_editor_property('max_distance_fade_range',450.)
 ambience.set_editor_property('lights',lights);ambience.set_editor_property('devices',devices)
 ambience.set_editor_property('windows',[actors['AP_WindowGlass']] if 'AP_WindowGlass' in actors else [])
 for prop,key in [('interior_sound','Ventilation'),('harbor_sound','Harbor'),('device_sound','Electronics')]:ambience.set_editor_property(prop,load(receipt['audio'][key]))
 if 'AP_OpticalQuality' in actors:actors['AP_OpticalQuality'].set_editor_property('enabled',False)
 report.update(device_stations=len(devices),light_bindings=len(lights),reflection_zones=2,window_rain_connected=bool(ambience.get_editor_property('windows')),audio_layers=list(receipt['audio']))
 next_revision=ROOT.parent/'RefinementV8'
 if (next_revision/'installed.json').exists():report['v8']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report

def main():
 report=dict(stage='preparing',map=MAP,game_run=False,rendered=False,auditioned=False)
 def record():(ROOT/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 try:
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if editor and editor.get_game_world():raise RuntimeError('Preserve active game')
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
  backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);source=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(source,backup/source.name);report['backup']=str(backup/source.name)
  world=u.EditorLoadingAndSavingUtils.load_map(MAP);report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('AP7 map save failed')
  report['stage']='map_saved';record();(ROOT/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8');print('AP7_MAP_SAVED')
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
