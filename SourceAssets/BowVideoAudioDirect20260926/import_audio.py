"""Create and save the two direct-video SoundWaves, without playback."""
from pathlib import Path
import json
import unreal as u

HERE = Path('D:/FPS3D/FPSGAME/SourceAssets/BowVideoAudioDirect20260926')
DEST = '/Game/Weapons/DarkBow20260925/AudioVideoDirect20260926'
records = json.loads((HERE/'audio-manifest.json').read_text(encoding='utf-8'))['outputs']
receipt = []
for record in records:
    task = u.AssetImportTask()
    task.filename = str(HERE/'Wav'/(record['asset']+'.wav'))
    task.destination_path = DEST
    task.destination_name = record['asset']
    task.automated = True
    task.replace_existing = False
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import failed: '+task.filename)
    sound = u.load_asset(task.imported_object_paths[0])
    sound.set_editor_property('volume', 1.)
    sound.set_editor_property('pitch', 1.)
    sound.set_editor_property('looping', False)
    sound.set_editor_property('compression_quality', 100)
    sound.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.FORCE_INLINE)
    if not u.EditorAssetLibrary.save_loaded_asset(sound, False):
        raise RuntimeError('Save failed: '+record['asset'])
    receipt.append({'asset': sound.get_path_name(), 'seconds': record['seconds'],
                    'channels': record['channels'], 'saved': True})
    (HERE/'import-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('DARKBOW_VIDEO_DIRECT_IMPORTED '+json.dumps(receipt))
