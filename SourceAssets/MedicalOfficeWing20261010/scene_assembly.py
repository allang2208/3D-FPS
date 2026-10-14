"""Editable office scene assembly using the same saved module descriptors."""
import math,runpy
from pathlib import Path
import unreal as u
PROJECT=Path(__file__).resolve().parents[2]
HELP=runpy.run_path(str(PROJECT/'SourceAssets/HospitalContainers20261003/Scripts/unreal_helpers.py'))
def populate(module,pose,prefix='MedicalOffice'):
 actors=(u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem));cache={};created=[]
 def asset(path):
  if path not in cache:
   cache[path]=u.load_asset(path)
   if not cache[path]:raise RuntimeError('Missing office dependency '+path)
  return cache[path]
 def location(p):
  a=math.radians(pose['yaw']);x,y,z=p;o=pose['position']
  return u.Vector(o[0]+math.cos(a)*x-math.sin(a)*y,o[1]+math.sin(a)*x+math.cos(a)*y,o[2]+z)
 def spawn(cls,spec,label):
  a=actors.spawn_actor_from_class(cls,location(spec.get('position',[0,0,0])),u.Rotator(pitch=spec.get('pitch',0),yaw=pose['yaw']+spec.get('yaw',0),roll=spec.get('roll',0)))
  a.set_actor_label(prefix+'_'+label);a.set_folder_path('HospitalLine/'+module['id'])
  a.set_editor_property('tags',[u.Name('HospitalLine.Subject'),u.Name(module['id']),u.Name('MedicalOfficeWing20261010')]);created.append(a)
  return a
 for i,s in enumerate(module['parts']):
  a=spawn(u.StaticMeshActor,s,s.get('id',str(i)));c=a.static_mesh_component
  c.set_mobility(u.ComponentMobility.STATIC);c.set_static_mesh(asset(s['mesh']))
  c.set_collision_profile_name('BlockAll' if s['collision'] else 'NoCollision');c.set_cast_shadow(s.get('cast_shadow',True))
  for j,p in enumerate(s.get('materials',[])):
   if p:c.set_material(j,asset(p))
  a.set_actor_scale3d(u.Vector(*s.get('scale',[1,1,1])))
 for i,s in enumerate(module['lights']):
  area=s.get('type')=='rect'
  a=spawn(u.RectLight if area else u.PointLight,s,'Light'+str(i));c=a.get_component_by_class(u.LocalLightComponent)
  c.set_mobility(u.ComponentMobility.MOVABLE)
  # Set the final pose after mobility, overriding the light class's root rotation.
  a.set_actor_location_and_rotation(location(s['position']),u.Rotator(pitch=s.get('pitch',0),yaw=pose['yaw']+s.get('yaw',0),roll=s.get('roll',0)),False,True)
  c.set_editor_property('intensity_units',u.LightUnits.LUMENS)
  c.set_intensity(s['intensity']);c.set_light_color(u.LinearColor(*s['color'],1))
  for key,value in dict(attenuation_radius=s['radius'],cast_shadows=s['cast_shadows'],max_draw_distance=s['max_draw_distance_cm'],
   max_distance_fade_range=s['fade_range_cm'],indirect_lighting_intensity=s['indirect_lighting_intensity'],
   volumetric_scattering_intensity=s.get('volumetric_scattering_intensity',1.)).items():c.set_editor_property(key,value)
  dimensions=dict(source_width=s['source_width_cm'],source_height=s['source_height_cm']) if area else dict(source_length=s.get('source_length',0),source_radius=s.get('source_radius',0))
  for key,value in dimensions.items():c.set_editor_property(key,value)
 for i,s in enumerate(module['runtime_actors']):
  if s['type']=='scene_container':
   a=HELP['spawn_container'](actors,s,pose,asset);a.set_editor_property('container_id',prefix+'.'+s['container_id']);created.append(a)
  elif s['type']=='glass_door':
   a=spawn(u.WardGlassDoor,s,s['id']);components={c.get_name():c for c in a.get_components_by_class(u.SceneComponent)}
   frame,leaf,hinge=(components[n] for n in ('DoorFrame','DoorLeaf','DoorHinge'))
   frame.set_static_mesh(None);frame.set_collision_profile_name('NoCollision');frame.set_visibility(False)
   mesh=asset(s['leaf']);leaf.set_static_mesh(mesh)
   leaf.set_relative_rotation(u.Rotator(pitch=0,yaw=180 if s['positive_hinge'] else 0,roll=0),False,True)
   for k,v in dict(hinge_on_positive_y=s['positive_hinge'],open_angle_degrees=85,open_seconds=s['open_seconds'],auto_close_seconds=s['auto_close_seconds']).items():a.set_editor_property(k,v)
   bounds=mesh.get_bounding_box();center=(bounds.min+bounds.max)*.5;extent=(bounds.max-bounds.min)*.5;sign=1 if s['positive_hinge'] else -1
   hinge.set_relative_location(u.Vector(0,sign*extent.y,0),False,True)
   leaf.set_relative_location(u.Vector(-center.x,-sign*extent.y-center.y,extent.z-center.z),False,True)
   pane=a.get_editor_property('glass_pane');pane.set_static_mesh(asset(s['pane']))
   for k,source in [('fracture_mesh','fracture'),('fracture_material','fracture_material'),('impact_particles','impact_particles'),('break_sound','sound')]:pane.set_editor_property(k,asset(s[source]))
   pane.set_editor_property('pane_dimensions',u.Vector(*s['dimensions_cm']))
  elif s['type']=='post_process':
   cls=u.EditorAssetLibrary.load_blueprint_class('/Game/Dungeons/HospitalLine20261003/Blueprints/BP_HospitalLineExposure')
   a=spawn(cls,s,'Exposure');bounds=a.get_component_by_class(u.BoxComponent);bounds.set_box_extent(u.Vector(*s['extent']),False)
   bounds.set_collision_enabled(u.CollisionEnabled.NO_COLLISION);bounds.set_hidden_in_game(True)
   c=a.get_component_by_class(u.PostProcessComponent);c.set_editor_property('unbound',False);c.set_editor_property('priority',s['priority']);c.set_editor_property('blend_radius',s['blend_radius'])
   settings=c.get_editor_property('settings')
   for k,v in dict(auto_exposure_min_brightness=s['exposure_ev'],auto_exposure_max_brightness=s['exposure_ev'],auto_exposure_bias=s['exposure_bias'],
     indirect_lighting_intensity=s['indirect_intensity'],color_saturation=u.Vector4(s['saturation'],s['saturation'],s['saturation'],1),
     vignette_intensity=s['vignette'],bloom_intensity=s['bloom']).items():
    settings.set_editor_property('override_'+k,True);settings.set_editor_property(k,v)
   c.set_editor_property('settings',settings)
 return created
