"""Retain more texels for the sample's multi-tile atlases than ordinary tiling maps."""
from pathlib import Path
import json,re,shutil
R=Path(__file__).resolve().parent;plan=json.loads((R/'asset_migration_plan.json').read_text())
log=(R/'native-publish-01.log').read_text(encoding='utf8',errors='replace')
unsupported=set(json.loads((R/'selected_texture_assets.json').read_text())['retained_unsupported_types'])
atlas_names={n:(int(w),int(h)) for n,w,h in re.findall(r'Texture \(([^)]+)\) Resizing to <= 2048 Source Size=(\d+)x(\d+)',log) if max(int(w),int(h))>8192}
rows=[]
for f in plan['files']:
    if f['package'] in unsupported:continue
    name=f['package'].rsplit('/',1)[-1]
    if name not in atlas_names:continue
    target=Path(f['target']).resolve();source=Path(f['source']).resolve()
    if not (target.is_relative_to(Path('F:/FPSGAMEData/Content').resolve()) or target.is_relative_to(Path('D:/FPS3D/FPSGAME/Plugins').resolve())):raise RuntimeError('Outside owned imported content '+str(target))
    if not target.is_file():raise RuntimeError('Imported texture disappeared '+str(target))
    shutil.copy2(source,target)
    rows.append(dict(package=f['package'],original_dimensions=atlas_names[name],max_dimension=8192))
(R/'atlas_tier.json').write_text(json.dumps(dict(stage='sources_restored_for_atlas_production',textures=rows),indent=2),encoding='utf8')
print('ATLAS_SOURCE_TIER_PREPARED',len(rows),flush=True)
