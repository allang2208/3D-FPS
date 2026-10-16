"""Reuse import/export tools only. V2 geometry is independently authored."""
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];old=P/'SourceAssets/Super90Duckbill20261016'
for script in ('package_runtime.py','install_assets.py','render_icon_reference.py','integrate_catalog.py'):
    value=(old/script).read_text(encoding='utf-8')
    value=value.replace('Super90Duckbill20261016','Super90DuckbillV2_20261016')
    value=value.replace('Duckbill20261016','DuckbillV2_20261016')
    value=value.replace('ShotgunDuckbill01','ShotgunDuckbillV2')
    if script=='install_assets.py':
        value=value.replace("('Muzzle',9.2),('AimGuide',10.2)","('Muzzle',10.7),('AimGuide',11.7)")
        value=value.replace("'muzzle_socket_cm':[9.2,0,0]","'muzzle_socket_cm':[10.7,0,0]")
    if script=='integrate_catalog.py':
        value=value.replace('短扁的深灰钢制壳体向前横向展开，宽口上下收窄，边缘带有细窄倒角。',
            '封闭侧壁将上下鸭舌连接成扁宽壳体，前方保留横向开口；收腰肩部、浅槽与刻槽安装环采用分区金属表面。')
    (O/script).write_text(value,encoding='utf-8')
for script in ('install.ps1','build.ps1'):
    value=(old/script).read_text(encoding='utf-8-sig').replace('Super90Duckbill20261016','Super90DuckbillV2_20261016')
    (O/script).write_text(value,encoding='utf-8-sig')
print('DUCKBILL_V2_PIPELINE_PREPARED')
