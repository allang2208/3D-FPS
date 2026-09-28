"""Read-only: report the current PKM reload SoundWave settings before re-import.

Run in-editor via the MCP bridge.  Changes nothing.
"""
import json

import unreal as u

DEST = '/Game/Weapons/PKMLowpoly20260922/ReloadAudio22'
NAMES = ['S_PKM_CoverOpen', 'S_PKM_CoverClose']

rows = []
for name in NAMES:
    path = f'{DEST}/{name}'
    obj = u.load_asset(path)
    row = {'asset': path, 'loaded': obj is not None}
    if obj is not None:
        for prop in ('volume', 'pitch', 'looping', 'duration', 'loading_behavior',
                     'num_channels', 'sample_rate'):
            try:
                row[prop] = str(obj.get_editor_property(prop))
            except Exception as exc:                       # noqa: BLE001
                row[prop] = f'<{exc}>'
        row['path_name'] = obj.get_path_name()
    rows.append(row)

print('PKM_AUDIO_PROBE ' + json.dumps(rows, indent=2))