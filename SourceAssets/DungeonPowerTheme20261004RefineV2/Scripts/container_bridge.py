"""Reuse the supplied, existing ColdSteelSceneContainer contract.

Source: References/Supplement/.../IncineratorContainers20261003/Scripts/
unreal_helpers.py and Source/FPSGAME/UI/ColdSteelSceneContainer.*, plus
Dungeons/WardRoomAssembly.cpp. This file never runs the upstream installers.
"""
import pipeline_common as c


def specifications(scene):
    """Resolve authored positions and exact approved prototypes to UE-local data."""
    sections = {s['id']: s for s in scene['rooms'] + scene.get('connectors', [])}
    entries = [(section, item) for section in sections.values()
               for item in section.get('scene_containers', [])]
    entries += [(sections[item['room_id']], item) for item in scene.get('scene_containers', [])]
    resolved = []
    seen = set()
    outlines = set()
    sources = {}
    for section, item in entries:
        relative = item['source_assembly']
        if relative not in sources:
            sources[relative] = c.read(c.source_file(relative))
        source = sources[relative]
        prototype = source['prototypes'][item['prototype']]
        if prototype.get('type') != 'scene_container':
            raise ValueError('Only supplied scene_container prototypes are supported')
        identity = section['id'] + '.' + item['id']
        if identity in seen:
            raise ValueError('Duplicate authored container identity: ' + identity)
        seen.add(identity)
        spec = {k: prototype[k] for k in ('body', 'door', 'hinge', 'opening_motion',
            'opened_yaw', 'opened_roll', 'drawer_travel', 'storage_pages', 'caption') if k in prototype}
        for key in ('caption', 'storage_pages', 'initial_open_fraction', 'body_materials', 'door_materials'):
            if key in item:
                spec[key] = item[key]
        if spec['opening_motion'] not in ('Swing', 'Drawer', 'Lid'):
            raise ValueError('Unsupported source container motion: ' + spec['opening_motion'])
        if not 1 <= spec['storage_pages'] <= 8:
            raise ValueError('Storage page count is outside the existing native contract')
        spec.update(type='scene_container', container_id='PowerTheme20261004RefineV2.' + identity,
                    position=c.vector_m(item['position_m']), yaw=-float(item.get('yaw_deg', 0)),
                    initial_open_fraction=float(item.get('initial_open_fraction', 0)))
        # Prototype hinge/drawer travel/open angles already use UE units/handedness.
        # Only the new local position and placement yaw are converted.
        resolved.append((section, item['id'], spec))
        outlines.add(source['outline'])
    if len(outlines) > 1:
        raise ValueError('Conflicting original container outline contracts; preserve sources')
    for section, part in c.existing_specs(scene):
        if part.get('container_id') and section['id'] + '.' + part['container_id'] not in seen:
            raise ValueError('Blender-only container member has no runtime actor: ' + part['id'])
    return resolved, next(iter(outlines), None)


def asset_paths(resolved, outline):
    paths = {outline} if outline else set()
    for _, _, spec in resolved:
        paths.update([spec['body'], spec['door']])
        for key in ('body_materials', 'door_materials'):
            paths.update(p for p in spec.get(key, []) if p)
    return sorted(paths)


def spawn(u, actors, spec, section, author_id, asset):
    world_position = c.add(c.vector_m(c.origin(section)), spec['position'])
    actor = actors.spawn_actor_from_class(u.ColdSteelSceneContainer, u.Vector(*world_position),
        u.Rotator(pitch=0, yaw=spec['yaw'], roll=0))
    if not actor:
        raise RuntimeError('Native container spawn failed: ' + spec['container_id'])
    actor.set_actor_label('PowerTheme_' + section['id'] + '_' + author_id)
    actor.set_folder_path('PowerTheme/' + section['id'] + '/Containers')
    # Preserve the native ColdSteel.SceneContainer tag from the constructor.
    actor.set_editor_property('tags', list(dict.fromkeys(list(actor.tags) +
        [u.Name('PowerTheme.Subject'), u.Name('PowerTheme.Room.' + section['id'])])))
    for key in ('container_id', 'caption', 'storage_pages'):
        actor.set_editor_property(key, spec[key])
    actor.set_editor_property('opened_yaw', spec.get('opened_yaw', 100.0))
    actor.set_editor_property('opened_roll', spec.get('opened_roll', 105.0))
    actor.set_editor_property('opening_motion', getattr(u.ColdSteelContainerMotion, spec['opening_motion'].upper()))
    actor.set_editor_property('initial_open_fraction', spec['initial_open_fraction'])
    if 'drawer_travel' in spec:
        actor.set_editor_property('drawer_travel', u.Vector(*spec['drawer_travel']))
    # Same mobility-before-mesh ordering as WardRoomAssembly.cpp.
    actor.root_component.set_mobility(u.ComponentMobility.MOVABLE)
    actor.body.set_mobility(u.ComponentMobility.MOVABLE)
    actor.door.set_mobility(u.ComponentMobility.MOVABLE)
    actor.body.set_static_mesh(asset(spec['body']))
    actor.door.set_static_mesh(asset(spec['door']))
    for key, component in (('body_materials', actor.body), ('door_materials', actor.door)):
        for index, material in enumerate(spec.get(key, [])):
            if material:
                component.set_material(index, asset(material))
    actor.body.set_collision_profile_name('BlockAll')
    actor.door.set_collision_profile_name('NoCollision')
    actor.door_hinge.set_relative_location(u.Vector(*spec['hinge']), False, False)
    return actor


def outline_volume(u, actors, path, asset):
    actor = actors.spawn_actor_from_class(u.PostProcessVolume, u.Vector())
    if not actor:
        raise RuntimeError('Container outline volume creation failed')
    actor.set_actor_label('PowerTheme_ContainerOutline')
    actor.set_folder_path('PowerTheme/Environment')
    actor.set_editor_property('tags', [u.Name('ColdSteel.SceneContainer.Outline'), u.Name('PowerTheme.Subject')])
    actor.set_editor_property('unbound', True)
    actor.set_editor_property('priority', 1.0)
    settings = actor.get_editor_property('settings')
    blendables = settings.get_editor_property('weighted_blendables')
    blend = u.WeightedBlendable()
    blend.set_editor_property('weight', 1.0)
    blend.set_editor_property('object', asset(path))
    blendables.set_editor_property('array', [blend])
    settings.set_editor_property('weighted_blendables', blendables)
    actor.set_editor_property('settings', settings)
    return actor
