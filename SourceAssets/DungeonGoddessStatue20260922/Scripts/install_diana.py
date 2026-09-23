"""Place the Diana statue in the ShoredBreach ruin cavity of the authored dungeon.

Stage 2 of 2; requires Receipts/import.json to be at stage 'mesh_saved'.

Placement comes from Config/diana.json:
  room origin (33, 38, 0.94) m + anchor local (14.1, 4, 0) m -> world (4710, -4200, 94) cm
  yaw 153 deg - the statue faces the wall breach (its local 206.57 deg direction), so a
  player squeezing through the breach is met head-on.
The actor label intentionally avoids the DGN_RS_/DGN_B_ prefixes that
install_rooms.py deletes when it rebuilds rooms.

Headless run (no editor open):
    & 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' \
        'D:/FPS3D/FPSGAME/FPSGAME.uproject' -run=pythonscript \
        -script='.../Scripts/install_diana.py' -unattended -nop4 -nosplash -nullrhi -abslog='...'
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'Config' / 'diana.json').read_text(encoding='utf-8'))
PLACE = CFG['placement']
TARGET = CFG['target_map']
BASE = CFG['content_root']

E = u.EditorAssetLibrary
AA = u.get_editor_subsystem(u.EditorActorSubsystem)
ED = u.get_editor_subsystem(u.LevelEditorSubsystem)
UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)

receipt_path = ROOT / 'Receipts' / 'install.json'


def vec3(v):
    """unreal.Vector is not iterable/subscriptable in this binding."""
    return [round(float(v.x), 2), round(float(v.y), 2), round(float(v.z), 2)]


def rot3(r):
    return [round(float(r.pitch), 2), round(float(r.yaw), 2), round(float(r.roll), 2)]


import_receipt = json.loads((ROOT / 'Receipts' / 'import.json').read_text(encoding='utf-8'))
if import_receipt.get('stage') != 'mesh_saved':
    raise RuntimeError('Import stage is %r; finish import_diana.py first' % import_receipt.get('stage'))
if Path(u.Paths.project_dir()).resolve() != ROOT.parents[1].resolve():
    raise RuntimeError('Different project: %s' % u.Paths.project_dir())
if UE.get_game_world():
    raise RuntimeError('Preserve running play session')
# Preserve other sessions' unsaved maps: this installer switches level and saves.
dirty_maps = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]
foreign_dirty = [n for n in dirty_maps if 'l_dungeon_authoredexpansion' not in n.lower()]
if foreign_dirty:
    raise RuntimeError('Unsaved maps owned by another session, refusing to switch level: %s' % foreign_dirty)

receipt = {'stage': 'preparing', 'target': TARGET, 'tests_run': False, 'map_saved': False}
receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')

mesh = u.load_asset(import_receipt['asset_paths']['mesh'])
if not isinstance(mesh, u.StaticMesh):
    raise RuntimeError('Statue mesh missing: %s' % import_receipt['asset_paths']['mesh'])

world = UE.get_editor_world()
if not world or world.get_path_name().split('.')[0] != TARGET:
    if not ED.load_level(TARGET):
        raise RuntimeError('Cannot open target map %s' % TARGET)
receipt['stage'] = 'installing'
receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')

location = u.Vector(*[float(v) for v in PLACE['world_cm']])
rotation = u.Rotator(pitch=0.0, yaw=float(PLACE['yaw_deg']), roll=0.0)

# Idempotent: drop an earlier instance of this same actor only.
removed = 0
for actor in list(AA.get_all_level_actors()):
    if actor.get_actor_label() == PLACE['actor_label']:
        if not AA.destroy_actor(actor):
            raise RuntimeError('Cannot replace previous actor %s' % PLACE['actor_label'])
        removed += 1

actor = AA.spawn_actor_from_class(u.StaticMeshActor, location, rotation)
if not actor:
    raise RuntimeError('Spawn failed')
actor.modify()
actor.set_actor_label(PLACE['actor_label'])
actor.set_folder_path(PLACE['folder_path'])
actor.set_editor_property('tags', [u.Name(t) for t in PLACE['tags']])

component = actor.static_mesh_component
component.modify()
component.set_static_mesh(mesh)
component.set_mobility(u.ComponentMobility.STATIC)
component.set_collision_profile_name('BlockAll')
actor.set_actor_location(location, False, True)
actor.set_actor_rotation(rotation, False)

# Save the map together with its external actor packages (World Partition layout).
dirty = list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages()) + \
        list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
owned = [p for p in dirty if '/gamemaps/l_dungeon_authoredexpansion' in p.get_name().lower()]
saved_owned = 0
if owned:
    if not u.EditorLoadingAndSavingUtils.save_packages(owned, False):
        raise RuntimeError('Owned map package save failed')
    saved_owned = len(owned)
if not ED.save_current_level():
    raise RuntimeError('Map save failed')

actor_bounds = actor.get_actor_bounds(False)
receipt.update({
    'stage': 'map_saved',
    'map_saved': True,
    'replaced_previous_actors': removed,
    'actor': {
        'label': actor.get_actor_label(),
        'class': actor.get_class().get_name(),
        'mesh': import_receipt['asset_paths']['mesh'],
        'material_instance': import_receipt['asset_paths']['material_instance'],
        'location_cm': vec3(actor.get_actor_location()),
        'rotation_deg': rot3(actor.get_actor_rotation()),
        'folder': str(actor.get_folder_path()),
        'tags': [str(t) for t in actor.get_editor_property('tags')],
        'collision_profile': 'BlockAll',
        'mobility': 'STATIC',
    },
    'anchor': {
        'room': PLACE['room'], 'role': PLACE['anchor_role'], 'index': PLACE['anchor_index'],
        'room_origin_m': PLACE['room_origin_m'], 'anchor_local_m': PLACE['anchor_local_m'],
        'facing_target_local_m': PLACE['facing_target_local_m'], 'yaw_deg': PLACE['yaw_deg'],
    },
    'actor_bounds_cm': {'origin': vec3(actor_bounds[0]),
                        'extent': vec3(actor_bounds[1])},
    'saved_owned_packages': saved_owned,
})
receipt_path.write_text(json.dumps(receipt, indent=2, default=str), encoding='utf-8')
u.log('GODDESS_STATUE_INSTALL ' + json.dumps(receipt['actor']))
print('GODDESS_STATUE_INSTALLED', json.dumps(receipt['actor']))
