"""Reuse tooling while preserving the accepted V2 runtime identity and finish."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];old=P/'SourceAssets/Super90DuckbillV2_20261016'
(O/'package_runtime.py').write_text((old/'package_runtime.py').read_text(encoding='utf-8'),encoding='utf-8')
reference=(old/'render_icon_reference.py').read_text(encoding='utf-8')
reference=reference.replace('Super90DuckbillV2_20261016/ShotgunDuckbillV2_Editable.blend',
    'Super90DuckbillClosedSides20261016/ShotgunDuckbill_ClosedSides_Editable.blend')
(O/'render_icon_reference.py').write_text(reference,encoding='utf-8')
install=(old/'install_assets.py').read_text(encoding='utf-8')
start=install.index("master=load(");end=install.index("flag='Interchange.")
bindings="""bindings={name:load(D+'/Materials/MI_'+name) for name in (
    'DuckbillV2_Graphite','DuckbillV2_Seat','DuckbillV2_Recess','DuckbillV2_Edge','DuckbillV2_Fastener')}
before=O/'Before';before.mkdir(exist_ok=True)
for package in (D+'/Meshes/SM_ShotgunDuckbillV2',D+'/UI/T_ShotgunDuckbill_Icon',
    '/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_shotgun_duckbill'):
    source=P/'Content'/(package.removeprefix('/Game/')+'.uasset')
    target=before/source.name
    if source.exists() and not target.exists():shutil.copy2(source,target)
active_icon=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/muzzle_shotgun_duckbill.png'
if active_icon.exists() and not (before/active_icon.name).exists():shutil.copy2(active_icon,before/active_icon.name)
"""
install=install[:start]+bindings+install[end:]
install=install.replace("'SHOTGUN_DUCKBILL_ASSETS_SAVED'","'DUCKBILL_CLOSED_SIDES_ASSETS_SAVED'")
(O/'install_assets.py').write_text(install,encoding='utf-8')
runner=(old/'install.ps1').read_text(encoding='utf-8-sig').replace('Super90DuckbillV2_20261016','Super90DuckbillClosedSides20261016')
(O/'install.ps1').write_text(runner,encoding='utf-8-sig')
print('CLOSED_SIDES_PIPELINE_PREPARED')
