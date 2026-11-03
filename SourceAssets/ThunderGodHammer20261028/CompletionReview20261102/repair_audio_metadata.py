from pathlib import Path
import json, shutil, unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
manifest=json.loads((P.parent/'JiLeiRecordedCurrentV2/audio_manifest.json').read_text(encoding='utf-8'))
path='/Game/Weapons/ThunderGodHammer20261028/JiLeiRecordedCurrentV2/MS_JiLei_CurrentRandom'
if any(p.get_path_name()==path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserving unsaved audio asset')
asset=u.load_asset(path)
before=u.EditorAssetLibrary.get_metadata_tag(asset,'AudioSourceSHA256')
if before and before!=manifest['source_sha256']:raise RuntimeError('Unexpected audio attribution: '+before)
backup=P/'AudioMetadataBefore';backup.mkdir(exist_ok=True)
for f in (R/'Content/Weapons/ThunderGodHammer20261028/JiLeiRecordedCurrentV2').glob('MS_JiLei_CurrentRandom.*'):
    if not (backup/f.name).exists():shutil.copy2(f,backup/f.name)
asset.modify()
u.EditorAssetLibrary.set_metadata_tag(asset,'AudioSourceSHA256',manifest['source_sha256'])
u.EditorAssetLibrary.set_metadata_tag(asset,'AuthoringRevision',manifest['revision'])
if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Metadata save failed')
(P/'audio_metadata_receipt.json').write_text(json.dumps(dict(before=before,after=u.EditorAssetLibrary.get_metadata_tag(asset,'AudioSourceSHA256'),graph_modified=False,source_sha256=manifest['source_sha256']),indent=2),encoding='utf-8')
print('THOR_AUDIO_ATTRIBUTION_SAVED',flush=True)
