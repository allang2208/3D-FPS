"""Missing third-room treasures; reuse the existing dungeon chest contract."""
import copy
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
BLUEPRINT = '/Game/Dungeons/StationWorkshop20261003/RefineV2/Blueprints/BP_StationUpperTreasure'
PLACEMENTS = {
    'AbandonedAnatomyTheatre': dict(position=[0, -1075, 216.3], yaw=90,
        identity='hospital_rear_gallery_treasure', role='hospital_rear_gallery'),
    'AccumulatorControl': dict(position=[0, 2100, 384.3], yaw=270,
        identity='power_outer_gallery_treasure', role='power_outer_gallery'),
}


def spec(module_id):
    source = json.loads((PROJECT / 'Content/ColdSteelData/treasure_chest_assets.json').read_text('utf8'))
    return dict(skeletal_mesh=source['mesh'], closed_animation=source['close'],
        opening_animation=source['opening'], material_overrides=source['materials'],
        collision_extent=source['collision_extent'], collision_center=source['collision_center'],
        scale=[1, 1, 1], **copy.deepcopy(PLACEMENTS[module_id]))


def is_treasure(prop):
    return 'TreasureChest' in prop.get('skeletal_mesh', '')


def asset_paths(prop):
    return [prop[k] for k in ('skeletal_mesh', 'closed_animation', 'opening_animation')]


def extend_module(module):
    result = copy.deepcopy(module)
    if result['id'] not in PLACEMENTS or any(is_treasure(p) for p in result.get('props', [])):
        return result
    chest = spec(result['id'])
    result.setdefault('props', []).append(chest)
    result['runtime_assets'] = list(dict.fromkeys(result.get('runtime_assets', []) + asset_paths(chest)))
    return result


def extend(catalog):
    result = copy.deepcopy(catalog)
    result['modules'] = [extend_module(m) for m in result['modules']]
    if 'module_asset_paths' in result:
        result['module_asset_paths'] = sorted(set(result['module_asset_paths']) |
            {p for m in result['modules'] for c in m.get('props', []) if is_treasure(c) for p in asset_paths(c)})
    return result


def spawn_subject(actors, load, chest, pose, map_path, theme_tag):
    import unreal as u
    a = math.radians(pose.get('yaw', 0))
    x, y, z = chest['position']
    ox, oy, oz = pose['position']
    location = u.Vector(ox + x * math.cos(a) - y * math.sin(a),
                        oy + x * math.sin(a) + y * math.cos(a), oz + z)
    actor = actors.spawn_actor_from_class(load(BLUEPRINT).generated_class(), location,
        u.Rotator(pitch=0, yaw=pose.get('yaw', 0) + chest['yaw'], roll=0))
    if not actor:
        raise RuntimeError('Could not place third-room treasure')
    actor.set_actor_label('ThirdRoomTreasure_' + chest['identity'])
    actor.set_folder_path(theme_tag.split('.')[0] + '/' + pose['id'] + '/Treasure')
    actor.set_actor_scale3d(u.Vector(*chest['scale']))
    actor.set_editor_property('tags', [u.Name(t) for t in (
        theme_tag, pose['id'], 'ThirdRoomTreasure20261007', 'DungeonTreasureChest',
        'FutureTreasureLoot', 'DungeonTreasure.HubTest',
        'DungeonChestClaim.' + map_path.rsplit('/', 1)[-1] + '.' + chest['identity'])])
    mesh = actor.skeletal_mesh_component
    mesh.set_skeletal_mesh_asset(load(chest['skeletal_mesh']))
    mesh.set_mobility(u.ComponentMobility.MOVABLE)
    mesh.set_collision_profile_name('NoCollision')
    for i in range(mesh.get_num_materials()):
        material = mesh.get_material(i)
        path = chest['material_overrides'].get(material.get_name()) if material else None
        if path:
            mesh.set_material(i, load(path))
    closed = load(chest['closed_animation'])
    mesh.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
    mesh.play_animation(closed, False)
    animation = mesh.get_editor_property('animation_data')
    animation.set_editor_property('saved_position', closed.get_play_length())
    animation.set_editor_property('saved_play_rate', 0.)
    animation.set_editor_property('saved_playing', False)
    mesh.set_editor_property('animation_data', animation)
    box = actor.get_component_by_class(u.BoxComponent)
    if not box:
        raise RuntimeError('Existing chest Blueprint lacks collision box')
    box.set_box_extent(u.Vector(*chest['collision_extent']), False)
    box.set_relative_location(u.Vector(*chest['collision_center']), False, False)
    box.set_collision_profile_name('BlockAll')
    return actor
