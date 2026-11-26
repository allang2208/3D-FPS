"""Freeze live TS01 routes and the delivered R2 source inputs for cloth authoring."""
import json,hashlib,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/ModernTacticalSet20261113';R=S/'CombatShirtR3';B=S/'CombatShirtR2'
for name in ['Inputs','Authored','Simulation','Models','Exports','Textures','Bakes','Icons','Logs','Review','Sources']:(R/name).mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
for name in ['modular_outfits','player_body','items']:
    target=R/'Inputs'/(name+'.json')
    if not target.exists():shutil.copyfile(P/'Content/ColdSteelData'/(name+'.json'),target)
baseline=read(B/'authored.json');saved=read(B/'saved.json')
records=[]
for row in baseline['rows']:
    sha=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest()
    if saved['wear'][row['asset']]['sha256']!=sha:raise RuntimeError('R2 source no longer matches saved asset: '+row['file'])
    records.append(dict(**row,sha256=sha))
(R/'Inputs/baseline.json').write_text(json.dumps(dict(rows=records),indent=2),encoding='utf-8')
for rig in ['Jason','Kaitlin']:
    shutil.copyfile(B/'Inputs'/f'Body_{rig}.json',R/'Inputs'/f'Body_{rig}.json')
    d=read(R/'Inputs'/f'Body_{rig}.json');bones={b['name']:b['position'] for b in d['bones']}
    print(rig,{n:bones.get(n) for n in ['pelvis','spine_04','spine_05','clavicle_l','clavicle_r','neck_01','neck_02','head','upperarm_l','lowerarm_l','hand_l']})
print('TS01_R3_INPUTS_FROZEN',len(records))
