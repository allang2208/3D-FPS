"""Headless dungeon prototype build (UnrealEditor-Cmd -run=pythonscript).

Runs without an interactive editor so a live session's compile/restart cycle cannot
interrupt it. Creates /Game/GameMaps/L_Dungeon_Prototype from the EBS
Polygonal/Stone kit at a 300 cm module, saves it, and writes a JSON report.

Kit measured in-editor 2026-09-20 (cm):
  wall 300x18x300, floor slab 300x300x170, ceiling 300x297x10,
  stairs 302x309x307 (rises 300), doorframe 300x28x300 (opening inside).

Layout (cell = 300 cm), 8 columns x 2 rows per floor:
  floor 0 (z=0)    : entry[0-1] | corridor[2-3] | combat[4-5] | stair room[6-7, no ceiling]
  floor 1 (z=300)  : boss[0-3]  | corridor[4-5] | landing[6-7, floor hole over the stairs]

Boundary ownership: every grid line is built once. Requests are collected first and
de-duplicated, and a door request wins over a wall request on the same line. Without
this, adjacent rooms each build their shared wall and the meshes z-fight.

Run:
  "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
     D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
     -script=D:/FPS3D/FPSGAME/SourceAssets/DungeonKit20260920/build_dungeon_headless.py \
     -unattended -nop4 -nosplash -nullrhi
"""
import json
import unreal

LEVEL = '/Game/GameMaps/L_Dungeon_Prototype'
STONE = '/Game/EasyBuildingSystem/Meshes/Structures/Polygonal/Stone/'
KIT = {
    'wall': STONE + 'SM_Polygonal_Stone_Wall',
    'floor': STONE + 'SM_Polygonal_Stone_Foundation',
    'ceiling': STONE + 'SM_Polygonal_Stone_Ceiling',
    'stairs': STONE + 'SM_Polygonal_Stone_Stairs',
    'doorframe': STONE + 'SM_Polygonal_Stone_Doorframe',
}
PROPS = {
    'barrel': '/Game/MilitaryTrench/Assets/3D/Ind_Storage_Barrel_Metal_Rust_01/StaticMeshes/SM_Ind_Storage_Barrel_Metal_Rust_01',
    'bench': '/Game/MilitaryTrench/Assets/3D/Mil_Trench_Bench_Wood_01/StaticMeshes/SM_Mil_Trench_Bench_Wood_01',
    'rubble': '/Game/MilitaryTrench/Assets/3D/Ind_Con_Pile_Rubble_Gravel_Patch_01/StaticMeshes/SM_Ind_Con_Pile_Rubble_Gravel_Patch_01',
    'column': '/Game/Props/RomanColumn20260915/SM_RomanColumn_Round_20',
}
CELL = 300.0
WALL_HALF = 150.0
FLOOR_SINK = 85.0
FOLDER = 'DungeonPrototype'

editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

report = {'walls': 0, 'doors': 0, 'floors': 0, 'ceilings': 0, 'props': 0, 'lights': 0, 'stairs': 0,
          'cleared_actors': 0, 'light_notes': [], 'game_mode': None}
slab_owner = {}      # (i, j, z) -> room name, to catch accidental overlaps
boundary = {}        # ('x'|'y', i, j, z) -> True if door requested


def create_or_load_level():
    if unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
        return editor.load_level(LEVEL)
    template = '/Game/MilitaryTrench/Tutorial/Scenes/Scene_Trench_Tutorial'
    if unreal.EditorAssetLibrary.does_asset_exist(template) and editor.new_level_from_template(LEVEL, template):
        return True
    return editor.new_level(LEVEL)


if not create_or_load_level():
    raise RuntimeError('could not create/load ' + LEVEL)

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world is None:
    raise RuntimeError('no editor world after level creation')

# Empty stage: a copied template brings its own scene, and a re-run must not stack.
for a in list(actors_api.get_all_level_actors()):
    actors_api.destroy_actor(a)
    report['cleared_actors'] += 1


def place_static(mesh_path, loc, yaw=0.0, label=None):
    a = actors_api.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator(0.0, 0.0, yaw))
    comp = a.static_mesh_component
    comp.set_static_mesh(unreal.load_asset(mesh_path))
    comp.set_mobility(unreal.ComponentMobility.STATIC)
    a.set_folder_path('/' + FOLDER)
    if label:
        a.set_actor_label(label)
    return a


# ---- pass 1: record every boundary, door overrides wall ----------------------
def request_x(i, j, z, door=False):
    key = ('x', i, j, z)
    boundary[key] = boundary.get(key, False) or door


def request_y(i, j, z, door=False):
    key = ('y', i, j, z)
    boundary[key] = boundary.get(key, False) or door


