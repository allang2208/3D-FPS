"""Author the same native interactive containers used by production generation."""
import math
from pathlib import Path
import unreal as u

ROOT=Path(__file__).resolve().parents[1]
OWNED_TAG='TreatmentContainers.Preview'


def transform(position,pose):
    a=math.radians(pose['yaw']);x,y,z=position;o=pose['position']
    return u.Vector(x*math.cos(a)-y*math.sin(a)+o[0],x*math.sin(a)+y*math.cos(a)+o[1],z+o[2])


def decorate(actor,identity,pose):
    actor.set_actor_label('TreatmentSearch_'+identity)
    actor.set_folder_path('IncineratorLine/Containers/'+pose['id'])
    actor.set_editor_property('tags',list(dict.fromkeys(list(actor.tags)+[
        u.Name(OWNED_TAG),u.Name('IncineratorLine.Subject'),u.Name(pose['id'])])))


def spawn_container(actors,spec,pose,asset):
    actor=actors.spawn_actor_from_class(u.ColdSteelSceneContainer,transform(spec['position'],pose),
        u.Rotator(pitch=0,yaw=pose['yaw']+spec['yaw'],roll=0))
    if not actor:raise RuntimeError('Treatment container spawn failed '+spec['container_id'])
    decorate(actor,spec['container_id'],pose)
    actor.set_editor_property('container_id','IncineratorLine.'+spec['container_id'])
    for key in ('caption','storage_pages'):actor.set_editor_property(key,spec[key])
    actor.set_editor_property('opened_yaw',spec.get('opened_yaw',100.))
    actor.set_editor_property('opened_roll',spec.get('opened_roll',108.))
    actor.set_editor_property('opening_motion',getattr(u.ColdSteelContainerMotion,spec['opening_motion'].upper()))
    actor.set_editor_property('initial_open_fraction',0.)
    if 'drawer_travel' in spec:actor.set_editor_property('drawer_travel',u.Vector(*spec['drawer_travel']))
    actor.body.set_mobility(u.ComponentMobility.MOVABLE)
    actor.body.set_static_mesh(asset(spec['body']));actor.door.set_static_mesh(asset(spec['door']))
    actor.body.set_collision_profile_name('BlockAll');actor.door.set_collision_profile_name('NoCollision')
    actor.door_hinge.set_relative_location(u.Vector(*spec['hinge']),False,False)
    return actor


def spawn_fixed(actors,spec,pose,asset):
    actor=actors.spawn_actor_from_class(u.StaticMeshActor,transform(spec['position'],pose),
        u.Rotator(pitch=0,yaw=pose['yaw']+spec['yaw'],roll=0))
    if not actor:raise RuntimeError('Treatment cabinet carcass spawn failed')
    decorate(actor,pose['id']+'.RecordsCarcass',pose)
    component=actor.static_mesh_component;component.set_static_mesh(asset(spec['mesh']))
    component.set_collision_profile_name('BlockAll');component.set_cast_shadow(True)
    return actor


def ensure_outline(actors,path,label,asset,preview=False):
    # Same shared outline contract, snapshotted without a hospital-author dependency.
    matches=[a for a in actors.get_all_level_actors() if isinstance(a,u.PostProcessVolume)
        and (a.get_actor_label()==label or 'ColdSteel.SceneContainer.Outline' in [str(t) for t in a.tags])]
    actor=matches[0] if matches else actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
    if not actor:raise RuntimeError('Treatment outline volume creation failed')
    actor.modify();actor.set_actor_label(label)
    actor.set_folder_path('IncineratorLine/Environment' if preview else 'Dungeon/Environment')
    actor.set_editor_property('tags',list(dict.fromkeys(list(actor.tags)+[u.Name('ColdSteel.SceneContainer.Outline')])))
    actor.set_editor_property('unbound',True);actor.set_editor_property('priority',1.)
    material=asset(path);settings=actor.get_editor_property('settings')
    blends=settings.get_editor_property('weighted_blendables')
    existing=list(blends.get_editor_property('array'))
    if not any(item.get_editor_property('object')==material for item in existing):
        blend=u.WeightedBlendable();blend.set_editor_property('weight',1.)
        blend.set_editor_property('object',material);existing.append(blend)
        blends.set_editor_property('array',existing);settings.set_editor_property('weighted_blendables',blends)
        actor.set_editor_property('settings',settings)
    return actor
