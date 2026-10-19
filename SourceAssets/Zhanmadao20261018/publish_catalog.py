"""Merge only this weapon after its UE assets were actually saved."""
import copy,json,shutil,runpy
from pathlib import Path
from datetime import datetime

P=Path(__file__).resolve().parent;ROOT=P.parents[1];DATA=ROOT/'Content/ColdSteelData';ID='ue_zhanmadao'
EX=json.loads((P/'exports.json').read_text(encoding='utf-8'))
receipt=json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))
if not receipt.get('complete'):raise RuntimeError('Save UE assets before publishing')
BACK=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S');BACK.mkdir(parents=True,exist_ok=True)
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def write(name,obj):
    path=DATA/name
    if path.exists():shutil.copy2(path,BACK/name)
    temp=path.with_suffix('.zhanmadao.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
def asset(name):return EX['ue_root']+'/Meshes/'+name+'.'+name
reference=read('xuanchi-zhenyue-modules.json')
catalog={'version':1,'weapon':ID,'interface':'zhanmadao_hilt_v1','drive_bone':reference['drive_bone'],
         'arms_mesh':reference['arms_mesh'],'bone_mount':copy.deepcopy(reference['bone_mount']),
         'trace_from_animation':False,'slots':{}}
for row in EX['parts']:
    spec={'mesh':asset(row['mesh']),'location_cm':row['location_cm'],'interface':'zhanmadao_hilt_v1'}
    if row['slot']=='blade_1':
        spec.update(trace_base_cm=EX['trace_base_cm'],trace_tip_cm=EX['trace_tip_cm'],rune_dimensions_cm=[8,3,EX['blade_tip_cm']])
    catalog['slots'][row['slot']]={'factory':spec}
# Reimporting the factory weapon must retain fitted common modifications.
if (DATA/'zhanmadao-modules.json').exists():
    existing=read('zhanmadao-modules.json')
    existing.update({k:v for k,v in catalog.items() if k!='slots'})
    for slot,choices in catalog['slots'].items():existing.setdefault('slots',{}).setdefault(slot,{}).update(choices)
    catalog=existing
extension=P/'RuneSurfaceV1/catalog_extension.py'
if extension.exists():catalog=runpy.run_path(str(extension))['extend'](catalog)
write('zhanmadao-modules.json',catalog)
items=read('items.json');item=copy.deepcopy(items['ue_xuanchi_zhenyue'])
item.update(id=ID,name='斩马刀',type='双手长刀',weaponTypeTag='双手刀',icon_fallback='斩马刀',
    ue_icon='Icons/ue_zhanmadao.png',modular_sword_catalog='zhanmadao-modules.json',world_mesh=asset(EX['world_mesh']),
    melee_reach_cm=225,attack_seconds=2.04125,desc='边地铸坊为守关刀手打造的双手长刀。修长刀身略带弧度，厚脊与开刃面贯至刀尖，黑红缠柄便于双手分握发力。挥斩时以长刃控制身前距离，回收刀势后可接突刺与格挡。')
for key in ['rarity','grade']:item.pop(key,None)
items[ID]=item;write('items.json',items)
formulas=read('combat-weapon-formulas.json');formulas[ID]=copy.deepcopy(formulas['ue_xuanchi_zhenyue'])
formulas[ID]['source']='ZHANMADAO_INITIAL_ZHENYUE_BASELINE';write('combat-weapon-formulas.json',formulas)
gunsmith=read('melee-gunsmith.json')
entry={'id':ID,'traits':[{'icon':'special','text':'攻击距离 +25%'}]}
index=next((i for i,v in enumerate(gunsmith['weapons']) if (v.get('id') if isinstance(v,dict) else v)==ID),None)
if index is None:gunsmith['weapons'].append(entry)
else:gunsmith['weapons'][index]=entry
write('melee-gunsmith.json',gunsmith)
mapping=read('whirlwind-temporal-materials.json')
mapping[EX['ue_root']+'/Materials/M_Zhanmadao_Surface_V1.M_Zhanmadao_Surface_V1']=EX['ue_root']+'/Materials/M_Zhanmadao_Surface_V1_Whirlwind.M_Zhanmadao_Surface_V1_Whirlwind'
write('whirlwind-temporal-materials.json',mapping)
shutil.copy2(P/'Export/ue_zhanmadao.png',DATA/'Icons/ue_zhanmadao.png')
(P/'catalog_receipt.json').write_text(json.dumps({'definition':ID,'backup':str(BACK),'catalog_saved':True,'game_tested':False},indent=2)+'\n',encoding='utf-8')
print('ZHANMADAO_CATALOG_SAVED',flush=True)
