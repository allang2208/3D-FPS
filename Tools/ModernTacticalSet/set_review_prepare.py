"""Inventory the currently selected TS01 set for the user-requested model review."""
import json, hashlib
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME'); S=P/'SourceAssets/ModernTacticalSet20261113'; R=S/'SetFitReview20261115'
R.mkdir(exist_ok=True)
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d): Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
c=read(P/'Content/ColdSteelData/modular_outfits.json'); b=read(P/'Content/ColdSteelData/player_body.json')
write(R/'modular_outfits.snapshot.json',c);write(R/'player_body.snapshot.json',b)
rows={}; pairs=[]
def add(path,key,role,rig,**kw):
    path=path.split('.')[0]
    if path in rows:
        rows[path]['aliases'].append(key);return rows[path]['key']
    rows[path]=dict(path=path,key=key,role=role,rig=rig,aliases=[key],**kw);return key
for rig,conf,bc in [('Jason',c,b),('Kaitlin',c['body_variants']['kaitlin'],b['body_variants']['kaitlin'])]:
    items=conf['items'];sh=items['ue_modern_kevlar_vest'];pa=items['ue_modern_tactical_pants']
    native=conf['profiles'][bc['body_mesh']]['native_bare_skin']
    add(native,rig+'_body','body',rig)
    for k in ['boots','gloves']:add(items['ue_modern_tactical_'+k]['rig_meshes'][rig],rig+'_'+k,k,rig)
    add(bc['head_equipment']['ue_modern_tactical_helmet']['static_mesh'],rig+'_helmet','helmet',rig)
    base=pa['rig_meshes'][rig];tactical=pa['shoe_fit_meshes']['ue_modern_tactical_boots'][rig]
    for key,path in [('pants',base),('pants_tactical',tactical)]+[(shoe,vs[rig]) for shoe,vs in pa['shoe_fit_meshes'].items()]:add(path,rig+'_'+key,'pants',rig)
    for style,path in [('bare_waist',None),('tactical',tactical),('regular',base)]:
        pair=sh if path is None else sh['pants_mesh_fit_meshes'].get(path,sh['pants_fit_meshes']['ue_modern_tactical_pants'])
        for view,field in [('world','rig_meshes'),('owner','owner_body_meshes')]:
            key=add(pair[field][rig],rig+'_shirt_'+style+'_'+view,'shirt',rig,view=view)
            pairs.append(dict(rig=rig,style=style,view=view,shirt=key,pants=rows[path.split('.')[0]]['key'] if path else None))
for rig,path in c['items']['ue_modern_kevlar_vest']['rig_meshes'].items():
    if rig in ['Jason','Kaitlin']:continue
    add(path,'FP_'+rig+'_shirt','fp_shirt',rig)
    gp=c['items']['ue_modern_tactical_gloves']['rig_meshes'][rig];add(gp,'FP_'+rig+'_gloves','fp_gloves',rig)
candidates={}
for file in [S/'CombatShirtR3/authored.json',S/'CombatShirtR3/CuffRepairR1/authored-world.json',S/'CombatShirtR3/CuffRepairR1/gloves-authored.json']:
    for row in read(file)['rows']:candidates.setdefault(row['asset'].split('.')[0],[]).append(row['file'])
for row in rows.values():
    key=row['key'];rig=row['rig'];extra=[]
    if row['role']=='boots':extra=[str(S/'Integration/Delivery'/f'boots_{rig}_Wear.json')]
    if row['role']=='helmet':extra=[str(S/'HelmetHairFitR1/Authored'/f'helmet_{rig}_wear.json')]
    if row['role']=='body':extra=[str(S/'CombatShirtR3/Inputs'/f'Body_{rig}.json')]
    row['candidates']=list(dict.fromkeys(candidates.get(row['path'],[])+extra))
    disk=P/'Content'/(row['path'].removeprefix('/Game/')+'.uasset')
    row['disk']=str(disk);row['asset_sha256']=hashlib.sha256(disk.read_bytes()).hexdigest() if disk.exists() else None
write(R/'plan.json',dict(rows=list(rows.values()),pairs=pairs,scope='Current full TS01 set, both bodies, world/owner and 24 first-person rigs. Other clothing combinations excluded.',gameplay=False))
print('SET_REVIEW_PLAN',len(rows),'missing',sum(not r['asset_sha256'] for r in rows.values()))
