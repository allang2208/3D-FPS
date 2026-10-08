"""Save the owned Bagua material and revised Niagara graph, without playback."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
PROJECT=Path(u.Paths.project_dir())
ASSETS=[
    'Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/SoftGroundV3/M_ZhenmoSoftGround',
    'Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/M_ZhenmoGoldMote',
    'Weapons/XuanChiZhenYue20261004/ZhenmoRune20261005/Particles/NS_ZhenmoRisingGold']
for name in ASSETS:
    src=PROJECT/'Content'/(name+'.uasset')
    dst=OUT/'Before'/(Path(name).name+'.uasset')
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
runpy.run_path(str(ROOT/'SoftGroundV3/save_visuals.py'),run_name='__main__')
(OUT/'asset_receipt.json').write_text(json.dumps({
    'complete':True,'revision':'GroundVisibility20261007',
    'saved_assets':['/Game/'+name for name in ASSETS],
    'runtime_tested':False,'visual_tested':False,
    'niagara_fresh_compile_pending':True},ensure_ascii=False,indent=2),encoding='utf-8')
print('ZHENMO_VISIBILITY_ASSETS_SAVED',flush=True)
