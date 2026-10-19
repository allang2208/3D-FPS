import unreal as u
import json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/MedicalBossSpawnFix20261018')
def prop(o,n):
 try:return o.get_editor_property(n)
 except Exception:return None
def val(v):
 if v is None or isinstance(v,(bool,int,float,str)):return v
 if isinstance(v,u.Object):return v.get_path_name()
 if isinstance(v,u.Vector):return [v.x,v.y,v.z]
 return str(v)
report={'read_only':True}
cls=u.load_class(None,'/Game/Monsters/BoundCongregate/BP_BoundCongregate.BP_BoundCongregate_C')
cdo=u.get_default_object(cls);cap=prop(cdo,'capsule_component');move=prop(cdo,'character_movement')
report['boss']={'radius':cap.get_scaled_capsule_radius(),'half_height':cap.get_scaled_capsule_half_height(),'nav':{k:val(prop(prop(move,'nav_agent_props'),k)) for k in ['agent_radius','agent_height']}}
game=None
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_Dungeon_Randomized')
report['game_world']=None;report['world']=val(world)
for gen in u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator):
 catalog=prop(gen,'module_catalog_json')
 if catalog:
  m=next(m for m in json.loads(catalog)['modules'] if m['id']=='AbandonedAnatomyTheatre')
  (OUT/'theatre_module.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
  report['walk_mask']=m.get('walk_mask')
  report['meshes']=[]
  for part in m['parts']:
   if not part.get('collision'):continue
   mesh=u.load_asset(part['mesh']);bounds=mesh.get_bounds();body=prop(mesh,'body_setup')
   report['meshes'].append({'mesh':part['mesh'],'origin':val(bounds.origin),'extent':val(bounds.box_extent),'collision_trace_flag':val(prop(body,'collision_trace_flag'))})
  if game:
   manifest=json.loads(prop(gen,'layout_manifest_json'))
   report['rooms']=[n for n in manifest['nodes'] if n['module']=='AbandonedAnatomyTheatre']
report['bound_actors']=[{'name':a.get_name(),'at':val(a.get_actor_location())} for a in u.GameplayStatics.get_all_actors_of_class(world,cls)]
# An isolated transient cube checks only the shared capsule clearance math.
# No pawn is created, BeginPlay is never called, and no package is saved.
cube=None
try:
 actors=u.get_editor_subsystem(u.EditorActorSubsystem)
 cube=actors.spawn_actor_from_class(u.StaticMeshActor,u.Vector(1000000,1000000,-50),transient=True)
 component=cube.get_component_by_class(u.StaticMeshComponent)
 component.set_static_mesh(u.load_asset('/Engine/BasicShapes/Cube.Cube'))
 component.set_collision_profile_name('BlockAll')
 cube.set_actor_scale3d(u.Vector(20,20,1))
 report['clearance_probe']=[]
 for name,radius,height,z in [('penetrating_control',228,225,224),('old_shape',228,225,228),('corrected_shape',228,228,231),('actual_body',225,225,231)]:
  hits=u.SystemLibrary.capsule_overlap_actors(world,u.Vector(1000000,1000000,z),radius,height,
      [u.ObjectTypeQuery.OBJECT_TYPE_QUERY1,u.ObjectTypeQuery.OBJECT_TYPE_QUERY2],u.Actor,[])
  report['clearance_probe'].append({'case':name,'radius':radius,'half_height':height,'center_z':z,'overlaps_floor':cube in (hits or [])})
 report['clearance_probe_valid']=report['clearance_probe'][0]['overlaps_floor']
 if not report['clearance_probe_valid']:
  report['clearance_probe_limitation']='Loaded editor world has no usable query scene: penetrating control did not hit. Use MedicalBossSpawnDiagnosis initialized physics world.'
except Exception as error:
 report['clearance_probe_error']=str(error)
finally:
 if cube:actors.destroy_actor(cube)
(OUT/'current_inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print('MEDICAL_BOSS_INPUTS',json.dumps({k:v for k,v in report.items() if k!='meshes'},ensure_ascii=False))
