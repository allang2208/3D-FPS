"""Import and save only the licensed exhaustion panting asset, without opening a level."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME')
source = root / 'SourceAssets/PlayerExhaustion20261014'
target = '/Game/Player/Exhaustion'
name = 'S_ExhaustionPanting'
level = u.get_editor_subsystem(u.LevelEditorSubsystem)
if level and level.is_in_play_in_editor():
    raise RuntimeError('Preserve running PIE; no exhaustion audio import performed')
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if f'{target}/{name}' in dirty:
    raise RuntimeError('Unsaved exhaustion audio edits')
task = u.AssetImportTask()
task.filename = str(source / f'{name}.wav')
task.destination_path = target
task.destination_name = name
task.automated = True
task.replace_existing = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
wave = u.load_asset(f'{target}/{name}')
if not isinstance(wave, u.SoundWave):
    raise RuntimeError('Exhaustion audio import failed')
wave.set_editor_property('looping', True)
wave.set_editor_property('volume', 1.0)
wave.set_editor_property('compression_quality', 80)
wave.set_editor_property('loading_behavior', u.SoundWaveLoadingBehavior.RETAIN_ON_LOAD)
if not u.EditorAssetLibrary.save_loaded_asset(wave, False):
    raise RuntimeError('Exhaustion audio save failed')
(source / 'loop-import-receipt.json').write_text(json.dumps({'asset': wave.get_path_name(), 'saved': True, 'looping': True}, indent=2), encoding='utf-8')
u.log('EXHAUSTION_LOOP_AUDIO_SAVED ' + wave.get_path_name())
