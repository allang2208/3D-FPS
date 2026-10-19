"""Create the selected 12K one-shot without replacing any shared shotgun sound."""
from pathlib import Path
import json,hashlib
import unreal as u
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KAudio20261018')
recipe=json.loads((O/'provenance.json').read_text(encoding='utf8'))
source=O/recipe['output'];dest,name=recipe['asset'].rsplit('/',1);E=u.EditorAssetLibrary
if hashlib.sha256(source.read_bytes()).hexdigest()!=recipe['source_sha256']:raise RuntimeError('Source changed before import')
if E.does_asset_exist(recipe['asset']):raise RuntimeError('Preserve existing target '+recipe['asset'])
# Keep the current 12K playback settings while changing only its source recording.
previous=u.load_asset('/Game/Weapons/Super90/GameDevAudio20261007/S_Super90_Fire')
suppressed=u.load_asset(recipe['suppressed_asset'])
if not previous or not suppressed:raise RuntimeError('Required existing shotgun sound is unavailable')
keys=('volume','pitch','sound_class_object','attenuation_settings')
settings={k:previous.get_editor_property(k) for k in keys}
t=u.AssetImportTask();t.filename=str(source);t.destination_path=dest;t.destination_name=name;t.automated=True;t.replace_existing=False;t.save=False;t.factory=u.SoundFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);sound=u.load_asset(recipe['asset'])
if not t.imported_object_paths or not isinstance(sound,u.SoundWave):raise RuntimeError('12K SoundWave import failed')
for k,v in settings.items():sound.set_editor_property(k,v)
sound.set_editor_property('looping',False);sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE);sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
E.set_metadata_tag(sound,'SaigaAudioSource',recipe['source']);E.set_metadata_tag(sound,'AudioSourceSHA256',recipe['source_sha256']);E.set_metadata_tag(sound,'AudioSourceRecipe',str(O/'provenance.json'));E.set_metadata_tag(sound,'AudioSourceRights',recipe['rights'])
if not E.save_loaded_asset(sound,False):raise RuntimeError('12K SoundWave save failed')
receipt={'complete':True,'saved':sound.get_path_name(),'normal_source_sha256':recipe['source_sha256'],'suppressed_reused_unchanged':suppressed.get_path_name(),'volume':settings['volume'],'pitch':settings['pitch'],'sound_class':settings['sound_class_object'].get_path_name() if settings['sound_class_object'] else None,'attenuation':settings['attenuation_settings'].get_path_name() if settings['attenuation_settings'] else None,'compression':'PCM','loading':'ForceInline','auditioned':False,'runtime_tested':False}
(O/'Receipts/import.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8');print('SAIGA12K_GAMEDEV_AUDIO_SAVED '+sound.get_path_name())
