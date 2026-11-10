import json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME');OUT=Path(__file__).resolve().parent
defs={}
for name in ['items.json','production_tools.json','bows.json','staffs.json']:
 defs.update(json.loads((ROOT/'Content/ColdSteelData'/name).read_text(encoding='utf-8-sig')))
cases=[dict(id=k,weapon=k,name=v.get('name'),family=v.get('weaponType',v.get('tool_kind')))
 for k,v in defs.items() if (str(v.get('category','')).startswith('weapon') or v.get('category')=='tool')
 and k not in ['ue_steel_warhammer','ue_runebound_warhammer']]
cases.sort(key=lambda c:(c['family'] in ['rifle','pistol','sniper','machineGun','shotgun'],c['family'] or '',c['id']))
pairs=[('dual_kukri','ue_kukri','ue_kukri'),('dual_hatchet','ue_tactical_hatchet','ue_tactical_hatchet'),
 ('dual_pistol','ue_m1911','ue_g18'),('pistol_kukri','ue_m1911','ue_kukri'),
 ('staff_kukri','ue_apprentice_staff','ue_kukri'),('staff_hatchet','ue_apprentice_staff','ue_tactical_hatchet'),
 ('lone_pistol','','ue_m1911'),('lone_kukri','','ue_kukri'),('book','','ue_alchemy_spellbook'),('unarmed','','')]
cases += [dict(id=i,weapon=w,offhand=o,family='combination') for i,w,o in pairs]
for name,data in [('cases',cases),('pilot',[next(c for c in cases if c['id']==i) for i in
 ['ue_frost_crystal_sword','ue_kukri','ue_m4a1','bow_dark','ue_apprentice_staff','tool_shovel']])]:
 (OUT/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('weapon cases:',len(cases))
