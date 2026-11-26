import json,hashlib,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3';C=R/'CuffRepairR1'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
for folder in ['Inputs','Read','Authored','Simulation','Logs','Before','Review']:(C/folder).mkdir(exist_ok=True)
cfg=read(P/'Content/ColdSteelData/modular_outfits.json');(C/'Inputs/modular_outfits.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
for rig in ['Jason','Kaitlin']:shutil.copy2(R/'Inputs'/f'Body_{rig}.json',C/'Inputs'/f'Body_{rig}.json')
rows=[]
for rig in ['M4',*[r['rig'] for r in read(R/'fp-authored.json')['rows'] if r['rig']!='M4']]:
    profiles=[p for p in cfg['profiles'].values() if p.get('rig_profile')==rig];skins=list(dict.fromkeys(p.get('native_bare_skin',p.get('base')) for p in profiles if p.get('native_bare_skin') or p.get('base')));skins.sort(key=lambda s:(0 if 'WristCoverage' in s else 1,0 if '3cced8ec73' in s else 1))
    if skins:rows.append(dict(key='Native_'+rig,rig=rig,role='native',path=skins[0]))
for item,key in [('ue_st6_sleeves','PreviousSleeve_M4'),('ue_modern_tactical_gloves','Glove_M4')]:rows.append(dict(key=key,rig='M4',role=key,path=cfg['items'][item]['rig_meshes']['M4']))
(C/'capture-plan.json').write_text(json.dumps(dict(rows=rows),indent=2),encoding='utf-8')
for rig in ['M4','Body']:shutil.copy2(R/'Authored'/f'shirt_fp_{rig}.json',C/'Before'/f'shirt_fp_{rig}.json')
evidence={}
import numpy as np
for file in (R/'Simulation').glob('*.npz'):
    if not file.stem.startswith(('FP_','Shirt_')):continue
    d=np.load(file);pinned=d['pins']>.9999;evidence[file.stem]=dict(pinned_vertices=int(pinned.sum()),max_anchor_drift_cm=float(np.linalg.norm(d['after'][pinned]-d['before'][pinned],axis=1).max()),max_offset_from_rest_key_cm=float(np.linalg.norm(d['after'][pinned]-d['rest'][pinned],axis=1).max()))
(C/'Review/anchor-regression-before.json').write_text(json.dumps(evidence,indent=2),encoding='utf-8');print('CUFF_REPAIR_INPUTS',len(rows))
