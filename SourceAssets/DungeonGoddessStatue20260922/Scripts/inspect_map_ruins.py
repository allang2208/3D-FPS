"""List the dungeon's ruin-side actors so additional statues can be placed deliberately.

Read-only. Opens L_Dungeon_AuthoredExpansion and dumps every actor whose label looks
like the preserved A-segment / ruin masonry / arch / breach / anchor, with world
positions and bounds, plus a coarse occupancy grid of the ruin wing.

Run headless:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
TARGET = '/Game/GameMaps/L_Dungeon_AuthoredExpansion'
KEYWORDS = ('DGN_A_', 'DGN_Link', 'Ruin', 'Arch', 'Breach', 'Statue', 'Anchor', 'Masonry',
            'Cavity', 'Pocket', 'Earth', 'Debris', 'Stone', 'Prop')

UE = u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED = u.get_editor_subsystem(u.LevelEditorSubsystem)
world = UE.get_editor_world()
if not world or world.get_path_name().split('.')[0] != TARGET:
    if not ED.load_level(TARGET):
        raise RuntimeError('Cannot open %s' % TARGET)


def vec3(v):
    return [round(float(v.x), 1), round(float(v.y), 1), round(float(v.z), 1)]


rows = []
for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    label = actor.get_actor_label()
    if not any(k.lower() in label.lower() for k in KEYWORDS):
        continue
    origin, extent = actor.get_actor_bounds(False)
    rows.append({
        'label': label,
        'class': actor.get_class().get_name(),
        'folder': str(actor.get_folder_path()),
        'location': vec3(actor.get_actor_location()),
        'bounds_origin': vec3(origin),
        'bounds_extent': vec3(extent),
    })

rows.sort(key=lambda r: (r['folder'], r['label']))
report = {'map': TARGET, 'matched_actors': len(rows), 'actors': rows,
          'total_level_actors': len(list(u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()))}
(ROOT / 'Receipts' / 'map_ruins.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('RUIN_SCAN', json.dumps({'matched': len(rows), 'total': report['total_level_actors']}))
for r in rows:
    print('%-44s %-22s %s' % (r['label'], r['class'], r['location']))
