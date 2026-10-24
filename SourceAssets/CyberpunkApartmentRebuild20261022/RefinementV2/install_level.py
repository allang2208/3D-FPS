"""Replace the apartment map with the authored assembly. No PIE, capture or test."""
from pathlib import Path
from datetime import datetime
import json,sys,shutil,traceback,runpy
import unreal as u
sys.path.insert(0,str(Path(__file__).resolve().parent))
from refinement_design import *
OWNER='CyberpunkApartment.RefinementV2'
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
E=u.EditorAssetLibrary
manifest=json.loads((ROOT/'assembly.json').read_text('utf8'))
imported=json.loads((ROOT/'assets_saved.json').read_text('utf8'))
rows={r['key']:r for r in manifest['meshes']}
report=dict(stage='preparing',map=MAP,actors=[],doors=[],lights=[],containers=[],removed=[],
            tests_run=False,game_run=False,acceptance_rendered=False,editor_opened=False)
def record():(ROOT/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def V(p):return u.Vector(p[0]*100,-p[1]*100,p[2]*100)
def R(yaw=0):return u.Rotator(pitch=0,yaw=yaw,roll=0)
def tag(a,extra=()):a.set_editor_property('tags',[u.Name(OWNER)]+[u.Name(t) for t in extra])
def load(p):
 a=u.load_asset(p)
 if not a:raise RuntimeError('Cannot load '+p)
 return a
try:
 if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
 if imported['stage']!='assets_saved':raise RuntimeError('Complete mesh import before publication')
 editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
 if editor and editor.get_game_world():raise RuntimeError('Preserve active PIE')
 previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else None
 if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
 backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
 disk=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(disk,backup/disk.name)
 report['backup']=str(backup/disk.name);record()
 meshes={key:load(path) for key,path in REUSE.items()}
 meshes.update({key:load(r['asset']) for key,r in rows.items()})
 world=u.EditorLoadingAndSavingUtils.load_map(MAP)
 if not world:raise RuntimeError('Cannot load apartment')
 doorcls=u.load_class(None,'/Script/FPSGAME.ColdSteelSlidingDoor')
 if not doorcls:raise RuntimeError('Existing native sliding door class unavailable')
 # Map is the user's explicitly authorized replacement target. Keep the approved
 # exterior and existing global environment settings; replace all furnished geometry.
 for a in list(u.GameplayStatics.get_all_actors_of_class(world,u.Actor)):
  label=a.get_actor_label()
  if label=='Bay_NightEnvironment' or a.actor_has_tag('CyberpunkApartment.LayeredBay20261022'):continue
  if isinstance(a,(u.StaticMeshActor,u.RectLight,u.PointLight,u.SpotLight,u.PlayerStart,u.ColdSteelSceneContainer)) or a.get_class()==doorcls:
   report['removed'].append(label);AA.destroy_actor(a)
  elif isinstance(a,u.DirectionalLight):
   c=a.get_component_by_class(u.DirectionalLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
   c.set_intensity(.35);c.set_light_color(u.LinearColor(.471,.549,1.,1))
   a.set_actor_rotation(u.Rotator(pitch=-28,yaw=200,roll=0),False)
 for p in manifest['placements']:
  key=p['key'];mesh=meshes[key]
  a=AA.spawn_actor_from_class(u.StaticMeshActor,V(p['p']),R(-p['yaw']))
  a.set_actor_label('CITY_our_tower' if key=='NearTower' else 'AP_'+p['label'])
  a.set_folder_path('Apartment20261022/'+(p['room'] or 'Details'));tag(a)
  c=a.static_mesh_component;c.set_static_mesh(mesh);c.set_mobility(u.ComponentMobility.STATIC)
  a.set_actor_scale3d(u.Vector(p['scale'],p['scale'],p['scale']))
  blocking=p['collision'] and (key not in rows or rows[key]['collision'])
  c.set_collision_profile_name(u.Name('BlockAll' if blocking else 'NoCollision'))
  c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if blocking else u.CollisionEnabled.NO_COLLISION)
  for i,s in enumerate(mesh.get_editor_property('static_materials')):
   for ending,replacement in p['override'].items():
    if str(s.material_slot_name).endswith('_'+ending):c.set_material(i,load(MATERIALS[replacement]))
  hidden=rows.get(key,{}).get('hidden',False)
  if hidden:
   c.set_visibility(False);c.set_hidden_in_game(True);c.set_editor_property('cast_shadow',False)
   c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('affect_dynamic_indirect_lighting',False)
  if key=='RailCollision':
   tag(a,['Traversal.GuardrailDrop']);c.set_editor_property('component_tags',[u.Name('Traversal.GuardrailDrop')])
  if key in ('CoffeeTray','Magazines','Kettle','CoffeeMachine'):
   c.set_editor_property('cast_shadow',False);c.set_cull_distance(2300.)
  if key in ('Plant','Plant2'):
   c.set_cull_distance(3500.)
  # Transparent architectural glass does not cast an opaque room-sized shadow.
  if key in ('WindowGlass','BalconyRailGlass','VanityClearGlass') or key.startswith('ShowerScreen_'):
   c.set_editor_property('cast_shadow',False)
  report['actors'].append(dict(label=a.get_actor_label(),mesh=mesh.get_path_name(),
      p_cm=[p['p'][0]*100,-p['p'][1]*100,p['p'][2]*100],yaw=-p['yaw'],scale=p['scale'],
      collision=blocking,hidden=hidden,reused=key in REUSE))

 # The established searchable-container class already owns the eased opening,
 # input/HUD routing and private/shared persistent storage. No parallel inventory.
 container_cls=u.load_class(None,'/Script/FPSGAME.ColdSteelSceneContainer')
 for spec in manifest['containers']:
  a=AA.spawn_actor_from_class(container_cls,V(spec['p']),R(-spec['yaw']))
  a.set_actor_label('AP_Container_'+spec['label']);a.set_folder_path('Apartment20261022/Containers/'+spec['room'])
  tag(a,['ColdSteel.SceneContainer'])
  for prop,value in dict(container_id=spec['id'],caption=spec['caption'],storage_pages=spec['storage_pages'],
     opening_duration=spec['opening_duration'],opened_yaw=spec['opened_yaw'],initial_open_fraction=0.).items():a.set_editor_property(prop,value)
  a.set_editor_property('opening_motion',u.ColdSteelContainerMotion.DRAWER if spec['motion']=='Drawer' else u.ColdSteelContainerMotion.SWING)
  a.set_editor_property('drawer_travel',u.Vector(0,spec['travel']*100,0))
  a.body.set_static_mesh(meshes[spec['body']]);a.door.set_static_mesh(meshes[spec['front']])
  a.door_hinge.set_relative_location(V(spec['hinge']),False,False)
  a.door_hinge.set_relative_rotation(R(),False,False)
  a.body.set_collision_profile_name('BlockAll')
  a.door.set_collision_profile_name('BlockAllDynamic');a.door.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
  a.door.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN,u.CollisionResponseType.ECR_IGNORE)
  for component in (a.body,a.door):
   component.set_render_custom_depth(False);component.set_custom_depth_stencil_value(201)
   if spec['body'].startswith('Fridge'):
    for i,s in enumerate(component.static_mesh.get_editor_property('static_materials')):
     slot=str(s.material_slot_name)
     role='Teal' if slot.endswith(('Ceramic','PaintedSteel')) else 'Steel' if slot.endswith('BareSteel') else None
     if role:component.set_material(i,load(MATERIALS[role]))
  report['containers'].append(dict(id=spec['id'],label=a.get_actor_label(),motion=spec['motion'],body=meshes[spec['body']].get_path_name(),
     moving_front=meshes[spec['front']].get_path_name(),hinge_cm=[spec['hinge'][0]*100,-spec['hinge'][1]*100,spec['hinge'][2]*100]))
 pp=next((a for a in u.GameplayStatics.get_all_actors_of_class(world,u.PostProcessVolume) if a.get_actor_label()=='AP_ContainerOutline'),None)
 if not pp:pp=AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
 pp.set_actor_label('AP_ContainerOutline');tag(pp);pp.set_editor_property('unbound',True);pp.set_editor_property('priority',1.)
 settings=pp.get_editor_property('settings');blend=u.WeightedBlendable()
 blend.set_editor_property('weight',1.);blend.set_editor_property('object',load('/Game/Dungeons/StaffLiving20261002/ScenePolishV4/Materials/M_Staff_ContainerOutline_V4'))
 blends=u.WeightedBlendables();blends.set_editor_property('array',[blend]);settings.set_editor_property('weighted_blendables',blends);pp.set_editor_property('settings',settings)

 for d in manifest['doors']:
  a=AA.spawn_actor_from_class(doorcls,V(d['p']),R(d['yaw']))
  a.set_actor_label('Door_'+d['name']);a.set_folder_path('Apartment20261022/Interactions');tag(a)
  a.set_editor_property('slide_distance_cm',d['width']*50+1)
  a.set_editor_property('slide_speed_cm',max(52.,d['width']*50+1))
  a.set_editor_property('auto_close_seconds',6.)
  parts={c.get_name():c for c in a.get_components_by_class(u.StaticMeshComponent)}
  frame=meshes['Door_'+d['name']+'_Frame'];leaf=meshes['Door_'+d['name']+'_Leaf']
  parts['DoorFrame'].set_static_mesh(frame)
  b=frame.get_bounding_box();mid=(b.min+b.max)*.5
  parts['DoorFrame'].set_relative_location(u.Vector(-mid.x,-mid.y,-b.min.z),False,False)
  b=leaf.get_bounding_box();mid=(b.min+b.max)*.5;half=(b.max-b.min)*.5
  for name,side in [('LeafLeft',-1),('LeafRight',1)]:
   c=parts[name];c.set_static_mesh(leaf);c.set_relative_scale3d(u.Vector(1,.5,1))
   c.set_relative_location(u.Vector(-mid.x,side*half.y*.5-mid.y*.5,-b.min.z),False,False)
   c.set_collision_profile_name(u.Name('BlockAll'))
  report['doors'].append(dict(label=a.get_actor_label(),native_class=doorcls.get_path_name(),
                             width_cm=d['width']*100,height_cm=d['height']*100,root_scale=[1,1,1]))

 for p in manifest['lights']:
  a=AA.spawn_actor_from_class(u.RectLight,V(p['p']),R())
  a.set_actor_label('AP_Light_'+p['label']);a.set_folder_path('Apartment20261022/Lighting');tag(a)
  c=a.get_component_by_class(u.RectLightComponent);c.set_mobility(u.ComponentMobility.MOVABLE)
  a.set_actor_rotation(u.Rotator(pitch=-90,yaw=p['yaw'],roll=0),False)
  c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(p['power'])
  c.set_light_color(u.LinearColor(*p['color'],1))
  c.set_editor_property('source_width',p['w']);c.set_editor_property('source_height',p['d'])
  c.set_editor_property('attenuation_radius',p['radius']);c.set_editor_property('cast_shadows',p['shadow'])
  c.set_editor_property('max_draw_distance',4000.);c.set_editor_property('max_distance_fade_range',500.)
  report['lights'].append(p)
 sp=manifest['spawn'];a=AA.spawn_actor_from_class(u.PlayerStart,V(sp['p']),R(sp['yaw_ue']))
 a.set_actor_label('PlayerStart_Apartment');a.set_folder_path('Apartment20261022/Gameplay');tag(a)
 a.get_component_by_class(u.CapsuleComponent).set_capsule_size(sp['capsule_radius_cm'],sp['capsule_half_height_cm'],False)
 settings=world.get_world_settings();settings.set_editor_property('default_game_mode',u.load_class(None,'/Script/FPSGAME.FPSGAMEGameMode'))
 settings.set_editor_property('kill_z',-21000.)
 bay=runpy.run_path(str(PROJECT/'SourceAssets/CyberpunkBayBackdrop20261021/install_background.py'))
 report['bay']=bay['apply_saved_background'](world)
 report['spawn']=sp
 if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Map save failed')
 report['stage']='map_saved';record()
 # Last successful installation stays authoritative if a later refresh fails.
 (ROOT/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 u.log('APARTMENT_REBUILD_MAP_SAVED '+MAP)
 if previous and previous!=MAP and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
  u.EditorLoadingAndSavingUtils.load_map(previous)
except Exception:
 report['stage']='failed';report['error']=traceback.format_exc();record();raise
