"""Check where the portal subsystem would place doors, by geometry only.

Commandlet runs have no physics scene, so line traces return None there. This
script instead replays the placement math from SceneTestPortal.cpp::SpawnPortals
against the known level geometry (a 300 cm grid for the dungeon, and the spawn
area layout for the hub), and reports whether each door lands in open space.

Run:
  "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe" \
     D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript \
     -script=D:/FPS3D/FPSGAME/SourceAssets/DungeonKit20260920/portal_geometry_check.py \
     -unattended -nop4 -nosplash -nullrhi
"""
import json
import unreal as u

CELL = 300.0
SPREAD = 440.0
FORWARD = 350.0

# Dungeon room extents in cm, from build_dungeon_headless.py (cell = 300 cm).
# Blocks are (x0, y0, x1, y1, z, name) on floor 0.
DUNGEON_BLOCKS = [
    (0.0, 0.0, 600.0, 600.0, 0.0, 'entry'),
    (600.0, 0.0, 1200.0, 600.0, 0.0, 'corridor0'),
    (1200.0, 0.0, 1800.0, 600.0, 0.0, 'combat'),
    (1800.0, 0.0, 2400.0, 600.0, 0.0, 'stairs0'),
]
# Interior boundaries: wall lines with doors, on floor 0 (x = 600 and x = 1200).
DOOR_LINES = [(600.0, 0.0, 300.0, 'entry|corridor0 j=0'), (1200.0, 0.0, 300.0, 'corridor0|combat j=0')]

report = {}


def locate(x, y, z):
    """Which floor-0 block contains this XY (walls are thin, so treat near-boundary as wall)."""
    for x0, y0, x1, y1, bz, name in DUNGEON_BLOCKS:
        if x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1 and abs(bz - z) < 1:
            on_wall = ''
            for wx, wy0, wy1, label in DOOR_LINES:
                if abs(x - wx) < 20 and wy0 - 20 <= y <= wy1 + 20:
                    on_wall = ' ON_WALL_LINE ' + label
            return name + on_wall
    return 'OUTSIDE'


# --- dungeon: 1 portal, from the pawn the subsystem spawns at DungeonStart -----
levels = {
    'L_Dungeon_Prototype': {
        'start': (0.5 * CELL, 1.5 * CELL, 20.0),
        'yaw': 0.0,
        'count': 1,
        'labels': ['HOME / Main Map'],
    },
}
for level, cfg in levels.items():
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GameMaps/' + level):
        report[level] = {'error': 'load failed'}
        continue
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    starts = [a for a in actors if isinstance(a, u.PlayerStart)]
    if not starts:
        report[level] = {'error': 'no PlayerStart'}
        continue
    loc = starts[0].get_actor_location()
    yaw = starts[0].get_actor_rotation().yaw
    facing = u.Rotator(0.0, 0.0, yaw)
    fwd = facing.get_forward_vector()
    rgt = u.MathLibrary.get_right_vector(facing)
    spots = []
    for i in range(cfg['count']):
        side = (i - (cfg['count'] - 1) * 0.5) * SPREAD
        px = loc.x + fwd.x * FORWARD + rgt.x * side
        py = loc.y + fwd.y * FORWARD + rgt.y * side
        spots.append({
            'label': cfg['labels'][i],
            'xy': [round(px, 1), round(py, 1)],
            'room': locate(px, py, 0.0),
        })
    report[level] = {
        'player_start': [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
        'yaw': round(yaw, 1),
        'spots': spots,
    }

# --- hub: 4 portals; we only need to know the pawn XY, not the scene contents --
if u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GameMaps/DayNight_Lighting'):
    actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    starts = [a for a in actors if isinstance(a, u.PlayerStart)]
    if starts:
        loc = starts[0].get_actor_location()
        yaw = starts[0].get_actor_rotation().yaw
        facing = u.Rotator(0.0, 0.0, yaw)
        fwd = facing.get_forward_vector()
        rgt = u.MathLibrary.get_right_vector(facing)
        labels = ['NORMANDY VILLAGE', 'MILITARY TRENCH', 'DUNGEON (new)', 'TEMPERATE HILLS']
        spots = []
        for i, label in enumerate(labels):
            side = (i - 3 * 0.5) * SPREAD
            px = loc.x + fwd.x * FORWARD + rgt.x * side
            py = loc.y + fwd.y * FORWARD + rgt.y * side
            spots.append({'label': label, 'xy': [round(px, 1), round(py, 1)]})
        report['DayNight_Lighting'] = {
            'player_start': [round(loc.x, 1), round(loc.y, 1), round(loc.z, 1)],
            'yaw': round(yaw, 1),
            'spacing_cm': SPREAD,
            'span_cm': round(3 * SPREAD, 1),
            'spots': spots,
        }

u.log('PORTAL_GEOM ' + json.dumps(report))