"""Publish the fitted action and the matching sparse support endpoint together."""
from pathlib import Path
import unreal as u,json,gzip,hashlib
r=Path(__file__).resolve().parent;path='/Game/Weapons/M249/Bipod/DA_M249_SupportGrip';file=Path(u.Paths.project_content_dir())/'Weapons/M249/Bipod/DA_M249_SupportGrip.uasset'
receipt_path=r/'support_receipt.json';prior=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
if u.EditorAssetLibrary.does_asset_exist(path):
    if hashlib.sha256(file.read_bytes()).hexdigest()!=prior.get('sha256'):raise RuntimeError('Unowned or changed support asset: '+path)
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if path in dirty:raise RuntimeError('Unsaved support profile retained')
exec(compile((r/'import.py').read_text(),str(r/'import.py'),'exec'),{'__file__':str(r/'import.py'),'__name__':'__main__'})
profile=u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
if not profile:
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.WeaponGripProfile)
    profile=u.AssetToolsHelpers.get_asset_tools().create_asset('DA_M249_SupportGrip','/Game/Weapons/M249/Bipod',u.WeaponGripProfile,factory)
if not profile.set_shared_clips_from_json(gzip.decompress((r/'support.json.gz').read_bytes()).decode()):raise RuntimeError('Support profile import')
if not u.EditorAssetLibrary.save_loaded_asset(profile,False):raise RuntimeError('Support profile save')
receipt_path.write_text(json.dumps(dict(path=path,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),complete=True),indent=2))
print('M249_BIPOD_AND_SUPPORT_SAVED',flush=True)
