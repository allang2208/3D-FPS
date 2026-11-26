"""Capture-plan ownership for TS01 combat shirt and its native fit variants."""
import json,hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1'
for name in ['Inputs','Authored','Models','Exports','Logs','Review']:(R/name).mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
c=read(P/'Content/ColdSteelData/modular_outfits.json');b=read(P/'Content/ColdSteelData/player_body.json')
refs={}
def collect(value):
    if isinstance(value,dict):
        for k,v in value.items():
            if k in ('rig_meshes','owner_body_meshes'):
                for rig,path in v.items():refs[path]=dict(rig=rig,source=path,file=hashlib.sha256(path.encode()).hexdigest()[:16]+'.json')
            elif k.startswith('pants_') and isinstance(v,dict):collect(v)
            elif isinstance(v,dict):collect(v)
for variant,rig in [(c,'Jason'),(c['body_variants']['kaitlin'],'Kaitlin')]:collect(variant['items']['ue_st6_sleeves'])
for rig,bc,cc in [('Jason',b,c),('Kaitlin',b['body_variants']['kaitlin'],c['body_variants']['kaitlin'])]:
    path=cc['profiles'][bc['body_mesh']]['native_bare_skin'];refs[path]=dict(rig=rig,source=path,file='Body_'+rig+'.json',role='body')
for name in ['modular_outfits.json','player_body.json','items.json']:(R/'Inputs'/name).write_bytes((P/'Content/ColdSteelData'/name).read_bytes())
(R/'plan.json').write_text(json.dumps(dict(rows=list(refs.values()),item='ue_modern_kevlar_vest',source_item='ue_st6_sleeves',design='../Design/TS01_CombatShirt_EarthBrown_R1.png'),indent=2),encoding='utf-8')
print('TS01_SHIRT_PLANNED',len(refs))
