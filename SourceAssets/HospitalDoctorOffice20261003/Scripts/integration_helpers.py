"""Apply only this batch's ward meshes and office furnishings to the existing sample."""
import json,math
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
TAG='HospitalOffice.Preview.Static'
def update_preview(actors,line,asset):
 office=json.loads((ROOT/'Config/office.json').read_text('utf8'))
 manifest=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))
 replacements={i['replaces']:i['asset'] for i in manifest['objects'] if 'replaces' in i}
 new_paths=set(replacements.values())
 pose=next(p for p in line['placements'] if p['id']=='AbandonedIsolationWard')
 angle=math.radians(pose['yaw']);origin=pose['position']
 count=0
 for actor in list(actors.get_all_level_actors()):
  tags=[str(t) for t in actor.tags]
  if TAG in tags:actors.destroy_actor(actor);continue
  if 'HospitalLine.Subject' not in tags or 'AbandonedIsolationWard' not in tags or not isinstance(actor,u.StaticMeshActor):continue
  component=actor.static_mesh_component;mesh=component.static_mesh
  if not mesh:continue
  path=mesh.get_path_name().split('.')[0]
  if path in replacements or path in new_paths:
   actor.modify();component.modify()
   component.set_static_mesh(asset(replacements.get(path,path)))
   component.set_editor_property('override_materials',[])
   count+=1
 for spec in office['parts']:
  x,y,z=spec['position'];at=u.Vector(origin[0]+x*math.cos(angle)-y*math.sin(angle),
    origin[1]+x*math.sin(angle)+y*math.cos(angle),origin[2]+z)
  actor=actors.spawn_actor_from_class(u.StaticMeshActor,at,u.Rotator(pitch=0,yaw=pose['yaw']+spec['yaw'],roll=0))
  if not actor:raise RuntimeError('Office furniture could not be created '+spec['id'])
  actor.set_actor_label('HospitalOffice_'+spec['id'].split('.')[-1])
  actor.set_folder_path('HospitalLine/DoctorOffice')
  actor.set_editor_property('tags',[u.Name(TAG),u.Name('HospitalLine.Subject'),u.Name('AbandonedIsolationWard')])
  component=actor.static_mesh_component;component.set_static_mesh(asset(spec['mesh']))
  component.set_collision_profile_name('BlockAll' if spec['collision'] else 'NoCollision')
 return dict(ward_detail_meshes=count,office_furniture=len(office['parts']))