def room(cols, rows, z, name, doors=(), ceiling=True, holes=(), over_ceiling=False):
    """over_ceiling: an upper room whose cells already stand on the lower room's
    ceiling cap — it needs no floor slab of its own (two caps would z-fight)."""
    c0, cw = cols
    r0, rh = rows
    for i in range(c0, c0 + cw):
        for j in range(r0, r0 + rh):
            cell = (i, j, z)
            if cell in slab_owner:
                raise RuntimeError(f'cell {cell} claimed by both {slab_owner[cell]} and {name}')
            slab_owner[cell] = name
    for i in range(c0, c0 + cw):
        for j, side in ((r0, 'S'), (r0 + rh, 'N')):
            request_x(i, j, z, door=f'{i}:{j}@{side}' in doors)
    for j in range(r0, r0 + rh):
        for i, side in ((c0, 'W'), (c0 + cw, 'E')):
            request_y(i, j, z, door=f'{i}:{j}@{side}' in doors)
    return {'name': name, 'cols': cols, 'rows': rows, 'z': z, 'ceiling': ceiling,
            'holes': list(holes), 'over_ceiling': over_ceiling}


rooms = [
    room((0, 2), (0, 2), 0.0, 'entry', doors={'2:0@E'}),
    room((2, 2), (0, 2), 0.0, 'corridor0', doors={'2:0@W', '4:0@E'}),
    room((4, 2), (0, 2), 0.0, 'combat', doors={'4:0@W', '6:0@E'}),
    room((6, 2), (0, 2), 0.0, 'stairs0', doors={'6:0@W'}, ceiling=False),
    # Over the stair room there is no lower ceiling, so the landing needs its own cap.
    room((6, 2), (0, 2), CELL, 'landing1', doors={'6:0@W'}, holes={(7, 1)}),
    room((4, 2), (0, 2), CELL, 'corridor1', doors={'4:0@W', '6:0@E'}, over_ceiling=True),
    room((0, 4), (0, 2), CELL, 'boss', doors={'4:0@E'}, over_ceiling=True),
]

# ---- pass 2: build ------------------------------------------------------------------
for (axis, i, j, z), is_door in sorted(boundary.items()):
    kind = 'doorframe' if is_door else 'wall'
    if axis == 'x':
        place_static(KIT[kind], ((i + 0.5) * CELL, j * CELL, z + WALL_HALF), 0.0, f'b{kind}_x_{i}_{j}_{int(z)}')
        report['doors' if is_door else 'walls'] += 1
    else:
        place_static(KIT[kind], (i * CELL, (j + 0.5) * CELL, z + WALL_HALF), 90.0, f'b{kind}_y_{i}_{j}_{int(z)}')
        report['doors' if is_door else 'walls'] += 1

for r in rooms:
    c0, cw = r['cols']
    r0, rh = r['rows']
    z = r['z']
    holes = set(r['holes'])
    for i in range(c0, c0 + cw):
        for j in range(r0, r0 + rh):
            if (i, j) not in holes:
                # Ground floor: the thick foundation slab (170 deep), sunk so its top
                # is z=0. Upper floors: a thin cap (9.6 deep) whose top lands at
                # z+307.5, i.e. placed at z. Using a foundation slab upstairs hangs
                # 170 cm into the room below and leaves only 130 cm of clearance,
                # which folds the player capsule on spawn.
                if z == 0.0:
                    place_static(KIT['floor'], ((i + 0.5) * CELL, (j + 0.5) * CELL, z - FLOOR_SINK), 0.0,
                                 f"{r['name']}_floor_{i}_{j}")
                    report['floors'] += 1
                elif not r.get('over_ceiling'):
                    place_static(KIT['ceiling'], ((i + 0.5) * CELL, (j + 0.5) * CELL, z), 0.0,
                                 f"{r['name']}_floor_{i}_{j}")
                    report['floors'] += 1
            if r['ceiling']:
                place_static(KIT['ceiling'], ((i + 0.5) * CELL, (j + 0.5) * CELL, z + CELL), 0.0,
                             f"{r['name']}_ceil_{i}_{j}")
                report['ceilings'] += 1

place_static(KIT['stairs'], (7.5 * CELL, 1.5 * CELL, FLOOR_SINK + 75.0), 0.0, 'stairs_up')
report['stairs'] += 1

