"""Shared authoring helpers for the saved hospital sample and its rebuild source."""
import math
import unreal as u

OWNED_TAG='HospitalContainers.Preview'


def struct(cls,**properties):
    value=cls()
    for key,item in properties.items():value.set_editor_property(key,item)
    return value


def configure_bedside(actor,spec,asset):
    config=spec.get('bedside_containers')
    if not config:return
    actor.set_editor_property('bedside_containers',struct(u.WardBedsideContainerSettings,
        body_mesh=asset(config['body']),lid_mesh=asset(config['door']),
        identity_prefix=config['container_id_prefix'],caption=config['caption'],
        hinge=u.Vector(*config['hinge']),opened_roll=config['opened_roll'],
        min_count=config['min_count'],max_count=config['max_count'],bed_gap=config['bed_gap']))


def spawn_container(actors,spec,pose,asset):
    angle=math.radians(pose['yaw']);x,y,z=spec['position'];origin=pose['position']
    position=u.Vector(x*math.cos(angle)-y*math.sin(angle)+origin[0],x*math.sin(angle)+y*math.cos(angle)+origin[1],z+origin[2])
    actor=actors.spawn_actor_from_class(u.ColdSteelSceneContainer,position,u.Rotator(pitch=0,yaw=pose['yaw']+spec['yaw'],roll=0))
    if not actor:raise RuntimeError('Hospital container spawn failed '+spec['container_id'])
    actor.set_actor_label('HospitalSearch_'+spec['container_id'])
    actor.set_folder_path('HospitalLine/Containers/'+pose['id'])
    tags=list(actor.tags)+[u.Name(OWNED_TAG),u.Name('HospitalLine.Subject'),u.Name(pose['id'])]
    actor.set_editor_property('tags',list(dict.fromkeys(tags)))
    actor.set_editor_property('container_id','HospitalLine.'+spec['container_id'])
    for key in ('caption','storage_pages'):
        actor.set_editor_property(key,spec[key])
    actor.set_editor_property('opened_yaw',spec.get('opened_yaw',100.))
    actor.set_editor_property('opened_roll',spec.get('opened_roll',108.))
    actor.set_editor_property('initial_open_fraction',spec.get('initial_open_fraction',0.))
    actor.set_editor_property('opening_motion',getattr(u.ColdSteelContainerMotion,spec['opening_motion'].upper()))
    if 'drawer_travel' in spec:actor.set_editor_property('drawer_travel',u.Vector(*spec['drawer_travel']))
    actor.body.set_static_mesh(asset(spec['body']));actor.door.set_static_mesh(asset(spec['door']))
    actor.body.set_collision_profile_name('BlockAll');actor.door.set_collision_profile_name('NoCollision')
    actor.door_hinge.set_relative_location(u.Vector(*spec['hinge']),False,False)
    for key,component in (('body_materials',actor.body),('door_materials',actor.door)):
        for index,path in enumerate(spec.get(key,[])):component.set_material(index,asset(path))
    return actor


def ensure_outline(actors,path,label,asset,preview=False):
    matches=[actor for actor in actors.get_all_level_actors() if isinstance(actor,u.PostProcessVolume)
        and (actor.get_actor_label()==label or 'ColdSteel.SceneContainer.Outline' in [str(t) for t in actor.tags])]
    actor=matches[0] if matches else actors.spawn_actor_from_class(u.PostProcessVolume,u.Vector())
    if not actor:raise RuntimeError('Hospital outline volume creation failed')
    actor.modify();actor.set_actor_label(label)
    actor.set_folder_path('HospitalLine/Environment' if preview else 'Dungeon/Environment')
    tags=list(actor.tags)+[u.Name('ColdSteel.SceneContainer.Outline')]
    if preview:tags.extend([u.Name(OWNED_TAG),u.Name('HospitalLine.Subject')])
    actor.set_editor_property('tags',list(dict.fromkeys(tags)))
    actor.set_editor_property('unbound',True);actor.set_editor_property('priority',1.)
    material=asset(path);settings=actor.get_editor_property('settings')
    blends=settings.get_editor_property('weighted_blendables')
    existing=list(blends.get_editor_property('array'))
    if not any(item.get_editor_property('object')==material for item in existing):
        existing.append(struct(u.WeightedBlendable,weight=1.,object=material))
        blends.set_editor_property('array',existing);settings.set_editor_property('weighted_blendables',blends)
        actor.set_editor_property('settings',settings)
    return actor
