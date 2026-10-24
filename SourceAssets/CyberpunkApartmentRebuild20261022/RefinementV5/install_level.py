"""Scoped in-place apartment update; preserve unrelated edits and native interactions."""
from pathlib import Path
from datetime import datetime
import json,runpy,shutil,traceback
import unreal as u
C=runpy.run_path(str(Path(__file__).resolve().parent/'design.py'));ROOT=C['ROOT'];PROJECT=C['PROJECT'];BASE=C['BASE'];MAP=C['MAP'];SCALE=C['SCALE'];OWNER=C['OWNER']
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing V5 asset '+path)
 return a
def V(p):return u.Vector(p[0]*100*SCALE,-p[1]*100*SCALE,p[2]*100*SCALE)
def mark(a):
 tags=list(a.get_editor_property('tags'))
 if u.Name(OWNER) not in tags:tags.append(u.Name(OWNER))
 a.set_editor_property('tags',tags)
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong apartment world')
 next_revision=ROOT.parent/'RefinementV6'
 environment_upgrade=None
 if (next_revision/'installed.json').exists():
  environment_upgrade=runpy.run_path(str(next_revision/'install_level.py'))
  environment_upgrade['restore_before_refinement'](world)
 manifest=json.loads((ROOT/'assembly.json').read_text('utf8'));surfaces=json.loads((ROOT/'surfaces_saved.json').read_text('utf8'))
 meshes={r['key']:load(r['asset']) for r in manifest['meshes']}
 mats={k:load(v['path']) for k,v in surfaces['materials'].items()}
 supplements={k:load(v['path']) for k,v in surfaces['supplements'].items()}
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 report=dict(replaced=[],retired=[],doors=[],moved=[],normal_supplements=0,glass_slots=0,
  bathroom_area_before_m2=manifest['bath_area_old_m2'],bathroom_area_after_m2=manifest['bath_area_new_m2'],other_room_area_change_m2=0)
 for key in manifest['retire']:
  a=actors.pop('AP_'+key,None)
  if a:AA.destroy_actor(a);report['retired'].append('AP_'+key)
 a=actors.pop('AP_Light_Bath1',None)
 if a:AA.destroy_actor(a)
 for row in manifest['meshes']:
  key=row['key']
  if not row['world']:continue
  label='AP_'+key;a=actors.get(label)
  if not a:
   a=AA.spawn_actor_from_class(u.StaticMeshActor,u.Vector(),u.Rotator());a.set_actor_label(label);actors[label]=a
  a.modify();mark(a);a.set_folder_path('Apartment20261022/RefinementV5')
  a.set_actor_location(u.Vector(),False,False);a.set_actor_rotation(u.Rotator(),False);a.set_actor_scale3d(u.Vector(SCALE,SCALE,SCALE))
  c=a.static_mesh_component;c.modify();c.set_static_mesh(meshes[key]);c.set_editor_property('override_materials',[])
  c.set_mobility(u.ComponentMobility.STATIC);c.set_collision_profile_name('BlockAll' if row['collision'] else 'NoCollision')
  c.set_collision_enabled(u.CollisionEnabled.QUERY_AND_PHYSICS if row['collision'] else u.CollisionEnabled.NO_COLLISION)
  c.set_visibility(not row['hidden']);c.set_hidden_in_game(row['hidden'])
  optical=key in ['WindowGlass','BathShowerGlass'];c.set_editor_property('cast_shadow',not (row['hidden'] or optical))
  if row['hidden']:
   c.set_editor_property('affect_distance_field_lighting',False);c.set_editor_property('affect_dynamic_indirect_lighting',False)
  report['replaced'].append(label)
 for d in manifest['doors']:
  a=actors['Door_'+d['name']];a.modify();mark(a);a.set_actor_location(V(d['p']),False,False)
  a.set_actor_rotation(u.Rotator(yaw=d['yaw']),False);a.set_actor_scale3d(u.Vector(SCALE,SCALE,SCALE))
  # Bed2 terminates beside a perpendicular corridor plinth; its shorter overtravel
  # still places the inner leaf edge 3 cm behind the opaque jamb.
  travel=d['width']*50+(3.0 if d['name']=='Bed2' else 4.5)
  a.set_editor_property('slide_distance_cm',travel);a.set_editor_property('slide_speed_cm',max(52.,travel))
  comps={c.get_name():c for c in a.get_components_by_class(u.StaticMeshComponent)}
  frame=meshes['Door_'+d['name']+'_Frame'];leaf=meshes['Door_'+d['name']+'_Leaf']
  c=comps['DoorFrame'];c.set_static_mesh(frame);c.set_editor_property('override_materials',[])
  b=frame.get_bounding_box();mid=(b.min+b.max)*.5;c.set_relative_location(u.Vector(-mid.x,-mid.y,-b.min.z),False,False)
  b=leaf.get_bounding_box();mid=(b.min+b.max)*.5;half=(b.max-b.min)*.5
  for name,sign in [('LeafLeft',-1),('LeafRight',1)]:
   c=comps[name];c.set_static_mesh(leaf);c.set_editor_property('override_materials',[]);c.set_relative_scale3d(u.Vector(1,.5,1))
   c.set_relative_location(u.Vector(-mid.x,sign*half.y*.5-mid.y*.5,-b.min.z),False,False)
   c.set_collision_profile_name('BlockAll')
   if d['name']=='Balcony':c.set_editor_property('cast_shadow',False)
  report['doors'].append(dict(label=a.get_actor_label(),centre=d['p'],travel_cm=travel,clear_width_cm=d['width']*100*SCALE,
    leaf_thickness_cm=(b.max.x-b.min.x)*SCALE,pocket_depth_cm=10*SCALE,fully_open_hidden_by_skins=True))
 def move(label,p,yaw=None):
  a=actors.get(label)
  if not a:raise RuntimeError('Expected bathroom fixture '+label)
  a.modify();a.set_actor_location(V(p),False,False)
  if yaw is not None:a.set_actor_rotation(u.Rotator(yaw=-yaw),False)
  report['moved'].append(dict(actor=label,p=p,yaw=yaw))
 move('AP_Bath1_VanityTop',[3.84,12.70,0],90)
 move('AP_Container_Vanity_0',[3.84,12.47,.30],90)
 move('AP_Container_Vanity_1',[3.84,12.93,.30],90)
 move('AP_Bath1_Toilet',[5.37,11.65,0],-90)
 move('AP_Bath1_Shower',[4.70,15.235,.07])
 move('AP_Bath1_Towels',[3.65,11.68,1.20],90)
 for spec in manifest['lights']:
  label='AP_Light_'+spec['label'];a=actors.get(label)
  if not a:a=AA.spawn_actor_from_class(u.RectLight,V(spec['p']),u.Rotator());a.set_actor_label(label)
  a.modify();mark(a);a.set_actor_location(V(spec['p']),False,False);a.set_actor_rotation(u.Rotator(pitch=-90),False)
  a.set_folder_path('Apartment20261022/Lighting');c=a.get_component_by_class(u.RectLightComponent)
  c.set_mobility(u.ComponentMobility.MOVABLE);c.set_editor_property('intensity_units',u.LightUnits.LUMENS);c.set_intensity(spec['power']*SCALE*SCALE)
  c.set_light_color(u.LinearColor(*spec['color'],1));c.set_editor_property('source_width',spec['w']*SCALE);c.set_editor_property('source_height',spec['d']*SCALE)
  c.set_editor_property('attenuation_radius',spec['radius']*SCALE);c.set_editor_property('cast_shadows',False)
  c.set_editor_property('max_draw_distance',1800.);c.set_editor_property('max_distance_fade_range',350.)
 # Upgrade existing specialty glass and preserve all calibrated V4 opaque surfaces.
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
  label=a.get_actor_label()
  if not label.startswith(('AP_','Door_')):continue
  for c in a.get_components_by_class(u.StaticMeshComponent):
   if not c.static_mesh or not c.is_visible() or c.get_editor_property('hidden_in_game'):continue
   for i,s in enumerate(c.static_mesh.get_editor_property('static_materials')):
    role=str(s.material_slot_name);old=c.get_material(i)
    if role in ['AP_Glass','AP_WindowGlass']:
     c.set_material(i,mats['WindowGlass']);c.set_editor_property('cast_shadow',False);report['glass_slots']+=1
    elif old and old.get_path_name() in supplements:
     c.set_material(i,supplements[old.get_path_name()]);report['normal_supplements']+=1
 # Apartment-local postprocess settings use existing Lumen; no second scene render.
 label='AP_OpticalQuality';pp=actors.get(label)
 if not pp:pp=AA.spawn_actor_from_class(u.PostProcessVolume,u.Vector());pp.set_actor_label(label)
 mark(pp);pp.set_editor_property('unbound',True);pp.set_editor_property('priority',2.)
 settings=pp.get_editor_property('settings')
 for k,v in dict(override_lumen_reflection_quality=True,lumen_reflection_quality=2.,
  override_lumen_ray_lighting_mode=True,lumen_ray_lighting_mode=u.LumenRayLightingModeOverride.HIT_LIGHTING_FOR_REFLECTIONS,
  override_lumen_front_layer_translucency_reflections=True,lumen_front_layer_translucency_reflections=True,
  override_lumen_max_reflection_bounces=True,lumen_max_reflection_bounces=1).items():settings.set_editor_property(k,v)
 pp.set_editor_property('settings',settings)
 report['reflection_mode']='existing Lumen, hit lighting for reflections, one bounce, apartment map only'
 report['scene_capture_actors_added']=0
 if environment_upgrade:report['v6']=environment_upgrade['apply_upgrade'](world)
 return report
def main():
 report=dict(stage='preparing',map=MAP,component_inspection_requested=True,game_run=False,rendered=False)
 def record():(ROOT/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 try:
  editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
  if editor and editor.get_game_world():raise RuntimeError('Preserve running game')
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
  backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
  disk=PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap';shutil.copy2(disk,backup/disk.name);report['backup']=str(backup/disk.name)
  world=u.EditorLoadingAndSavingUtils.load_map(MAP);report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cannot save V5 map')
  report['stage']='map_saved';record();(ROOT/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
  print('APARTMENT_V5_MAP_SAVED',len(report['doors']),len(report['replaced']))
 except Exception:report['error']=traceback.format_exc();record();raise
if __name__=='__main__':main()
