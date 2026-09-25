"""In-editor (MCP bridge, read-only): channel counts and settings of the DW715 cues.

The rebuilt WAVs imported as stereo; this checks what the untouched cues and the
Fire asset use, so a mismatch can be corrected rather than left to chance.
"""
import json

import unreal as u

DEST = '/Game/Weapons/DanWesson715/RecordedAudio20260914'
NAMES = ['S_DW715_Fire_Recorded', 'S_DW715_Loader_Open', 'S_DW715_Loader_Eject',
         'S_DW715_Loader_Retrieve', 'S_DW715_Loader_Insert', 'S_DW715_Loader_Release',
         'S_DW715_Loader_Withdraw', 'S_DW715_Loader_Close']

rows = []
for name in NAMES:
    obj = u.load_asset('%s/%s' % (DEST, name))
    if obj is None:
        rows.append({'asset': name, 'loaded': False})
        continue
    rows.append({'asset': name,
                 'num_channels': obj.get_editor_property('num_channels'),
                 'sample_rate': obj.get_editor_property('sample_rate'),
                 'duration': round(float(obj.get_editor_property('duration')), 4),
                 'volume': obj.get_editor_property('volume'),
                 'pitch': obj.get_editor_property('pitch'),
                 'looping': obj.get_editor_property('looping'),
                 'loading_behavior': str(obj.get_editor_property('loading_behavior'))})
print('DW715_CHANNEL_AUDIT ' + json.dumps(rows, indent=2))