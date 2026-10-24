"""Requested per-light/fixture inventory, plus the TV wall and apartment doors."""
from pathlib import Path
import unreal as u,json
R=Path(__file__).resolve().parent;MAP='/Game/GameMaps/L_CyberpunkApartment'
s=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if s and s.get_game_world():raise RuntimeError('Preserve active play world')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map edits')
world=s.get_editor_world() if s else None
if not world or world.get_path_name().split('.')[0]!=MAP:world=u.EditorLoadingAndSavingUtils.load_map(MAP)
report=dict(map=MAP,lights=[],fixtures=[],doors=[],controllers=[])
def props(o,names):
 d={}
 for name in names:
  value=o.get_editor_property(name)
  d[name]=value if isinstance(value,(float,int,str,bool)) else list(value.to_tuple()) if hasattr(value,'to_tuple') else str(value)
 return d
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
 label=a.get_actor_label()
 for c in a.get_components_by_class(u.LightComponent):
  r=dict(actor=label,actor_class=a.get_class().get_name(),component=c.get_name(),kind=c.get_class().get_name(),location=list(c.get_world_location().to_tuple()),forward=list(c.get_forward_vector().to_tuple()),right=list(c.get_right_vector().to_tuple()),up=list(c.get_up_vector().to_tuple()),rotation=props(c.get_world_rotation(),['pitch','yaw','roll']),scale=list(c.get_world_scale().to_tuple()))
  r.update(props(c,['intensity','light_color','cast_shadows','use_temperature','temperature','indirect_lighting_intensity','volumetric_scattering_intensity','max_draw_distance','max_distance_fade_range']))
  if isinstance(c,u.LocalLightComponent):r.update(props(c,['intensity_units','attenuation_radius']))
  if isinstance(c,u.RectLightComponent):r.update(props(c,['source_width','source_height','barn_door_angle','barn_door_length']))
  if isinstance(c,u.SpotLightComponent):r.update(props(c,['inner_cone_angle','outer_cone_angle']))
  report['lights'].append(r)
 if isinstance(a,u.ColdSteelSlidingDoor):report['doors'].append(dict(actor=label,auto_close_seconds=a.get_editor_property('auto_close_seconds')))
 if label=='AP7_Atmosphere':
  report['controllers']=[dict(actor=b.get_editor_property('actor').get_actor_label() if b.get_editor_property('actor') else None,base=b.get_editor_property('base_intensity'),day=b.get_editor_property('day_factor'),night=b.get_editor_property('night_factor')) for b in a.get_editor_property('lights')]
 selected=(label.startswith(('AP_Lighting_','AP_Ceiling','AP_Container_Living_Console','AP_Living_TV','AP_Gym_Fixtures','AP_BathFixtures','AP_BathLighting','AP_EntryLanding','AP_LivingTV')) or label in ('AP_Wall_EastPartition','AP_Wall_CorridorSouth','AP_Facade','AP_BathMirror'))
 if not selected:continue
 r=dict(actor=label,location=list(a.get_actor_location().to_tuple()),rotation=props(a.get_actor_rotation(),['pitch','yaw','roll']),scale=list(a.get_actor_scale3d().to_tuple()),meshes=[])
 for c in a.get_components_by_class(u.StaticMeshComponent):
  if not c.static_mesh:continue
  box=c.static_mesh.get_bounding_box();xf=c.get_world_transform();vs=[u.MathLibrary.transform_location(xf,u.Vector(x,y,z)) for x in (box.min.x,box.max.x) for y in (box.min.y,box.max.y) for z in (box.min.z,box.max.z)]
  bounds=[[min(getattr(v,axis) for v in vs) for axis in ('x','y','z')],[max(getattr(v,axis) for v in vs) for axis in ('x','y','z')]]
  r['meshes'].append(dict(mesh=c.static_mesh.get_path_name(),local_bounds=[list(box.min.to_tuple()),list(box.max.to_tuple())],world_bounds=bounds,materials=[m.get_path_name() if m else None for m in c.get_materials()],slots=[str(x.material_slot_name) for x in c.static_mesh.get_editor_property('static_materials')]))
 report['fixtures'].append(r)
(R/'source-bindings.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('AP12_TARGETS_READ',len(report['lights']),len(report['fixtures']),len(report['doors']))
