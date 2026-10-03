"""Keep all accepted workshop states and route just the three corrected assets."""
import copy,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent
BASE='/Game/Dungeons/StationWorkshop20261003/RefineV3'
def apply(rules):
    rules=copy.deepcopy(rules)
    for p in rules['fixed_parts']:
        if p['mesh'].split('.')[0].endswith('/SM_SW_Roof'):
            p['mesh']=BASE+'/Meshes/SM_SW_Roof';p['materials']=[]
    for variant in rules['variants']:
        for p in variant['parts']:
            if p['mesh'].split('.')[0].endswith('/SM_WBK_Fab_BenchRetained'):
                p['mesh']=BASE+'/Meshes/SM_SW_BenchRetained'
    remap=rules.get('geometry_asset_remap',{})
    remap['/Game/Dungeons/TransitStation20260928/Meshes/SM_Station_Railings']=BASE+'/Meshes/SM_Station_Railings'
    rules.update(revision=3,geometry_asset_remap=remap,
        ceiling_surface='Single planar slab; matte concrete without displacement or coarse normal',
        bench_clearance='Retained ratchet moved 14 cm from parts-tray rim; tray and loose contents retained',
        recovery_railing='Posts inside stair width, centred on actual tread tops; shared 110 cm landing handrail junction')
    fitted=PARENT/'RefineV4';receipt=fitted/'Receipts/install.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='maps_saved':
        import runpy
        rules=runpy.run_path(str(fitted/'Scripts/fit_rules.py'))['apply'](rules)
    return rules
if __name__=='__main__':
    (ROOT/'Config').mkdir(parents=True,exist_ok=True)
    source=json.loads((PARENT/'Config/workshop.json').read_text('utf-8-sig'))
    (ROOT/'Config/workshop.json').write_text(json.dumps(apply(source),ensure_ascii=False,indent=2),encoding='utf8')
