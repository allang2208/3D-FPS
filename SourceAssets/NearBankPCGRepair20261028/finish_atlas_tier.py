from pathlib import Path
import json,gc,unreal as u
R=Path(__file__).resolve().parent
d=json.loads((R/'atlas_tier.json').read_text())
for i,row in enumerate(d['textures']):
    texture=u.load_asset(row['package'])
    if not texture:raise RuntimeError('Cannot load atlas '+row['package'])
    result=u.TextureAssetActionsBlueprintFns.resize_texture_source(texture,row['max_dimension'])
    if result==u.TextureAssetActionsBlueprintReturn.ERROR:raise RuntimeError('Cannot author atlas resolution '+row['package'])
    if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Cannot save atlas '+row['package'])
    del texture;gc.collect();u.SystemLibrary.collect_garbage()
    print('ATLAS_TEXTURE_SAVED',i+1,len(d['textures']),row['package'],flush=True)
d['stage']='atlas_assets_saved';(R/'atlas_tier.json').write_text(json.dumps(d,indent=2),encoding='utf8')
p=json.loads((R/'asset_migration_plan.json').read_text());total=sum(Path(r['target']).stat().st_size for r in p['files'])
(R/'final_asset_size.json').write_text(json.dumps(dict(selected_packages=len(p['files']),source_bytes=p['copy_bytes'],project_bytes=total,ordinary_texture_source_max=2048,large_atlas_source_max=8192),indent=2),encoding='utf8')
print('ATLAS_TIER_FINISHED','selected_asset_bytes',total,flush=True)
