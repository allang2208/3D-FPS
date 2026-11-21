"""Carpenter's arcade, timber loft and repairable envelope in the house floor frame."""
import json
import math
from pathlib import Path

import unreal as u

from author_shop import pose, require, standing
from carpenter_floor_repairs import add_ground_deck
from LoftR3.design import SOURCE_SCALE, XY_FACTOR


NORMANDY = '/Game/UnrealNormandy/StaticMeshes/'
SMITH = '/Game/WorldGeneration/TemperateHills/VillageBlacksmith/'
WINDOW = SMITH + 'WindowR7/Meshes/'


def _window(house, name, position, yaw):
    # These leaves have physical pivots. Preserve the window actor's unit scale
    # while matching the larger Normandy wall's recessed jamb and oak stops.
    x, y, z = position
    a = math.radians(yaw)
    xy = SOURCE_SCALE * XY_FACTOR
    transform = pose(house, x + xy * (2.6952 * math.cos(a) + 26 * math.sin(a)),
                     y + xy * (2.6952 * math.sin(a) - 26 * math.cos(a)),
                     z + 30.2665 * SOURCE_SCALE, yaw - 90)
    actors = u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
    actor = actors.spawn_actor_from_class(u.ColdSteelWindow, transform.translation, transform.rotation.rotator())
    actor.set_actor_label('Village_Carpenter_Window_' + name)
    actor.tags = ['VillageCarpenter.Window']
    actor.set_editor_property('use_authored_hinges', True)
    actor.set_editor_property('authored_left_hinge', u.Vector(0, -74, 0))
    actor.set_editor_property('authored_right_hinge', u.Vector(0, 74, 0))
    actor.set_editor_property('fixed_swing_direction', 1)
    actor.set_editor_property('open_angle_degrees', 105)
    actor.set_editor_property('open_seconds', .85)
    meshes = {'WindowFrame': 'WindowMount', 'WindowLeafLeft': 'WindowLeft', 'WindowLeafRight': 'WindowRight'}
    for component in actor.get_components_by_class(u.StaticMeshComponent):
        component.set_static_mesh(require(WINDOW + 'SM_SmithLoft_' + meshes[component.get_name()] + '_R7b'))
        component.set_editor_property('receives_decals', False)
    actor.call_method('RefreshAuthoredGeometry')


