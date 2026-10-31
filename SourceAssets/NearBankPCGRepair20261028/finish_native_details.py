"""Finish plugin texture sources and manufacture the updated water reflection."""
from pathlib import Path
from datetime import datetime
import unreal as u,json,gc,runpy
R=Path(__file__).resolve().parent;PROJECT=R.parents[1]
plan=json.loads((R/'asset_migration_plan.json').read_text())
prior=json.loads((R/'selected_texture_assets.json').read_text())
done=set(prior['resized_source_to_2048'])|set(prior['retained_unsupported_types'])
done.update(x['package'] for x in json.loads((R/'atlas_tier.json').read_text())['textures'])
finished=[]
for row in plan['files']:
    p=row['package']
    if p in done or '/PivotPainter/' in p:continue
    if not any(s in p for s in ['/Textures/','/Texture/']):continue
    obj=u.load_asset(p)
    if not isinstance(obj,u.Texture2D):continue
    result=u.TextureAssetActionsBlueprintFns.resize_texture_source(obj,2048)
    if result==u.TextureAssetActionsBlueprintReturn.SUCCESS:
        if not u.EditorAssetLibrary.save_loaded_asset(obj,False):raise RuntimeError('Cannot save imported texture '+p)
        finished.append(p)
    del obj;gc.collect();u.SystemLibrary.collect_garbage()
    if len(finished)%8==0:print('PLUGIN_TEXTURES_FINISHED',len(finished),flush=True)
(R/'remaining_textures_saved.json').write_text(json.dumps(dict(stage='saved',textures=finished,pivot_painter_data_preserved=True),indent=2),encoding='utf8')
runpy.run_path(str(PROJECT/'SourceAssets/CyberpunkNearBank20261028/publish_reflection.py'),run_name='__main__')
installed=json.loads((R/'installed.json').read_text());installed.update(water_reflection='updated_for_native_district',saved_at=datetime.now().astimezone().isoformat());(R/'installed.json').write_text(json.dumps(installed,indent=2),encoding='utf8')
total=sum(Path(r['target']).stat().st_size for r in plan['files'])
(R/'final_asset_size.json').write_text(json.dumps(dict(selected_packages=len(plan['files']),source_bytes=plan['copy_bytes'],project_bytes=total,ordinary_texture_source_max=2048,large_atlas_source_max=8192,original_array_and_unsupported_formats_retained=True),indent=2),encoding='utf8')
print('NATIVE_DETAILS_SAVED','selected_asset_bytes',total,flush=True)
