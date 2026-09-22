"""Build a dungeon prototype level from the existing modular kits.

Kit measured in-editor on 2026-09-20 (audit_kit.py output, cm):
  EBS Polygonal/Stone wall      300 wide x 18 thick x 300 tall, origin centered
  EBS Polygonal/Stone floor     300 x 300 x 170 slab  -> sink 85 so its top is the floor level
  EBS Polygonal/Stone ceiling   300 x 297 x 10 slab   -> sits at wall top
  EBS Polygonal/Stone stairs    302 x 309 x 307       -> rises one 300 level
  EBS Polygonal/Stone doorframe 300 x 28 x 300        -> replaces a wall segment, opening inside
  Props: barrel / bench / rubble pile / roman column

Layout: a two-floor band, 4 rooms per floor, doors between them.
  Floor 0 (z=0)   : entry(0-1) | corridor(2-3) | combat(4-5) | stairs(6-7)
  Floor 1 (z=300) : landing(6-7, stair opening) | corridor(4-5) | boss(2-5)
Cell = 300 cm. Walls sit on cell boundary lines (X-wall at y = j*CELL,
Y-wall at x = i*CELL). Doors are doorframe pieces replacing one wall segment.

Authoring only: creates/updates the level and saves it. No PIE, no acceptance.
The previously open map is restored at the end.

Run: python Tools/AssetPipeline/ue_python_exec.py --script SourceAssets/DungeonKit20260920/build_dungeon.py
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
WALL_HALF = 150.0     # wall is 300 tall, centered on its origin
FLOOR_SINK = 85.0     # foundation slab is 170 tall; sink so the top is the floor level
FOLDER = 'DungeonPrototype'

editor = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors_api = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
world_subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)


def package_path(world):
    """'/Game/GameMaps/Foo.Foo' -> '/Game/GameMaps/Foo' (what load_level wants)."""
    if world is None:
        return ''
    return world.get_path_name().split('.')[0]


def in_our_folder(actor):
    return FOLDER in str(actor.get_folder_path())


# A freshly started editor can still be loading its world; wait briefly.
import time
previous_world = None
for _ in range(20):
    previous_world = world_subsystem.get_editor_world()
    if previous_world is not None:
        break
    unreal.log('DUNGEON_WAIT editor world not ready')
    time.sleep(3)
previous_map = package_path(previous_world)

# ---- level ------------------------------------------------------------------
if not unreal.EditorAssetLibrary.does_asset_exist(LEVEL):
    created = False
    for attempt in range(5):
        if editor.new_level(LEVEL):
            created = True
            break
        unreal.log(f'DUNGEON_RETRY new_level attempt {attempt + 1} failed')
        time.sleep(5)
    if not created:
        raise RuntimeError('new_level failed')
else:
    if not editor.load_level(LEVEL):
        raise RuntimeError('load_level failed')

report = {'walls': 0, 'doors': 0, 'floors': 0, 'ceilings': 0, 'props': 0, 'lights': 0, 'stairs': 0}

# Re-runs must not stack a second dungeon: drop everything we own first.
for a in list(actors_api.get_all_level_actors()):
    if in_our_folder(a):
        actors_api.destroy_actor(a)


def place(mesh_path, loc, yaw=0.0, label=None, mobility=None):
    a = actors_api.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*loc), unreal.Rotator(0.0, 0.0, yaw))
    comp = a.static_mesh_component
    comp.set_static_mesh(unreal.load_asset(mesh_path))
    if mobility is not None:
        comp.set_mobility(mobility)
    a.set_folder_path('/' + FOLDER)
    if label:
        a.set_actor_label(label)
    return a


def x_wall(i, j, z, kind='wall', tag=''):
    """Wall on the boundary line between rows j-1 and j, spanning column i."""
    place(KIT[kind], ((i + 0.5) * CELL, j * CELL, z + WALL_HALF), 0.0, f'{tag}xw_{i}_{j}')
    report['doors' if kind == 'doorframe' else 'walls'] += 1


def y_wall(i, j, z, kind='wall', tag=''):
    """Wall on the boundary line between columns i-1 and i, spanning row j."""
    place(KIT[kind], (i * CELL, (j + 0.5) * CELL, z + WALL_HALF), 90.0, f'{tag}yw_{i}_{j}')
    report['doors' if kind == 'doorframe' else 'walls'] += 1


def slab(i, j, z, ceiling=False, tag=''):
    if ceiling:
        place(KIT['ceiling'], ((i + 0.5) * CELL, (j + 0.5) * CELL, z), 0.0, f'{tag}ceil_{i}_{j}')
        report['ceilings'] += 1
    else:
        place(KIT['floor'], ((i + 0.5) * CELL, (j + 0.5) * CELL, z - FLOOR_SINK), 0.0, f'{tag}floor_{i}_{j}')
        report['floors'] += 1


def room(cols, rows, z, name, doors=(), ceiling=True, skip_cells=()):
    """cols/rows are (start, count) on the cell grid. doors = set of 'i:j@side'."""
    c0, cw = cols
    r0, rh = rows
    for i in range(c0, c0 + cw):
        for j in range(r0, r0 + rh):
            if (i, j) in skip_cells:
                continue
            slab(i, j, z, ceiling=ceiling, tag=name + '_')
    # South (j = r0) and north (j = r0 + rh) boundaries, spanning all columns.
    for i in range(c0, c0 + cw):
        for j, side in ((r0, 'S'), (r0 + rh, 'N')):
            kind = 'doorframe' if f'{i}:{j}@{side}' in doors else 'wall'
            x_wall(i, j, z, kind, name + '_')
    # West (i = c0) and east (i = c0 + cw) boundaries, spanning all rows.
    for j in range(r0, r0 + rh):
        for i, side in ((c0, 'W'), (c0 + cw, 'E')):
            kind = 'doorframe' if f'{i}:{j}@{side}' in doors else 'wall'
            y_wall(i, j, z, kind, name + '_')


# ---- floor 0 ----------------------------------------------------------------
# Entry 2x2 (cols 0-1): door on its east boundary in row 0.
room((0, 2), (0, 2), 0.0, 'entry', doors={'2:0@E'})
# Corridor 2x2 (cols 2-3): west door into entry, east door into combat.
room((2, 2), (0, 2), 0.0, 'corridor0', doors={'2:0@W', '4:0@E'})
# Combat 2x2 (cols 4-5): west door from corridor, east door into stairs room.
room((4, 2), (0, 2), 0.0, 'combat', doors={'4:0@W', '6:0@E'})
# Stair room 2x2 (cols 6-7): west door, no ceiling (stairwell).
room((6, 2), (0, 2), 0.0, 'stairs0', doors={'6:0@W'}, ceiling=False)
place(KIT['stairs'], (7.5 * CELL, 1.5 * CELL, FLOOR_SINK + 75.0), 0.0, 'stairs_up')
report['stairs'] += 1

# ---- floor 1 ----------------------------------------------------------------
Z1 = CELL
# Landing above the stair room; the cell above the stairs stays open.
room((6, 2), (0, 2), Z1, 'landing1', doors={'6:0@W'}, skip_cells={(7, 1)})
# Corridor above the floor-0 corridor.
room((4, 2), (0, 2), Z1, 'corridor1', doors={'4:0@W', '6:0@E'})
# Boss room spanning cols 2-5.
room((2, 4), (0, 2), Z1, 'boss', doors={'6:0@E'})

# ---- props ------------------------------------------------------------------
place(PROPS['column'], (0.4 * CELL, 0.4 * CELL, 0.0), 0.0, 'col_entry_a')
place(PROPS['column'], (1.6 * CELL, 1.6 * CELL, 0.0), 0.0, 'col_entry_b')
place(PROPS['barrel'], (4.4 * CELL, 0.4 * CELL, 0.0), 0.0, 'barrel_combat_a')
place(PROPS['barrel'], (4.7 * CELL, 0.6 * CELL, 0.0), 25.0, 'barrel_combat_b')
place(PROPS['bench'], (5.4 * CELL, 1.5 * CELL, 0.0), 90.0, 'bench_combat')
place(PROPS['rubble'], (4.6 * CELL, 1.6 * CELL, 0.0), 0.0, 'rubble_combat')
place(PROPS['bench'], (2.6 * CELL, 1.5 * CELL, Z1), 90.0, 'bench_boss')
place(PROPS['rubble'], (4.0 * CELL, 1.0 * CELL, Z1), 40.0, 'rubble_boss')
report['props'] = 8

# ---- player start -----------------------------------------------------------
start = actors_api.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(1.5 * CELL, 1.5 * CELL, 20.0), unreal.Rotator(0, 0, 0))
start.set_folder_path('/' + FOLDER)
start.set_actor_label('DungeonStart')

# ---- movable lights ---------------------------------------------------------
for name, loc in [('entry', (1.0 * CELL, 1.0 * CELL, 260.0)),
                  ('combat', (5.0 * CELL, 1.0 * CELL, 260.0)),
                  ('stairs', (7.0 * CELL, 1.0 * CELL, 260.0)),
                  ('boss', (4.0 * CELL, 1.0 * CELL, Z1 + 260.0))]:
    light = actors_api.spawn_actor_from_class(unreal.PointLight, unreal.Vector(*loc), unreal.Rotator(0, 0, 0))
    comp = light.point_light_component
    comp.set_mobility(unreal.ComponentMobility.MOVABLE)
    comp.set_intensity(3000.0)
    comp.set_editor_property('attenuation_radius', 900.0)
    light.set_folder_path('/' + FOLDER)
    light.set_actor_label('light_' + name)
    report['lights'] += 1

# ---- verify alignment on a few pieces ---------------------------------------
def bounds_of(label):
    for a in actors_api.get_all_level_actors():
        if a.get_actor_label() == label:
            origin, extent = a.get_actor_bounds(False)
            return {'origin': [round(origin.x, 1), round(origin.y, 1), round(origin.z, 1)],
                    'extent': [round(extent.x, 1), round(extent.y, 1), round(extent.z, 1)]}
    return None

report['check_wall'] = bounds_of('entry_xw_0_0')          # south wall of entry: z 0..300
report['check_floor'] = bounds_of('entry_floor_0_0')      # slab: top at z=0
report['check_ceiling'] = bounds_of('entry_ceil_0_0')     # cap at z=300
report['check_stairs'] = bounds_of('stairs_up')
report['check_door'] = bounds_of('entry_yw_2_0')          # doorframe on the east boundary

# ---- save and restore -------------------------------------------------------
if not editor.save_current_level():
    raise RuntimeError('save_current_level failed')
if previous_map and previous_map != LEVEL:
    editor.load_level(previous_map)

out = unreal.Paths.project_saved_dir() + 'SceneTests/dungeon-prototype.json'
with open(out, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2)
unreal.log('DUNGEON_BUILD_OK ' + json.dumps(report))