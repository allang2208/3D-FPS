"""导入手枪快速近战的**起手/释放**音（用户 2026-09-18 指定 quickhit2.mp3）。

口径沿用 SourceAssets/WeaponHitAudio20260916：44.1 kHz / 立体声 / 16-bit PCM WAV →
SoundWave，短促单次音设 LoadingBehavior=FORCE_INLINE（首击不 pop），并写回执。
"""
import json
from pathlib import Path

import unreal as u

P = Path(__file__).parent
DEST = '/Game/Audio/QuickCombat20260918'
NAME = 'S_QuickCombatSwing'

tools = u.AssetToolsHelpers.get_asset_tools()
task = u.AssetImportTask()
task.filename = str(P / (NAME + '.wav'))
task.destination_path = DEST
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = True
tools.import_asset_tasks([task])
if not task.imported_object_paths:
    raise RuntimeError('Import failed: ' + NAME)
sound = u.load_asset(task.imported_object_paths[0])
sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
if not u.EditorAssetLibrary.save_loaded_asset(sound):
    raise RuntimeError('Sound save failed: ' + NAME)
receipt = [{'source': task.filename, 'asset': sound.get_path_name(),
            'seconds': sound.get_editor_property('duration'),
            'loading_behavior': 'FORCE_INLINE',
            'slot': 'quick-combat release/swing cue'}]
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('QUICK_COMBAT_SWING_AUDIO_IMPORTED %s %.4fs' % (sound.get_path_name(),
                                                      sound.get_editor_property('duration')))
u.log('QUICK_COMBAT_SWING_AUDIO_IMPORT_COMPLETE')
