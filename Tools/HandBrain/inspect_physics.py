import unreal,json
from pathlib import Path
mesh=unreal.load_asset('/Game/Monsters/HandBrain/SK_HandBrain');pa=unreal.load_asset('/Game/Monsters/HandBrain/PA_HandBrain');actors=unreal.get_editor_subsystem(unreal.EditorActorSubsystem);a=actors.spawn_actor_from_class(unreal.SkeletalMeshActor,unreal.Vector());c=a.skeletal_mesh_component;c.set_skeletal_mesh_asset(mesh)
r={'bones':{n:str(c.get_socket_transform(n,unreal.RelativeTransformSpace.RTS_COMPONENT)) for n in ['root','death_pivot','base','neck','cranium']}}
try:
 r['bodies']=[]
 for b in pa.get_editor_property('skeletal_body_setups'):
  x={'name':str(b.get_editor_property('bone_name')),'geometry':str(b.get_editor_property('agg_geom'))}
  r['bodies'].append(x)
except Exception as e:r['body_inspection_error']=str(e)
actors.destroy_actor(a);Path('D:/FPS3D/FPSGAME/Saved/HandBrain/physics-inspection.json').write_text(json.dumps(r,indent=2));unreal.log('HANDBRAIN_PHYSICS_INSPECTION '+json.dumps(r))
