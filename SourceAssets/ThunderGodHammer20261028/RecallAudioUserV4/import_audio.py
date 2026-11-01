"""Replace air loop and catch independently, retaining both existing routes."""
from pathlib import Path
from datetime import datetime, timezone
import json
import unreal as u

P=Path(__file__).resolve().parent
if Path(u.Paths.project_dir()).resolve()!=P.parents[2]:
    raise RuntimeError('Wrong project')
recipe=json.loads((P/'audio_manifest.json').read_text(encoding='utf-8'))
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
paths=[recipe['runtime_destination']+'/'+Path(row['file']).stem for row in recipe['assets']]
if any(path in dirty for path in paths):
    raise RuntimeError('Preserving unsaved GuanLei audio assets')
saved=[]
for row,dest in zip(recipe['assets'],paths):
    wave=u.load_asset(dest)
    if not isinstance(wave,u.SoundWave):
        raise RuntimeError('Existing audio missing: '+dest)
    properties={key:wave.get_editor_property(key) for key in
                ('volume','pitch','sound_class_object','attenuation_settings')}
    task=u.AssetImportTask()
    task.filename=str(P/row['file'])
    task.destination_path,task.destination_name=dest.rsplit('/',1)
    task.automated=True;task.replace_existing=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    wave=u.load_asset(dest)
    for key,value in properties.items():
        wave.set_editor_property(key,value)
    wave.set_editor_property('looping',dest.endswith('Loop'))
    wave.set_editor_property('loading_behavior',u.SoundWaveLoadingBehavior.FORCE_INLINE)
    wave.set_sound_asset_compression_type(u.SoundAssetCompressionType.PCM)
    for key,value in {'AudioSourceAttribution':recipe['rights'],
                      'AudioSourceRecipe':str(P/'audio_manifest.json'),
                      'AudioSourceSHA256':row['sha256'],'AudioRevision':recipe['revision']}.items():
        u.EditorAssetLibrary.set_metadata_tag(wave,key,value)
    if not u.EditorLoadingAndSavingUtils.save_packages([wave.get_outermost()],False):
        raise RuntimeError('Failed saving '+dest)
    saved.append({'asset':wave.get_path_name(),'source_sha256':row['sha256']})
receipt={'saved':True,'revision':recipe['revision'],'assets':saved,'metal_loop_modified':False,
         'independent_triggers_preserved':True,'gameplay_tested':False,
         'finished_utc':datetime.now(timezone.utc).isoformat()}
(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_AUDIO_USER_V4_SAVED '+json.dumps(receipt,ensure_ascii=False))
