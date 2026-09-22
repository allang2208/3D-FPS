"""Merge this new weapon into the live item/formula/modification catalogs."""
import copy,json,shutil
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
ID='ue_highland_claymore';exports=json.loads((P/'exports.json').read_text(encoding='utf-8'));D=exports['ue_root']
stamp=datetime.now().strftime('%Y%m%d-%H%M%S');backup=P/'Before'/stamp;backup.mkdir(parents=True,exist_ok=True)
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def write(name,value):
    path=DATA/name
    if path.exists():shutil.copy2(path,backup/name)
    temp=path.with_suffix(path.suffix+'.highland.tmp');temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
def asset(name):return D+'/Meshes/'+name+'.'+name
catalog={'version':1,'weapon':ID,'interface':'highland_hilt_v1','drive_bone':'WPN_root','arms_mesh':exports['arms_mesh'],'bone_mount':copy.deepcopy(read('frost-sword-modules.json')['bone_mount']),'trace_from_animation':False,'slots':{},'pommel_profile':{'library':'shared-sword-pommels.json','finish':'frost_bronze','interfaces':{}}}
for row in exports['parts']:
    spec={k:copy.deepcopy(v) for k,v in row.items() if k not in ['slot','id','mesh','triangles']}
    spec.update(mesh=asset(row['mesh']),interface='highland_hilt_v1')
    catalog['slots'].setdefault(row['slot'],{})[row['id']]=spec
for key,row in exports['adapters'].items():
    catalog['pommel_profile']['interfaces'][key]={'location_cm':[0,0,-22.7-row['depth_cm']],'rotation_deg':[0,0,0],'scale':[row['scale']]*3,'adapter':{'mesh':asset(row['mesh']),'location_cm':[0,0,-22.7],'interface':'highland_hilt_v1_to_'+key}}
write('highland-claymore-modules.json',catalog)
items=read('items.json');item=copy.deepcopy(items['ue_rune_sword'])
item.update(id=ID,name='高地·双手剑',type='高地双手剑',icon_fallback='高地',ue_icon='Icons/'+ID+'.png',
    desc='修长钢刃镌刻苍蓝符文，弧形护手与圆盘配重延续高地双手剑的形制。支持三段连击、蓄力重击、突刺与格挡，占用副手槽；剑刃、护手、握把、配重和刃面符文可独立改造。',
    modular_sword_catalog='highland-claymore-modules.json',viewmodel_mesh=exports['arms_mesh'],world_mesh=asset(exports['world_mesh']),
    melee_damage=55,melee_reach_cm=180,animation_folder=exports['animation_folder'])
items[ID]=item;write('items.json',items)
formulas=read('combat-weapon-formulas.json');formulas[ID]=copy.deepcopy(formulas['ue_rune_sword']);formulas[ID]['source']='HIGHLAND_CLAYMORE_SHARED_TWO_HANDED_RULES';write('combat-weapon-formulas.json',formulas)
gunsmith=read('melee-gunsmith.json')
if ID not in gunsmith['weapons']:gunsmith['weapons'].append(ID)
for column in gunsmith['columns']:
    for option in column['options']:
        if column['key']=='guard' or option['id']=='erosion_rune':
            if 'weapons' in option and ID not in option['weapons']:option['weapons'].append(ID)
write('melee-gunsmith.json',gunsmith)
# Entity icons are authored from this sword. Shared semantic rune icons retain
# the accepted meanings/palette; shared pummels retain the same six actual models.
icons=[];target=DATA/'AttachmentIcons20260913'
for file in (P/'Icons').glob('*.png'):
    destination=(DATA/'Icons' if file.stem==ID else target)/file.name
    destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,destination);icons.append(str(destination.relative_to(ROOT)))
for option in ['false','resonance_rune','erosion_rune','conduction_rune']:
    src=target/('ue_rune_sword_blade_2_'+option+'.png');dst=target/(ID+'_blade_2_'+option+'.png');shutil.copy2(src,dst);icons.append(str(dst.relative_to(ROOT)))
src=target/'ue_rune_sword_category_blade_2.png';dst=target/(ID+'_category_blade_2.png');shutil.copy2(src,dst);icons.append(str(dst.relative_to(ROOT)))
for option in read('shared-sword-pommels.json')['options']:
    src=target/('ue_frost_crystal_sword_pommel_'+option+'.png')
    if not src.exists():src=target/('ue_rune_sword_pommel_'+option+'.png')
    if not src.exists():raise RuntimeError('Shared pommel icon source missing: '+option)
    dst=target/(ID+'_pommel_'+option+'.png');shutil.copy2(src,dst);icons.append(str(dst.relative_to(ROOT)))
receipt={'time':stamp,'definition':ID,'name':item['name'],'catalog':str(DATA/'highland-claymore-modules.json'),'icons':icons,'damage_formula':formulas[ID],'shared_pommels':list(read('shared-sword-pommels.json')['options']),'backup':str(backup),'tested':False}
(P/'catalog_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('HIGHLAND_CATALOG_INSTALLED '+ID)