# ---- props ---------------------------------------------------------------------------
props = [
    ('column', (0.4, 0.4, 0.0), 0.0), ('column', (1.6, 1.6, 0.0), 0.0),
    ('barrel', (4.4, 0.4, 0.0), 0.0), ('barrel', (4.7, 0.6, 0.0), 25.0),
    ('bench', (5.4, 1.5, 0.0), 90.0), ('rubble', (4.6, 1.6, 0.0), 0.0),
    ('bench', (1.6, 1.5, CELL), 90.0), ('rubble', (2.6, 1.0, CELL), 40.0),
]
for idx, (kind, (cx, cy, cz), yaw) in enumerate(props):
    place_static(PROPS[kind], (cx * CELL, cy * CELL, cz), yaw, f'{kind}_{idx:02d}')
report['props'] = len(props)

# Player start sits well back in the entry room: the portal subsystem puts each
# door 350 cm ahead of the pawn, and at x=1.5 cells that spot falls past the
# entry/corridor wall line. From x=0.5 cells the home door lands inside the room.
# Z matches the hub's start height (floor top + 102): the capsule is 96 half-height,
# so spawning at 20 buries the pawn in the slab and it falls through the level.
start = actors_api.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0.5 * CELL, 1.5 * CELL, 102.0), unreal.Rotator(0, 0, 0))
start.set_folder_path('/' + FOLDER)
start.set_actor_label('DungeonStart')

# ---- lights: all movable, no lighting build needed -----------------------------------
def light_component_of(actor):
    for name in ('point_light_component', 'directional_light_component', 'sky_light_component', 'light_component'):
        comp = getattr(actor, name, None)
        if comp is not None:
            return comp, name
    for comp in actor.get_components_by_class(unreal.LightComponent) or []:
        return comp, 'via_class'
    return None, None


def spawn_light(cls, loc, rot=(0.0, 0.0, 0.0), label='', intensity=None):
    try:
        a = actors_api.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(*rot))
        a.set_folder_path('/' + FOLDER)
        a.set_actor_label(label)
        comp, name = light_component_of(a)
        if comp is not None:
            comp.set_mobility(unreal.ComponentMobility.MOVABLE)
            if intensity is not None:
                comp.set_intensity(intensity)
            report['light_notes'].append(f'{label}:{name}')
        else:
            report['light_notes'].append(f'{label}:no-component')
        return a
    except Exception as e:
        report['light_notes'].append(f'{label}:FAILED {e}')
        return None


spawn_light(unreal.DirectionalLight, (0.0, 0.0, 800.0), rot=(-46.0, -35.0, 0.0), label='DungeonSun', intensity=3.5)
spawn_light(unreal.SkyLight, (0.0, 0.0, 400.0), label='DungeonSkyLight')
spawn_light(unreal.SkyAtmosphere, (0.0, 0.0, 0.0), label='DungeonSkyAtmosphere')
spawn_light(unreal.ExponentialHeightFog, (0.0, 0.0, 0.0), label='DungeonFog')
for name, loc in [('entry', (1.0, 1.0, 260.0)), ('combat', (5.0, 1.0, 260.0)),
                  ('stairs', (7.0, 1.0, 260.0)), ('boss', (2.0, 1.0, CELL + 260.0))]:
    spawn_light(unreal.PointLight, (loc[0] * CELL, loc[1] * CELL, loc[2]), label='light_' + name, intensity=3000.0)
    report['lights'] += 1

try:
    world.get_world_settings().set_editor_property(
        'default_game_mode', unreal.load_class(None, '/Script/FPSGAME.FPSGAMEGameMode'))
    report['game_mode'] = 'FPSGAMEGameMode'
except Exception as e:
    report['game_mode'] = 'FAILED ' + str(e)


def bounds_of(label):
    for a in actors_api.get_all_level_actors():
        if a.get_actor_label() == label:
            origin, extent = a.get_actor_bounds(False)
            return {'origin': [round(origin.x, 1), round(origin.y, 1), round(origin.z, 1)],
                    'extent': [round(extent.x, 1), round(extent.y, 1), round(extent.z, 1)]}
    return None


report['check_wall'] = bounds_of('bwall_x_0_0_0')          # entry south wall, z 0..300
report['check_floor'] = bounds_of('entry_floor_0_0')       # top at z=0
report['check_ceiling'] = bounds_of('entry_ceil_0_0')      # ~z=300
report['check_door'] = bounds_of('bdoorframe_y_2_0_0')     # entry|corridor door
report['check_stairs'] = bounds_of('stairs_up')
report['check_hole_cell'] = bounds_of('landing1_floor_7_1')  # expect null (stair opening)
report['room_count'] = len(rooms)
report['unique_boundaries'] = len(boundary)

if not editor.save_current_level():
    raise RuntimeError('save_current_level failed')

report['map'] = LEVEL
out = unreal.Paths.project_saved_dir() + 'SceneTests/dungeon-prototype.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
unreal.log('DUNGEON_BUILD_OK ' + json.dumps(report))