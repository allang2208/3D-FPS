from pathlib import Path
from datetime import datetime
import unreal as u,json,runpy,shutil,math,traceback
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'));BASE=C['BASE'];MAP=C['MAP'];PROJECT=C['PROJECT']
AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
def world_position(p):return u.Vector((-p[0]+10)*125,p[1]*125,(p[2]-90)*125)
def apply_upgrade(world):
 if world.get_path_name().split('.')[0]!=MAP:raise RuntimeError('Wrong searchlight target')
 assets=json.loads((R/'assets_saved.json').read_text())
 if assets['stage']!='assets_saved':raise RuntimeError('Searchlight assets incomplete')
 actors={a.get_actor_label():a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)}
 ambience=actors.get('AP7_Atmosphere')
 if not ambience:raise RuntimeError('Existing apartment clock/light controller missing')
 made=[];bindings=[b for b in ambience.get_editor_property('lights') if b.get_editor_property('actor') and not b.get_editor_property('actor').get_actor_label().startswith('AP9_')]
 def mark(a):
  a.modify();a.set_folder_path('Apartment20261022/BaySearchlights');tags=list(a.get_editor_property('tags'))
  if u.Name('CyberpunkApartment.RefinementV9') not in tags:tags.append(u.Name('CyberpunkApartment.RefinementV9'));a.set_editor_property('tags',tags)
  made.append(a.get_actor_label())
 def fixture(label,key,p,scale=1.25,rotation=None,overrides=None,moving=False):
  a=actors.get(label)
  if not a:a=AA.spawn_actor_from_class(u.StaticMeshActor,p);a.set_actor_label(label)
  mark(a);comp=a.static_mesh_component;mesh=u.load_asset(assets['meshes'][key]);comp.set_static_mesh(mesh);comp.set_editor_property('override_materials',[])
  comp.set_collision_profile_name('NoCollision');comp.set_editor_property('cast_shadow',False);comp.set_editor_property('affect_distance_field_lighting',False);comp.set_editor_property('visible_in_ray_tracing',not moving and key!='Beam')
  if key!='Beam':comp.set_editor_property('bounds_scale',2.)
  if key=='Beam':comp.set_editor_property('receives_decals',False)
  if overrides:
   for i,s in enumerate(mesh.get_editor_property('static_materials')):
    role=str(s.material_slot_name)
    if role in overrides:comp.set_material(i,u.load_asset(assets['materials'][overrides[role]]))
  a.set_actor_location(p,False,False);a.set_actor_rotation(rotation or u.Rotator(),False);a.set_actor_scale3d(u.Vector(scale,scale,scale));return a
 for b in C['SEARCH']:
  p=world_position(b['p']);pivot=p+u.Vector(0,0,375);key=b['key']
  fixture('AP9_'+key+'_Base','Base',p,overrides={'Yoke':key+'_Yoke'},moving=True)
  fixture('AP9_'+key+'_Head','Head',pivot,overrides={'HeadMetal':key+'_Head','Lens':key+'_Lens'},moving=True)
  fixture('AP9_'+key+'_Beam','Beam',pivot,b['length']/400,overrides={'Beam':key+'_Beam'},moving=True)
 for b in C['FIXED']:
  p=world_position(b['p']);pivot=p+u.Vector(0,0,375);target=world_position(b['target']);d=target-pivot;distance=math.sqrt(d.x*d.x+d.y*d.y+d.z*d.z);n=d/distance
  yaw=math.degrees(math.atan2(n.y,n.x));theta=math.degrees(math.acos(max(-1,min(1,n.z))));key=b['key']
  fixture('AP9_'+key+'_Base','Base',p,rotation=u.Rotator(yaw=yaw))
  fixture('AP9_'+key+'_Head','Head',pivot,rotation=u.Rotator(pitch=-theta,yaw=yaw),overrides={'Lens':key+'_Lens'})
  label='AP9_'+key+'_Spot';a=actors.get(label)
  if not a:a=AA.spawn_actor_from_class(u.SpotLight,pivot);a.set_actor_label(label)
  mark(a);comp=a.get_component_by_class(u.SpotLightComponent);comp.set_mobility(u.ComponentMobility.MOVABLE)
  for k,v in dict(intensity_units=u.LightUnits.CANDELAS,intensity=0.,use_inverse_squared_falloff=True,attenuation_radius=11000.,inner_cone_angle=12.,outer_cone_angle=22.,source_radius=15.,cast_shadows=False,volumetric_scattering_intensity=0.,indirect_lighting_intensity=0.,max_draw_distance=600000.,max_distance_fade_range=50000.,affect_translucent_lighting=False).items():comp.set_editor_property(k,v)
  comp.set_light_color(u.LinearColor(*b['color'],1));a.set_actor_location(pivot+n*71.875,False,False);a.set_actor_rotation(u.MathLibrary.find_look_at_rotation(pivot,target),False)
  binding=u.ApartmentLightBinding();binding.set_editor_property('actor',a);binding.set_editor_property('base_intensity',float(b['candela']));binding.set_editor_property('day_factor',0.);binding.set_editor_property('night_factor',1.);bindings.append(binding)
 ambience.modify();ambience.set_editor_property('lights',bindings)
 report=dict(actors=made,real_spotlights=6,decorative_sweeping_beams=6,weather_controller='AP7_Atmosphere',total_controller_lights=len(bindings),beam_lengths_m=[b['length'] for b in C['SEARCH']],added_tick_actors=0,global_fog_modified=False,day_intensity_factor=0,spot_radius_m=110,spot_shadow_casting=False,spots_volumetric_scattering=0,beam_motion='GPU material WPO, mechanically aligned yaw yoke and pitch head')
 next_revision=R.parent/'RefinementV10'
 if (next_revision/'installed.json').exists():report['v10']=runpy.run_path(str(next_revision/'install_level.py'))['apply_upgrade'](world)
 return report
def main():
 report=dict(stage='preparing',map=MAP,game_run=False,visual_acceptance=False,performance_measured=False)
 try:
  if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
  backup=R/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True);shutil.copy2(PROJECT/'Content/GameMaps/L_CyberpunkApartment.umap',backup/'L_CyberpunkApartment.umap')
  subsystem=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=subsystem.get_editor_world() if subsystem else None
  if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
  report.update(apply_upgrade(world))
  if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Searchlight map save failed')
  report['stage']='map_saved';report['backup']=str(backup);(R/'installed.json').write_text(json.dumps(report,indent=2),encoding='utf8')
 except Exception:report['stage']='failed';report['error']=traceback.format_exc();raise
 finally:(R/'map_saved.json').write_text(json.dumps(report,indent=2),encoding='utf8')
if __name__=='__main__':main()
