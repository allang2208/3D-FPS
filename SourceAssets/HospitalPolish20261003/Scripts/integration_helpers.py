"""Update only the three requested fixture kinds in the existing hospital sample."""
import math
import runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
rules=runpy.run_path(str(ROOT/'Scripts/fixture_rules.py'))


def update_preview(actors,line,asset):
    counts=dict(pumps=0,sinks=0,spares_removed=0)
    poses={p['id']:p for p in line['placements'] if p['id']!='Transit'}
    for actor in actors.get_all_level_actors():
        if not isinstance(actor,u.StaticMeshActor):continue
        tags=[str(t) for t in actor.tags]
        if 'HospitalLine.Subject' not in tags:continue
        component=actor.static_mesh_component;mesh=component.get_editor_property('static_mesh')
        if not mesh:continue
        path=mesh.get_path_name().split('.')[0];spec=None;pose=None
        if 'Drainage' in tags:
            if path==rules['OLD_SPARES']:
                actors.destroy_actor(actor);counts['spares_removed']+=1;continue
            if path in (rules['OLD_PUMP'],rules['PUMP']):
                pose=poses['Drainage'];yaw=(actor.get_actor_rotation().yaw-pose['yaw']+180)%360-180
                spec=rules['pump_part'](dict(yaw=yaw));counts['pumps']+=1
        if 'AbandonedAnatomyTheatre' in tags and path in (rules['OLD_SINK'],rules['SINK']):
            pose=poses['AbandonedAnatomyTheatre'];spec=dict(mesh=rules['SINK'],position=[-600,1147,.3],yaw=0)
            counts['sinks']+=1
        if spec:
            a=math.radians(pose['yaw']);x,y,z=spec['position'];origin=pose['position']
            actor.modify();component.modify();component.set_static_mesh(asset(spec['mesh']))
            component.set_editor_property('override_materials',[]);component.set_collision_profile_name('BlockAll')
            component.set_cast_shadow(True);component.set_visibility(True)
            actor.set_actor_location(u.Vector(x*math.cos(a)-y*math.sin(a)+origin[0],x*math.sin(a)+y*math.cos(a)+origin[1],z+origin[2]),False,True)
            actor.set_actor_rotation(u.Rotator(pitch=0,yaw=pose['yaw']+spec['yaw'],roll=0),True)
            actor.set_actor_scale3d(u.Vector(1,1,1))
    return counts
