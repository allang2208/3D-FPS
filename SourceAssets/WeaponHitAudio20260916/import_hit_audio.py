"""Import the two user-supplied weapon hit sounds as SoundWaves.

Sources (user, 2026-09-16): D:/FPS3D/资产/音效/quickhit.mp3 and gunhit.mp3,
converted to 44.1 kHz stereo 16-bit PCM WAV in this folder. Melee weapons point
their item hit_sound at S_MeleeHit_Quick; firearm hit confirmation uses S_GunHit.
"""
import json
from pathlib import Path

import unreal as u

P = Path(__file__).parent
DEST = '/Game/Audio/WeaponHit20260916'
tools = u.AssetToolsHelpers.get_asset_tools()
receipt = []
for name in ('S_MeleeHit_Quick', 'S_GunHit'):
    task = u.AssetImportTask()
    task.filename = str(P / (name + '.wav'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    tools.import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: ' + name)
    sound = u.load_asset(task.imported_object_paths[0])
    # Short one-shots are loaded with the asset so the first hit never pops.
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    if not u.EditorAssetLibrary.save_loaded_asset(sound):
        raise RuntimeError('Sound save failed: ' + name)
    receipt.append({'source': task.filename, 'asset': sound.get_path_name(),
                    'seconds': sound.get_editor_property('duration')})
(P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('WEAPON_HIT_AUDIO_IMPORT_COMPLETE')
