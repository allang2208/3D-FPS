"""Plant the repaired mill's stone foot, in centimetres in the tower frame."""
from collections import defaultdict
import math
import random

import unreal as ue

from layout_geometry import house_paths, rotate, wall_segments
from village_yard_dressing import HILLS, MESH, segment_distance


PALETTE = {role: MESH[role] for role in ('grass', 'tuft', 'rough', 'herb', 'stone', 'shard')}
PALETTE.update({
    'hazel': HILLS + 'ForestSpecies20261110/Meshes/SM_Hazel_B',
    'chips': HILLS + 'VillagePerimeter/SM_VillageWallRubbleA',
    'flat': HILLS + 'OldChapel/Meshes/SM_ChapelYardPathStone',
})
GROWTH = {'grass', 'tuft', 'rough', 'herb', 'hazel'}
TAG = 'VillageWindmill.Ground.'


def place_verge(site, plan, kit, current):
    rng = random.Random(527601)
    meshes = {role: ue.load_asset(path) for role, path in PALETTE.items()}
    for role, mesh in meshes.items():
        if not mesh:
            raise RuntimeError('Missing mill ground asset ' + PALETTE[role])
    boxes = {role: mesh.get_bounding_box() for role, mesh in meshes.items()}
    origin = site.get_actor_location()
    yaw = site.get_actor_rotation().yaw

    def local(point):
        return rotate(point[0]*100-origin.x, point[1]*100-origin.y, -yaw)

    def nearby(a, b, width):
        return segment_distance(0., 0., a, b) <= 770.+width

    paths = [(r['points'], r['width']) for r in plan['roads']] + house_paths(plan, kit)
    lanes = [(a, b, w*50.) for points, w in paths
             for a, b in zip(map(local, points), map(local, points[1:]))
             if nearby(a, b, w*50.)]
    walls = [(local(p[1:3]), local(p[3:5]), half*100.) for p, half in wall_segments(plan)]
    walls = [(a, b, w) for a, b, w in walls if nearby(a, b, w)]
    # The west rubble and the rear wall are sources for new growth and spall.
    # Leave their actual cores clear so the deposits join them at the edges.
    rubble = [local(p) for p in plan['rubble'] if math.hypot(*local(p)) < 800.]
    batches = defaultdict(list)
    roots = []
    stones = []

    def place(role, x, y, width, height, sink, heading=None):
        plant = role in GROWTH
        radius = width*.5
        # Leaves can brush masonry; an entire rock or a rooted stem cannot
        # disappear through it. Keep both open leaves and their road clear.
        if math.hypot(x, y) < 379.+radius*(.18 if plant else .56):
            return False
        if 310.-radius < y < 452.+radius and abs(x) < 96.+radius:
            return False
        if any(segment_distance(x, y, a, b) < w+radius for a, b, w in lanes):
            return False
        if any(segment_distance(x, y, a, b) < w+radius*.55 for a, b, w in walls):
            return False
        if any(math.hypot(x-rx, y-ry) < 69.+radius*.45 for rx, ry in rubble):
            return False
        occupied = roots if plant else stones
        separation = width*(.23 if plant else .35)
        if any(math.hypot(x-px, y-py) < separation+pr for px, py, pr in occupied):
            return False
        occupied.append((x, y, separation))
        box = boxes[role]
        span = box.max-box.min
        scale = width/max(span.x, span.y)
        zscale = height/span.z
        heading = rng.uniform(-180., 180.) if heading is None else heading
        dx, dy = rotate((box.min.x+box.max.x)*.5*scale,
                        (box.min.y+box.max.y)*.5*scale, heading)
        # The village pad is level at sublevel Z=0, four cm below the mill's
        # pivot. Fit the rendered bounds, since these kits use different pivots.
        batches[role].append(ue.Transform(
            location=[x-dx, y-dy, -origin.z-sink-box.min.z*zscale],
            rotation=ue.Rotator(yaw=heading), scale=[scale, scale, zscale]))
        return True

    # One younger shoot at the foot of the east thicket; one lower, sheltered
    # plant at the west return. Leave the rear lane and window sills in view.
    for x, y, width, height, angle in [(493, 107, 112, 79, -23), (555, 144, 62, 43, 36),
                                       (-376, -191, 77, 53, 126)]:
        place('hazel', x, y, width, height, 1.7, angle)

    # Lenses follow shelter, not a constant radius. The stretched east patch
    # meets the existing thicket; the west one dies out against the rubble.
    # Dimensions are ellipse semiaxes, then direction, attempts and exposure.
    beds = [
        (477, 117, 153, 76, 9, 33, .86),
        (367, -177, 75, 34, 57, 13, .47),
        (-121, -411, 156, 62, -13, 32, .83),
        (-356, -208, 86, 49, 55, 20, .77),
        (-417, 165, 108, 54, -31, 24, .54),
        (176, 365, 62, 31, -23, 10, .25),
        (-172, 370, 54, 29, 26, 6, .16),
    ]
    for cx, cy, length, depth, angle, count, shelter in beds:
        for _ in range(count):
            phi = rng.uniform(0., math.tau)
            reach = math.sqrt(rng.random())
            dx, dy = rotate(length*reach*math.cos(phi), depth*reach*math.sin(phi), angle)
            x, y = cx+dx, cy+dy
            lush = shelter*(1.-.76*reach**2)
            draw = rng.random()
            role = 'rough' if draw < lush*.52 else 'herb' if draw < lush*.84 else 'tuft'
            width = rng.uniform(24., 45.)*(.7+lush)
            height = rng.uniform(10., 17.)+lush*(30. if role == 'rough' else 13.)
            if not place(role, x, y, width, height, 1.4):
                continue
            for _ in range(rng.choice((1, 1, 2, 3))):
                theta = rng.uniform(0., math.tau)
                distance = rng.uniform(.43, .93)*width
                place('grass', x+math.cos(theta)*distance, y+math.sin(theta)*distance,
                      rng.uniform(16., 34.), rng.uniform(6., 12.)+lush*3., .9)

    # Stone flakes travel outward from a specific bed joint or the exposed toe
    # of a jamb. Break up the fan with gaps, burying the smaller distal fines.
    for x, y, direction, run, width, count in [
        (-365, 151, 159, 113, 39, 17), (-206, -338, -103, 75, 29, 11),
        (126, 365, 44, 60, 21, 9), (341, -190, -13, 45, 18, 6),
    ]:
        place('chips', x, y, width, width*.20, width*.095, direction)
        for _ in range(count):
            progress = rng.random()
            dx, dy = rotate(6.+progress*run, rng.uniform(-1., 1.)*(9.+progress*20.), direction)
            size = rng.uniform(7., 21.)*(1.-.55*progress)
            role = rng.choice(('flat', 'shard', 'flat', 'stone'))
            height = size*rng.uniform(.26, .48)
            place(role, x+dx, y+dy, size, height, height*(.38+.26*progress))

    # Use the actual village grass material variants. Keep rock faces on
    # their own material, especially where they meet the ground color.
    overrides = {}
    foliage = {meshes[role] for role in GROWTH}
    yard = next((a for a in current if a.get_actor_label() == 'Village_Yards_And_Lanes'), None)
    if yard:
        for comp in yard.get_components_by_class(ue.InstancedStaticMeshComponent):
            if comp.static_mesh not in foliage:
                continue
            for i, material in enumerate(comp.get_editor_property('override_materials')):
                if material:
                    overrides[comp.static_mesh, i] = material

    subs = ue.get_engine_subsystem(ue.SubobjectDataSubsystem)
    handles = ue.SubobjectDataBlueprintFunctionLibrary
    parent = subs.k2_gather_subobject_data_for_instance(site)[0]
    owned = {tag[len(TAG):]: c for c in site.get_components_by_class(ue.InstancedStaticMeshComponent)
             for tag in map(str, c.component_tags) if tag.startswith(TAG)}
    for role in PALETTE:
        poses = batches[role]
        comp = owned.get(role)
        if comp:
            comp.modify()
            comp.clear_instances()
        elif poses:
            handle, reason = subs.add_new_subobject(ue.AddNewSubobjectParams(
                parent_handle=parent, new_class=ue.HierarchicalInstancedStaticMeshComponent))
            comp = handles.get_associated_object(handles.get_data(handle))
            if not comp:
                raise RuntimeError(str(reason))
        else:
            continue
        comp.set_mobility(ue.ComponentMobility.STATIC)
        comp.set_relative_transform(ue.Transform(), False, True)
        comp.set_static_mesh(meshes[role])
        for i in range(comp.get_num_materials()):
            if (meshes[role], i) in overrides:
                comp.set_material(i, overrides[meshes[role], i])
        comp.set_editor_property('component_tags', ['VillageWindmill.Restored', TAG+role])
        comp.set_collision_profile_name('NoCollision')
        comp.set_collision_enabled(ue.CollisionEnabled.NO_COLLISION)
        comp.set_editor_property('receives_decals', False)
        comp.set_cast_shadow(role == 'hazel')
        cull = (6800, 10400) if role == 'hazel' else (3700, 6100)
        comp.set_cull_distances(*cull)
        comp.set_visibility(False)
        comp.set_hidden_in_game(True)
        if poses:
            comp.add_instances(poses, False, False, False)
    return {role: len(poses) for role, poses in batches.items()}
