"""Import the dedicated ordinary three-hit swing and save it."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
TARGET='/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing'
recipe=json.loads((P/'provenance.json').read_text(encoding='utf-8'))
if Path(u.Paths.project_dir()).resolve()!=P.parents[2]:raise RuntimeError('Wrong project')
if TARGET in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
    raise RuntimeError('Preserve the unsaved target audio package')
task=u.AssetImportTask()
task.filename=str(P/recipe['output'])
task.destination_path,task.destination_name=TARGET.rsplit('/',1)
task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
sound=u.load_asset(TARGET)
if not isinstance(sound,u.SoundWave):raise RuntimeError('SoundWave import failed')
sound.set_editor_property('volume',1.)
sound.set_editor_property('pitch',1.)
sound.set_editor_property('looping',False)
sound.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
sound.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
previous=u.load_asset('/Game/Items/ProductionTools/GripMotion20260913/S_Harvest_Swing')
if previous:
    for field in ('sound_class_object','attenuation_settings'):
        sound.set_editor_property(field,previous.get_editor_property(field))
u.EditorAssetLibrary.set_metadata_tag(sound,'AudioSourceSHA256',recipe['source_sha256'])
u.EditorAssetLibrary.set_metadata_tag(sound,'AudioSourceAttribution',recipe['attribution'])
u.EditorAssetLibrary.set_metadata_tag(sound,'AudioSourceRecipe',str(P/'provenance.json'))
if not u.EditorLoadingAndSavingUtils.save_packages([sound.get_outermost()],False):raise RuntimeError('SoundWave save failed')
receipt={'saved':True,'asset':sound.get_path_name(),'duration_seconds':recipe['duration_seconds'],
    'routes':['warhammer_normal_slash1','warhammer_normal_slash2','warhammer_normal_slash3'],
    'volume':1.,'pitch':1.,'compression':'PCM','loading':'ForceInline','auditioned':False,'runtime_tested':False}
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_NORMAL_SWING_SAVED '+json.dumps(receipt))
