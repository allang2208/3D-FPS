"""Release R3 saved surfaces through existing stable TS01 equipment routes."""
import json,copy,sys,os,uuid,hashlib,shutil,ast
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/CombatShirtR3';D=P/'Content/ColdSteelData'
sys.path.insert(0,str(P/'Tools/BrownLeatherSet'));import json_entries as entries
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
tree=ast.parse((P/'Tools/ModernTacticalSet/shirt_publish.py').read_text(encoding='utf-8'));exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='transaction'],type_ignores=[]),'r3_field_release','exec'))
saved=read(R/'saved.json');authored=read(R/'authored.json');art=read(R/'artwork-saved.json');baseline=read(R/'Inputs/baseline.json')['rows'];mapping={};pants={}
if not saved.get('completed') or not art.get('completed'):raise RuntimeError('Save every authored garment and artwork first')
for row in authored['rows']:
    record=saved['wear'][row['asset']]
    if record['sha256']!=hashlib.sha256(Path(row['file']).read_bytes()).hexdigest():raise RuntimeError('Unsaved source '+row['file'])
    old=next(x for x in baseline if x['rig']==row['rig'] and x.get('source')==row.get('source') and x.get('kind')==row.get('kind'));path=old['asset'];mapping[path]=record['asset'];mapping[path+'.'+path.rsplit('/',1)[-1]]=record['asset']
    if row.get('kind'):pants[row['rig']+'/'+row['kind']]=record['asset']
for name,path in saved['materials'].items():
    old=path.replace('CombatShirtR3','CombatShirtR2');mapping[old]=path;mapping[old.split('.')[0]]=path
def replace(value,keys=False):
    if isinstance(value,dict):return {(mapping.get(k,k) if keys else k):replace(v,keys) for k,v in value.items()}
    if isinstance(value,list):return [replace(v,keys) for v in value]
    return mapping.get(value,value) if isinstance(value,str) else value
V='ue_modern_kevlar_vest';T='ue_modern_tactical_pants';current=read(D/'modular_outfits.json');edits=[];aliases=0
for prefix,rig in [(['items'],'Jason'),(['body_variants','kaitlin','items'],'Kaitlin')]:
    items=current
    for k in prefix:items=items[k]
    shirt=replace(copy.deepcopy(items[V]));shirt.update(appearance_family='TS01PhysicalCloth20261114',pants_fit_pipeline='Tools/ModernTacticalSet/combat3_assemble.py',waist_fit_revision='TS01CombatShirtR3-native-waist',wear_mode='low_crew_tucked_combat_shirt_with_carrier')
    # Pants keep their native waist; preserve old aliases while registering
    # each new ordinary and boot-fit package in every existing upper recipe.
    for item,recipe in items.items():
        if recipe.get('slot')!=7:continue
        fits=shirt.get('pants_mesh_fit_meshes',{}) if item==V else recipe.get('pants_mesh_fit_meshes',{})
        for old,new in mapping.items():
            if '/SK_TS01_pants' not in old or old not in fits:continue
            value=copy.deepcopy(fits[old])
            if item==V:shirt.setdefault('pants_mesh_fit_meshes',{})[new]=value
            else:edits.append((prefix+[item,'pants_mesh_fit_meshes',new],value));aliases+=1
    trousers=replace(copy.deepcopy(items[T]));trousers['appearance_family']='TS01PhysicalCloth20261114'
    edits.extend([(prefix+[V],shirt),(prefix+[T],trousers)])
transaction(D/'modular_outfits.json',edits)
catalog=read(D/'items.json');transaction(D/'items.json',[([V,'desc'],'土棕色凯夫拉防弹衣搭配低圆领作战上衣，防撕裂袖片和深棕弹力躯干，肘部与袖口自然堆褶，后摆扎入裤腰。'),([V,'world_mesh'],art['pickup']),([V,'ue_equipment_icon_mesh'],art['display']),([T,'world_mesh'],art['pants_pickup']),([T,'ue_equipment_icon_mesh'],art['pants_display'])])
for item,file in [(V,'artwork.json'),(T,'lower-artwork.json')]:
    for dest in [D/catalog[item]['ue_icon'],D/'Icons'/(item+'.png')]:
        tmp=dest.with_suffix('.'+uuid.uuid4().hex+'.tmp');shutil.copyfile(read(R/file)['icon']['png'],tmp);os.replace(tmp,dest)
policy=read(P/'Tools/GarmentWaist/policies.json')['shirts'][V];policy.update(producer='Tools/ModernTacticalSet/combat3_assemble.py',source_root='SourceAssets/ModernTacticalSet20261113/CombatShirtR3');transaction(P/'Tools/GarmentWaist/policies.json',[(['shirts',V],policy)])
(R/'published.json').write_text(json.dumps(dict(completed=True,wear_assets=len(authored['rows']),pants=pants,artwork=art,waist_aliases=aliases,inventory_granted=False,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8');print('TS01_COMBAT3_PUBLISHED',flush=True)
