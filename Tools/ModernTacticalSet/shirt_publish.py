"""Publish only TS01 shirt, dedicated calf fit, and unchanged-waist aliases."""
import json,copy,sys,os,uuid,hashlib,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR1';D=P/'Content/ColdSteelData'
if (R/'release-block.json').exists():raise RuntimeError('Superseded concept-fidelity draft; publication stopped')
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
saved=read(R/'saved.json');authored=read(R/'authored.json');art=read(R/'artwork-saved.json')
if not saved['completed'] or not art['completed']:raise RuntimeError('Complete actual asset saves first')
mapping={};pants={}
for row in authored['rows']:
    item=saved['wear'][row['asset']]
    if item['sha256']!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():raise RuntimeError('Unsaved source '+row['file'])
    if row.get('source'):mapping[row['source']]=item['asset']
    else:pants[row['rig']]=item['asset']
source=read(R/'Inputs/modular_outfits.json');V='ue_modern_kevlar_vest';T='ue_modern_tactical_pants';B='ue_modern_tactical_boots'
def substitute(value):
    if isinstance(value,dict):return {k:substitute(v) for k,v in value.items()}
    if isinstance(value,list):return [substitute(v) for v in value]
    if isinstance(value,str):return mapping.get(value,value)
    return value
def transaction(path,edits):
    raw=path.read_bytes();text=raw.decode('utf-8-sig');doc=json.loads(text)
    for keys,value in edits:
        parent=doc
        for k in keys[:-1]:parent=parent[k]
        text=entries.replace(text,keys,value) if keys[-1] in parent else entries.insert(text,keys[:-1],keys[-1],value);parent[keys[-1]]=value
    (R/'BeforePublish').mkdir(exist_ok=True);backup=R/'BeforePublish'/path.name
    if not backup.exists():backup.write_bytes(raw)
    tmp=path.with_suffix('.combat-'+uuid.uuid4().hex+'.tmp');tmp.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
    if path.read_bytes()!=raw:raise RuntimeError('Concurrent config edit '+str(path))
    os.replace(tmp,path)
cfg=read(D/'modular_outfits.json');edits=[];route_count=0
for prefix,rig,old in [(['items'],'Jason',source),(['body_variants','kaitlin','items'],'Kaitlin',source['body_variants']['kaitlin'])]:
    items=cfg
    for k in prefix:items=items[k]
    shirt=substitute(copy.deepcopy(old['items']['ue_st6_sleeves']));shirt.update(appearance_family='TS01CombatShirt20261114',first_person_mode='native_sleeves',wear_mode='native_body_with_tucked_trim_and_outer_carrier',pants_fit_pipeline='Tools/ModernTacticalSet/shirt_author.py',waist_fit_revision='TS01CombatShirtR1-native-waist')
    for target,overrides in shirt['base_material_overrides'].items():
        for slot in overrides:overrides[slot]=saved['materials']['fabric' if slot in ['0','1'] else target]
    oldboot=items[T]['shoe_fit_meshes'][B][rig];newboot=pants[rig]
    upperfit=copy.deepcopy(shirt['pants_mesh_fit_meshes'].get(oldboot,shirt['pants_fit_meshes'][T]));shirt['pants_mesh_fit_meshes'][newboot]=upperfit
    edits.append((prefix+[V],shirt));edits.append((prefix+[T,'shoe_fit_meshes',B],{rig:newboot}))
    for key,recipe in items.items():
        if key==V or recipe.get('slot')!=7:continue
        fit=recipe.get('pants_mesh_fit_meshes',{}).get(oldboot)
        if fit is not None:edits.append((prefix+[key,'pants_mesh_fit_meshes',newboot],copy.deepcopy(fit)));route_count+=1
transaction(D/'modular_outfits.json',edits)
catalog=read(D/'items.json');transaction(D/'items.json',[([V,'desc'],'土棕色凯夫拉防弹衣配深棕弹力躯干、土棕长袖作战上衣。低圆领、贴臂袖袋和护肘，后摆扎入裤腰；袖口与全指手套衔接。'),([V,'world_mesh'],art['pickup']),([V,'ue_equipment_icon_mesh'],art['display'])])
png=read(R/'artwork.json')['icon']['png']
for destination in [D/catalog[V]['ue_icon'],D/'Icons'/(V+'.png')]:
    tmp=destination.with_suffix('.'+uuid.uuid4().hex+'.tmp');shutil.copyfile(png,tmp);os.replace(tmp,destination)
policy=dict(mode='native_body_with_tucked_trim',producer='Tools/ModernTacticalSet/shirt_author.py',source_root='SourceAssets/ModernTacticalSet20261113/CombatShirtR1',requires_native_waist_refresh=True,outer_slots={'Jason':[1],'Owner_Jason':[0]},outer_carrier_preserved=True)
transaction(P/'Tools/GarmentWaist/policies.json',[(['shirts',V],policy)])
(R/'published.json').write_text(json.dumps(dict(completed=True,wear_assets=len(saved['wear']),pants=pants,unchanged_waist_aliases=route_count,artwork=art,inventory_granted=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8');print('TS01_COMBAT_PUBLISHED',flush=True)
