"""Give the existing house 05 masonry and furnishings to its repairable mill site."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import unreal as ue

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
sys.path[:0] = [str(HERE.parent / 'AbandonedVillage'), str(HERE.parent / 'VillageBlacksmith')]
from author_shop import BENCH, CRATE, KIT, require, shell_transform
from layout_geometry import plot_geometry
from room_daylight import SHOP_DAYLIGHT, apply_daylight
from repair_house_instances import transfer_ruin
from windmill_verge import place_verge
from mill_yard import install_mill_yard

SITE_TAG = 'VillageWindmill.Site'
MESHES = '/Game/WorldGeneration/TemperateHills/VillageWindmill/Meshes/SM_Windmill_'
SUPPORT_BEAM = '/Game/UnrealNormandy/StaticMeshes/SM_HW_Plank_01A'
HOIST_HEADER = (0, -233, 816)


def refresh_hoist_header(site):
    # The four existing frame timbers share one ISM, with pivots taken from the
    # Normandy mesh. Shift just the header supporting the loft hoist.
    for c in site.get_components_by_class(ue.InstancedStaticMeshComponent):
        if not c.static_mesh or c.static_mesh.get_path_name().split('.')[0] != SUPPORT_BEAM:
            continue
        if 'VillageWindmill.Restored' not in map(str,c.component_tags):
            continue
        bounds = c.static_mesh.get_bounding_box()
        center = (bounds.min+bounds.max)*.5
        for i in range(c.get_instance_count()):
            pose = c.get_instance_transform(i,False)
            at = ue.MathLibrary.transform_location(pose,center)
            if (at-ue.Vector(0,-208,816)).length() < 1.:
                pose.translation += ue.Vector(0,-25,0)
                c.modify()
                if not c.update_instance_transform(i,pose,False,True,True):
                    raise RuntimeError('Could not seat the loft header on the revised hoist frame')


def install_fittings(site, kit):
    """Seat the two gear trains and hoist on the building fabric at their actual journals."""
    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    handles = ue.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(site)[0]

    def batch(mesh, state, poses, solid=False, material=None):
        handle, reason = subs.add_new_subobject(ue.AddNewSubobjectParams(
            parent_handle=parent, new_class=ue.InstancedStaticMeshComponent))
        comp = handles.get_associated_object(handles.get_data(handle))
        if not comp:
            raise RuntimeError(str(reason))
        comp.set_mobility(ue.ComponentMobility.STATIC)
        comp.set_relative_transform(ue.Transform(), False, True)
        comp.set_static_mesh(mesh)
        if material:
            comp.set_material(0, material)
        tags = ['VillageWindmill.' + state]
        if solid:
            tags.extend(['VillageWindmill.Solid', 'HillsStaticSupport'])
        comp.set_editor_property('component_tags', tags)
        comp.set_editor_property('receives_decals', False)
        comp.set_collision_profile_name('BlockAll' if solid else 'NoCollision')
        comp.add_instances(poses, False, False, False)
        if state == 'Restored':
            comp.set_visibility(False)
            comp.set_hidden_in_game(True)
            comp.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)

    def fit(mesh, center, size, heading=0):
        bounds = mesh.get_bounding_box()
        span = bounds.max - bounds.min
        scale = [size[0]/span.x, size[1]/span.y, size[2]/span.z]
        frame = ue.Transform(location=center, rotation=ue.Rotator(yaw=heading), scale=scale)
        return ue.MathLibrary.compose_transforms(ue.Transform(location=-(bounds.min+bounds.max)*.5), frame)

    beam = require(SUPPORT_BEAM)
    stone = require('/Game/UnrealNormandy/StaticMeshes/SM_Brick_00A')
    floor = require('/Engine/BasicShapes/Cylinder')
    batch(floor, 'Restored', [fit(floor, [0,0,-2], [665,665,8])], True,
          require('/Game/WorldGeneration/TemperateHills/OldChapel/Materials/M_ChapelFlagstone'))
    batch(stone, 'Restored', [fit(stone, [0,0,34], [48,52,68])], True)
    cap_yaw = ue.Transform(rotation=ue.Rotator(yaw=42))
    arms = [fit(beam, [-112,0,196], [180,20,18]), fit(beam, HOIST_HEADER, [469,21,20])]
    for y, width in [(244,478), (-1,666)]:
        arms.append(ue.MathLibrary.compose_transforms(fit(beam, [0,y,892], [width,27,22]), cap_yaw))
    batch(beam, 'Restored', arms)

    def on_ground(mesh, x, y, rotation):
        pose = ue.Transform(rotation=rotation)
        bounds = mesh.get_bounding_box()
        bottom = min(ue.MathLibrary.transform_location(pose, ue.Vector(a,b,c)).z
                     for a in (bounds.min.x,bounds.max.x) for b in (bounds.min.y,bounds.max.y)
                     for c in (bounds.min.z,bounds.max.z))
        return ue.Transform(location=[x,y,-bottom], rotation=rotation)

    # Two salvageable original fittings outside the ruined wall identify the mill from the road.
    batch(kit['A01'], 'Ruin', [on_ground(kit['A01'], -108,412,ue.Rotator(pitch=88,roll=7))])
    batch(kit['A03'], 'Ruin', [on_ground(kit['A03'], -169,464,ue.Rotator(roll=81,yaw=16))])


def install_windmill(actors, plan, kit):
    house = next(h for h in plan['houses'] if h[0] == '05')
    pieces = kit[house[2]]
    shape = plot_geometry(house, pieces, plan)
    scale = plan['house_scale']
    frame = ue.Transform(location=[house[3]*100, house[4]*100, 4-shape['floor']*scale],
                         rotation=ue.Rotator(yaw=house[5]), scale=[scale]*3)
    door, normal = shape['entry'], shape['normal']
    position = ue.Vector(door[0]*100-376.5*normal[0], door[1]*100-376.5*normal[1], 4)
    facing = ue.Rotator(yaw=math.degrees(math.atan2(normal[1], normal[0]))-90.)
    current = list(actors.get_all_level_actors())
    site = next((a for a in current if SITE_TAG in map(str, a.tags)), None)
    catalog = PROJECT / 'SourceAssets/HillsVillageWindmill/ComponentsR2/catalog.json'
    meshes = {p['id']: require(MESHES+p['id']) for p in json.loads(catalog.read_text(encoding='utf-8'))}
    transferred = 0
    if not site:
        site = actors.spawn_actor_from_class(ue.HillsWindmill, position, facing)
        site.set_actor_label('Village_05_Windmill')
        expected = defaultdict(list)
        for piece in pieces:
            if not piece['mesh'].endswith('.SM_Door_00A'):
                expected[piece['mesh'].split('.')[0]].append(shell_transform(piece, frame).translation)

        transferred = transfer_ruin(current, site, expected, shape, prefix='VillageWindmill',
                                    loose_furniture={KIT+'TimberBed', KIT+'OakTable', KIT+'OakShelf', BENCH, CRATE})
        install_fittings(site, meshes)
    else:
        refresh_hoist_header(site)
    site.modify()
    site.set_editor_property('part_meshes', meshes)
    ground_instances = place_verge(site, plan, kit, current)
    mill_yard = install_mill_yard(site)
    room = next((a for a in current if a.get_actor_label().startswith('Village_InteriorVision_05_')), None)
    if room:
        room.modify()
        room.set_actor_transform(ue.Transform(location=position, rotation=facing), False, False)
        room.set_editor_property('room_minimum', ue.Vector(-245, -245, 0))
        room.set_editor_property('room_maximum', ue.Vector(245, 245, 805))
        apply_daylight(room, SHOP_DAYLIGHT['05'])
    return dict(site=site.get_path_name(), house=house[0], meshes=len(meshes), ground_instances=ground_instances, yard=mill_yard,
                transferred_ruin_instances=transferred, location_cm=[position.x, position.y, position.z],
                yaw_degrees=facing.yaw)
