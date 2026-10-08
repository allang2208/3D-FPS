"""Merge this weapon into live data after its assets have actually been saved."""
import copy,json,shutil
from pathlib import Path
from datetime import datetime
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData';ID='ue_xuanchi_zhenyue'
active=P.parent/'active_revision.json'
if active.exists():
    import runpy
    revision=json.loads(active.read_text());runpy.run_path(revision['publish_script'],run_name='__main__');raise SystemExit(0)
ex=json.loads((P/'exports.json').read_text());receipt=json.loads((P/'import_receipt.json').read_text())
if not receipt.get('complete'):raise RuntimeError('Finish asset creation before publishing its catalog')
BACK=P/'Before'/datetime.now().strftime('%Y%m%d-%H%M%S');BACK.mkdir(parents=True)
def read(name):return json.loads((DATA/name).read_text(encoding='utf-8-sig'))
def write(name,obj):
    path=DATA/name
    if path.exists():shutil.copy2(path,BACK/name)
    temp=path.with_suffix('.xuanchi.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
def asset(name):return ex['ue_root']+'/Meshes/'+name+'.'+name
base=read('frost-sword-modules.json')
catalog={'version':1,'weapon':ID,'interface':'xuanchi_hilt_v1','drive_bone':'WPN_root','arms_mesh':ex['arms_mesh'],'bone_mount':copy.deepcopy(base['bone_mount']),'trace_from_animation':False,'slots':{},'pommel_profile':{'library':'shared-sword-pommels.json','finish':'frost_bronze','interfaces':{}}}
for row in ex['parts']:
    if row['slot']=='tassel':continue
    spec={k:copy.deepcopy(v) for k,v in row.items() if k not in ['slot','mesh','triangles']};spec.update(mesh=asset(row['mesh']),interface='xuanchi_hilt_v1')
    catalog['slots'][row['slot']]={'factory':spec}
tail=next(r for r in ex['parts'] if r['slot']=='tassel')
catalog['slots']['pommel']['factory']['tassel']={'mesh':asset(tail['mesh']),'location_cm':tail['location_cm'],'guides_cm':ex['tassel_guides_cm'],'collision_capsules_cm':ex['tassel_collision_capsules_cm'],'appearance':'赤绳玉坠与柔性剑穗'}
for interface,row in ex['adapters'].items():
    catalog['pommel_profile']['interfaces'][interface]={'location_cm':[0,0,-30-row['depth_cm']],'rotation_deg':[0,0,0],'scale':[row['scale']]*3,'adapter':{'mesh':asset(row['mesh']),'location_cm':[0,0,-30],'interface':'xuanchi_to_'+interface}}
write('xuanchi-zhenyue-modules.json',catalog)
items=read('items.json');item=copy.deepcopy(items['ue_highland_claymore'])
item.update(id=ID,name='玄螭镇岳',type='双手重剑',weaponTypeTag='双手剑',icon_fallback='玄螭镇岳',ue_icon='Icons/'+ID+'.png',modular_sword_catalog='xuanchi-zhenyue-modules.json',viewmodel_mesh=ex['arms_mesh'],world_mesh=asset(ex['world_mesh']),animation_folder=ex['animation_folder'],desc='镇岳铸坊以玄钢锻成的双手重剑，刃面刻有相向盘绕的螭龙与流云，青玉镶于铜护手中央。长柄便于双手发力，横斩之后可接突刺，蓄势时以厚脊承力。环首系着赤绳玉坠与剑穗，挥剑时随惯性摆动。剑刃、护手、握柄、配重与刃面符文可分别改造。')
item['melee_reach_cm']=225
items[ID]=item;write('items.json',items)
formulas=read('combat-weapon-formulas.json');formulas[ID]=copy.deepcopy(formulas['ue_highland_claymore']);formulas[ID]['source']='XUANCHI_SHARED_TWO_HANDED_MELEE_RULES';write('combat-weapon-formulas.json',formulas)
gunsmith=read('melee-gunsmith.json')
if not any((x.get('id') if isinstance(x,dict) else x)==ID for x in gunsmith['weapons']):
    gunsmith['weapons'].append({'id':ID,'traits':[{'icon':'mechanic','text':'双手持剑，占用副手；两次横斩后接突刺'},{'icon':'mechanic','text':'支持蓄力重击、格挡与既有近战技能'},{'icon':'neutral','text':'原装环首带赤绳玉坠和随动作摆动的剑穗'}]})
for col in gunsmith['columns']:
    for option in col['options']:
        if option['id'] in ['bastion_guard','riposte_guard','light_guard','erosion_rune'] and 'weapons' in option and ID not in option['weapons']:option['weapons'].append(ID)
write('melee-gunsmith.json',gunsmith)
(P/'catalog_receipt.json').write_text(json.dumps({'definition':ID,'catalog':str(DATA/'xuanchi-zhenyue-modules.json'),'backup':str(BACK),'game_tested':False},indent=2),encoding='utf-8');print('XUANCHI_CATALOG_SAVED')
