"""Import the dedicated JiLei electromagnetic loop, preserving GuanLei audio."""
from pathlib import Path
import json
import unreal as u
P=Path(__file__).resolve().parent
D='/Game/Weapons/ThunderGodHammer20261028/JiLeiChargeAudioV1'
recipe=json.loads((P/'audio_manifest.json').read_text(encoding='utf-8'))
file=P/recipe['file'];name=file.stem
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if D+'/'+name in dirty:raise RuntimeError('Charge loop has unsaved editor edits')
task=u.AssetImportTask();task.filename=str(file);task.destination_path=D;task.destination_name=name
task.automated=True;task.replace_existing=False;task.save=False
wave=u.load_asset(D+'/'+name)
if not wave:
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);wave=u.load_asset(D+'/'+name)
if not isinstance(wave,u.SoundWave):raise RuntimeError('Charge sound import failed')
wave.set_editor_property('looping',True)
wave.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
u.EditorAssetLibrary.set_metadata_tag(wave,'AudioSourceAttribution',recipe['source'])
u.EditorAssetLibrary.set_metadata_tag(wave,'AudioSourceSHA256',recipe['sha256'])
if not u.EditorLoadingAndSavingUtils.save_packages([wave.get_outermost()],False):raise RuntimeError('Charge sound save failed')
(P/'import_receipt.json').write_text(json.dumps({'saved':True,'asset':wave.get_path_name(),
 'source_sha256':recipe['sha256'],'gameplay_tested':False},indent=2),encoding='utf-8')
print('JI_LEI_ELECTROMAGNETIC_LOOP_SAVED',wave.get_path_name())
