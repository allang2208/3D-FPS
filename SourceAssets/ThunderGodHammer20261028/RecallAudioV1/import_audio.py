"""Import/save only GuanLei recall sounds and their dedicated attenuation assets."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).resolve().parent
DEST='/Game/Weapons/ThunderGodHammer20261028/RecallAudioV1'
if Path(u.Paths.project_dir()).resolve()!=P.parents[2]:
    raise RuntimeError('Wrong project')
recipe=json.loads((P/'audio_manifest.json').read_text(encoding='utf-8'))
tools=u.AssetToolsHelpers.get_asset_tools()
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
names=[Path(row['file']).stem for row in recipe['assets']]+['SA_GuanLei_RecallFlight','SA_GuanLei_RecallCatch']
if any(DEST+'/'+name in dirty for name in names):
    raise RuntimeError('Preserving unsaved recall audio assets')
saved=[]

def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Failed to save '+asset.get_path_name())
    saved.append(asset.get_path_name())

def attenuation(name,inner,falloff):
    asset=u.load_asset(DEST+'/'+name)
    if not asset:
        asset=tools.create_asset(name,DEST,u.SoundAttenuation,u.SoundAttenuationFactory())
    settings=asset.get_editor_property('attenuation')
    settings.set_editor_property('attenuation_shape_extents',u.Vector(inner,0,0))
    settings.set_editor_property('falloff_distance',falloff)
    settings.set_editor_property('spatialize',True)
    settings.set_editor_property('distance_algorithm',u.AttenuationDistanceModel.LINEAR)
    asset.set_editor_property('attenuation',settings)
    save(asset)
    return asset

flight=attenuation('SA_GuanLei_RecallFlight',120.,3200.)
catch=attenuation('SA_GuanLei_RecallCatch',160.,1900.)
baseline=u.load_asset('/Game/Weapons/SteelWarhammer20261014/NormalSwingAudioV1/S_Warhammer_NormalSwing')
for row in recipe['assets']:
    path=P/row['file']
    task=u.AssetImportTask()
    task.filename=str(path)
    task.destination_path=DEST;task.destination_name=path.stem
    task.automated=True;task.replace_existing=True;task.save=False
    tools.import_asset_tasks([task])
    wave=u.load_asset(DEST+'/'+path.stem)
    if not isinstance(wave,u.SoundWave):
        raise RuntimeError('SoundWave import failed: '+path.stem)
    loop=path.stem.endswith('Loop')
    wave.set_editor_property('looping',loop)
    wave.set_editor_property('volume',1.)
    wave.set_editor_property('pitch',1.)
    wave.set_editor_property('attenuation_settings',flight if loop else catch)
    wave.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
    wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    if baseline:
        wave.set_editor_property('sound_class_object',baseline.get_editor_property('sound_class_object'))
    u.EditorAssetLibrary.set_metadata_tag(wave,'AudioSourceAttribution',recipe['rights'])
    u.EditorAssetLibrary.set_metadata_tag(wave,'AudioSourceRecipe',str(P/'audio_manifest.json'))
    u.EditorAssetLibrary.set_metadata_tag(wave,'AudioSourceSHA256',row['sha256'])
    save(wave)
receipt={'saved':True,'assets':saved,'routes':['recall_metal_loop','recall_rotating_air_loop','actual_catch_contact'],
         'audition':'Audition/GuanLei_Recall_Full.wav','gameplay_tested':False}
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_RECALL_AUDIO_SAVED '+json.dumps(receipt,ensure_ascii=False))
