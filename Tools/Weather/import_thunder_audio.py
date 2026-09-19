"""Import only the three prepared weather waves; no map or dirty-package save."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME')
source = root/'SourceAssets/Weather/Thunder'
target = '/Game/Weather/Audio'
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for variant in ('I', 'II', 'III'):
    if f'{target}/S_Thunder_{variant}' in dirty:
        raise RuntimeError('Unsaved edits in thunder import target')

saved = []
for variant in ('I', 'II', 'III'):
    name = f'S_Thunder_{variant}'
    task = u.AssetImportTask()
    task.filename = str(source/(name+'.wav'))
    task.destination_path = target
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    wave = u.load_asset(f'{target}/{name}')
    if not isinstance(wave, u.SoundWave):
        raise RuntimeError('Thunder import failed: '+name)
    wave.set_editor_property('volume', 1.0)
    wave.set_editor_property('looping', False)
    wave.set_editor_property('compression_quality', 80)
    # Keep the opening chunk resident; long rolling tails still use streaming.
    wave.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.RETAIN_ON_LOAD)
    if not u.EditorAssetLibrary.save_loaded_asset(wave, False):
        raise RuntimeError('Could not save '+name)
    saved.append(wave.get_path_name())
out = root/'Saved/LightningDiagnosis20260919'
out.mkdir(parents=True, exist_ok=True)
(out/'audio-import.json').write_text(json.dumps(saved, indent=2), encoding='utf-8')
u.log('PREPARED_THUNDER_IMPORTED '+str(saved))
