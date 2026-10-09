"""Second-floor clearances and scoped replacement references."""
import copy, json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
BASE='/Game/Dungeons/ReceptionHall20261006/UpperProps20261007'
TARGET_POTS={6:[-20.4,-15.90,4.5],7:[-20.4,15.78,4.5],8:[11.3,-15.88,4.5],9:[11.3,15.90,4.5]}

def revise(cfg):
    cfg=copy.deepcopy(cfg);parts={p['id']:p for p in cfg['parts']}
    for i,target in TARGET_POTS.items():
        old=cfg['pots'][i];p=parts['PlanterPlant'+str(i)]
        p['position_m']=[p['position_m'][j]+target[j]-old[j] for j in range(3)]
        cfg['pots'][i]=target[:]
    # The previous low ground-cover mesh became 4.6 m wide when scaled to
    # 1.2 m high. Use the existing compact plant with its proven root anchor.
    source=parts['PlanterPlant6'];target=parts['PlanterPlant9']
    for key in ('mesh','yaw_deg','scale'):target[key]=copy.deepcopy(source[key])
    target['position_m']=[source['position_m'][j]+TARGET_POTS[9][j]-TARGET_POTS[6][j] for j in range(3)]
    for side in (-1,1):
        parts[f'UpperBench_{side}_3']['position_m'][1]=side*15.55
        for j,y in enumerate((side*4.4,side*11.8)):
            parts[f'OfficePaper_{side}_{j}']['position_m']=[23.03,y-.82,5.276]
    cfg['upper_props_revision']='20261007-wall-placement-and-detailed-bins'
    return cfg

def source_sync():
    parent=ROOT.parent
    path=parent/'Config/layout.json'
    cfg=revise(json.loads(path.read_text('utf8')))
    path.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')
    manifest_path=parent/'manifest.json'
    man=json.loads(manifest_path.read_text('utf8'))
    new=json.loads((ROOT/'geometry.json').read_text('utf8'))['meshes']
    kinds={p['kind'] for p in new}|{'WasteBinTrim'}
    man['meshes']=[p for p in man['meshes'] if p['kind'] not in kinds]+new
    man['upper_props_refinement']=str(ROOT)
    manifest_path.write_text(json.dumps(man,ensure_ascii=False,indent=2),encoding='utf8')
    import runpy
    runpy.run_path(str(parent/'draft.py'),run_name='__main__')

def preserve_source_if_installed(cfg):
    receipt=ROOT/'Receipts/install.json'
    if receipt.exists() and json.loads(receipt.read_text('utf8')).get('stage')=='maps_saved':return revise(cfg)
    return cfg
