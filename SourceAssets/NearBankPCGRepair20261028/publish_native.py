"""Finish selected imported assets and install the completed native district."""
from pathlib import Path
import unreal as u,json,runpy,gc
R=Path(__file__).resolve().parent
plan=json.loads((R/'asset_migration_plan.json').read_text())
ar=u.AssetRegistryHelpers.get_asset_registry();ar.search_all_assets(True)
resized=[];retained=[]
for index,row in enumerate(plan['files']):
    data=ar.get_asset_by_object_path(row['package']+'.'+row['package'].rsplit('/',1)[-1])
    if data.is_valid() and not str(data.asset_class_path.asset_name).startswith('Texture'):continue
    texture=u.load_asset(row['package'])
    if not texture:raise RuntimeError('Cannot load new texture '+row['package'])
    if not isinstance(texture,u.Texture):continue
    if '/PivotPainter/' in row['package']:continue
    # Preserve full sample originals and all already installed assets. Only the
    # newly copied source images are reduced for this exterior distance tier.
    result=u.TextureAssetActionsBlueprintFns.resize_texture_source(texture,2048)
    if result==u.TextureAssetActionsBlueprintReturn.SUCCESS:
        if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Texture save failed '+row['package'])
        resized.append(row['package'])
    elif result==u.TextureAssetActionsBlueprintReturn.ERROR:retained.append(row['package'])
    if index%12==0:
        del texture;gc.collect();u.SystemLibrary.collect_garbage()
        print('SELECTED_TEXTURES_FINISHED',index,len(resized),flush=True)
(R/'selected_texture_assets.json').write_text(json.dumps(dict(resized_source_to_2048=resized,retained_unsupported_types=retained,original_sample_changed=False,existing_assets_changed=False),indent=2),encoding='utf8')
print('SELECTED_TEXTURE_PRODUCTION_COMPLETE',len(resized),len(retained),flush=True)
runpy.run_path(str(R/'build_publish_assets.py'),run_name='__main__')
runpy.run_path(str(R/'install_level.py'),run_name='__main__')
total=sum(Path(r['target']).stat().st_size for r in plan['files'])
(R/'final_asset_size.json').write_text(json.dumps(dict(selected_packages=len(plan['files']),source_bytes=plan['copy_bytes'],project_bytes=total),indent=2),encoding='utf8')
print('NATIVE_PUBLISH_COMPLETE','selected_asset_bytes',total,flush=True)