def assemble_shell(house, add):
    root = Path(__file__).resolve().parents[3]
    # This donor already carries the wider plan of the shop. Its roof, floor,
    # gables and foundation corners share the same seams as the oak loft kit.
    kits = json.loads((root / 'SourceAssets/TemperateHillsVillage/house-pieces.json').read_text(encoding='utf-8'))
    parts = kits['SL_Blacksmith_LoftR3']
    floor = max(p['pos'][2] + 20 * p['scale'][2] for p in parts if 'SM_WoodenFloor_' in p['mesh'])
    base = pose(house, 0, 0, -floor * SOURCE_SCALE, scale=SOURCE_SCALE)
    local_frame = pose(house, 0, 0)

    def part_transform(p, path=None, state='Common'):
        pitch, yaw, roll = p['rot']
        local = u.Transform(location=p['pos'], rotation=u.Rotator(pitch=pitch, yaw=yaw, roll=roll), scale=p['scale'])
        add(state, path or p['mesh'], u.MathLibrary.compose_transforms(local, base), p['materials'], p['profile'])

    for p in parts:
        name = p['mesh'].rsplit('.', 1)[-1]
        x, y, z = p['pos']
        if name == 'SM_Roof_00A' and y < 0:
            part_transform(p, NORMANDY + 'SM_RoofDamaged_01A', 'Ruined')
            part_transform(p, state='Repaired')
        elif name.startswith('SM_Roof') or name == 'SM_H_OldWall_Triangle_00A':
            part_transform(p)
        elif name == 'SM_H_WallCorner_00A' and (z > -100 or y > 0):
            part_transform(p)
        elif x < 0 and y < -300 and z > -145 and name in (
                'SM_H_OldWall_00A_PieceB', 'SM_H_OldWall_00A_PieceC',
                'SM_H_OldWall_00A_PieceD', 'SM_MortarChunk_03A'):
            # Keep the bonded sill and west return. The higher central stones
            # and the mortar behind them fell together, exposing the oak frame.
            part_transform(p, state='Ruined')

    xy = SOURCE_SCALE * XY_FACTOR
    lower = (-297.4087 - floor) * SOURCE_SCALE
    upper = (2.5913 - floor) * SOURCE_SCALE
    x_left, x_right = -288.5354 * xy, 291.4646 * xy
    y_front, y_back = -290 * xy, 290 * xy
    west_bay, east_bay = -148.5354 * xy, 151.4646 * xy
    front_bay, rear_bay = -150 * xy, 150 * xy

    def wall(x, y, z, yaw, window_name=None):
        path = WINDOW + 'SM_SmithWindowWall_R7' if window_name else NORMANDY + 'SM_H_OldWall_00A'
        scale = u.Transform(scale=[xy, xy, SOURCE_SCALE])
        add('Common', path, u.MathLibrary.compose_transforms(scale, pose(house, x, y, z, yaw)))
        if window_name:
            _window(house, window_name, (x, y, z), yaw)

    # Ground floor: the middle and both street-facing bays are open for long
    # stock. The return stair and back storage sit against full-height masonry.
    wall(west_bay, y_back, lower, 180)
    wall(east_bay, y_back, lower, 180, 'Workroom')
    wall(x_left, rear_bay, lower, -90)
    wall(x_right, rear_bay, lower, 90)

    # The street-side western bay gets a carpenter-built weatherboard repair.
    # The other front bay and eastern gable have operable upstairs windows.
    wall(east_bay, y_front, upper, 0, 'Street')
    wall(west_bay, y_back, upper, 180)
    wall(east_bay, y_back, upper, 180)
    wall(x_right, front_bay, upper, 90)
    wall(x_right, rear_bay, upper, 90, 'Loft')
    wall(x_left, front_bay, upper, -90)
    wall(x_left, rear_bay, upper, -90)

    mortar = '/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A'

    def joint(x, y, z, sx, sy, sz):
        core = u.Transform(location=[x, y, z], scale=[sx / 100, sy / 100, sz / 100])
        add('Common', '/Engine/BasicShapes/Cube', u.MathLibrary.compose_transforms(core, local_frame), (mortar,))

    # The joint backing is narrower than the stone, outside the window reveals.
    joint(1.4646 * xy, y_back, lower, 42, 14, 355)
    joint(1.4646 * xy, y_back, upper, 42, 14, 355)
    for x in (x_left, x_right):
        joint(x, 0, upper, 14, 42, 355)
    for x in (-322.5924 * SOURCE_SCALE, 314.6870 * SOURCE_SCALE):
        joint(x, 0, 846, 14, 20, 348)

    for name in ('ArcadeFrame_R4', 'UpperFloor', 'Stair'):
        add('Common', SMITH + 'LoftR3/Meshes/SM_SmithLoft_' + name, local_frame)
    add('Common', SMITH + 'DetailR6/Meshes/SM_SmithLoft_Guardrails_R6', local_frame,
        extra=('Traversal.GuardrailDrop',))

    # Both plank variants have real worn edges and lengthwise grain. Scale each
    # from its own mesh bounds, preserving its pivot and the direction of grain.
    planks = []
    for name in ('SM_HW_Plank_00A', 'SM_HW_Plank_01A'):
        path = NORMANDY + name
        bounds = require(path).get_bounding_box()
        planks.append((path, (bounds.max + bounds.min) * .5, bounds.max - bounds.min))

    def board(state, a, b, depth, width, variant=0, upright_yaw=0, profile='BlockAll', mats=()):
        dx, dy, dz = (b[i] - a[i] for i in range(3))
        plan = math.hypot(dx, dy)
        yaw = math.degrees(math.atan2(dy, dx)) if plan else upright_yaw
        rotation = u.Rotator(pitch=math.degrees(math.atan2(dz, plan)), yaw=yaw)
        path, middle, span = planks[variant]
        scale = [math.hypot(plan, dz) / span.x, depth / span.y, width / span.z]
        placement = u.Transform(location=[(a[i] + b[i]) * .5 for i in range(3)], rotation=rotation, scale=scale)
        pivot = u.MathLibrary.compose_transforms(u.Transform(location=-middle), placement)
        add(state, path, u.MathLibrary.compose_transforms(pivot, local_frame), mats, profile=profile)

    add_ground_deck(parts, part_transform, board)

    # A low ventilated screen admits raking light at the stock-preparation end.
    # The east beam and diagonal carry the masonry above in either condition.
    board('Common', (390, -392, 332), (390, 14, 332), 26, 29, 1)
    board('Common', (390, -5, 0), (390, -5, 332), 21, 23, upright_yaw=90)
    board('Common', (390, -8, 245), (390, -96, 326), 13, 15)
    board('Common', (390, -370, 0), (390, -370, 329), 19, 18, upright_yaw=90)
    board('Common', (386, -213, 0), (386, -213, 130), 10, 12, upright_yaw=90)
    for row, height in enumerate((16, 41, 66, 91, 116)):
        y_end = -5 if row < 2 else (-188, -237, -302)[row - 2]
        board('Ruined', (390, -370, height), (390, y_end, height - row), 6, 19, row % 2)
        board('Repaired', (390, -370, height), (390, -5, height), 6, 19, row % 2)

    # A shouldered oak frame outlines the skyline gap in both states. The
    # repaired bay shows exterior overlapping courses and an interior wind brace.
    board('Common', (-386, -386, 679), (6, -386, 679), 17, 19, 1)
    for x in (-379, 1):
        board('Common', (x, -386, 348), (x, -386, 674), 15, 16)
    board('Repaired', (-383, -386, 361), (4, -386, 361), 17, 16, 1)
    board('Repaired', (-371, -379, 369), (-8, -379, 670), 11, 15, 1)
    board('Repaired', (-187, -389, 362), (-187, -389, 679), 11, 12)
    finishes = '/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_Carpenter'
    sawn, iron = (finishes + 'Sawn',), (finishes + 'Iron',)
    # Three nail lines sit over the two jambs and the new intermediate stud.
    # At these positions the outside faces of the two scanned planks are
    # 1.4–1.9 cm forward of their nominal centres.
    fixings = ((-375, 1.), (-187, -2.), (-3, 2.))
    for row in range(15):
        z = 369 + row * 20.75
        proud = row % 2
        y = -398 if proud else -394
        board('Repaired', (-382, y, z), (4, y, z), 5, 23, proud, mats=sawn)
        for x, lift in fixings:
            if proud:
                # Local packing sits behind this outer course and beds into
                # the stud. Stop short of the neighbouring recessed courses.
                board('Repaired', (x, -393.7, z-7), (x, -393.7, z+7),
                      9.4, 7, profile='NoCollision')
            nail = u.Transform(location=[x, y-1.3, z+lift], rotation=u.Rotator(roll=90),
                               scale=[.014, .012, .018])
            add('Repaired', '/Engine/BasicShapes/Cylinder',
                u.MathLibrary.compose_transforms(nail, local_frame), iron, profile='NoCollision')

    # The long stone rests on its lower edge with the upper end leaning back
    # against the chipped face of PieceC; its lowest vertex is on the loft.
    leaning = u.Transform(location=[-272, -349.70, 387.875],
                          rotation=u.Rotator(pitch=54, yaw=-84), scale=[.82]*3)
    add('Ruined', NORMANDY+'SM_Brick_01A',
        u.MathLibrary.compose_transforms(leaning, local_frame), profile='NoCollision')
    # The other fallen stones lie on separate footprints clear of the stair.
    for name, x, y, z, yaw, scale in [
        ('SM_Brick_02A', -315, -295, 360, -38, .79),
        ('SM_Brick_00A', -222, -311, 360, 9, .51),
        ('SM_Brick_00A', -341, -420, -4, 19, .78),
        ('SM_Brick_01A', -279, -445, -4, -26, .6),
    ]:
        path = NORMANDY + name
        add('Ruined', path, standing(house, path, x, y, z, yaw, scale), profile='NoCollision')
