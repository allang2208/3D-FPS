import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CONTENT=ROOT.parents[1]/'Content/ColdSteelData'
legacy=json.loads((ROOT/'Reference/legacy-contract.json').read_text(encoding='utf-8'))
item=legacy['runtime_item_contract'].copy()
item.update({'id':'ue_apprentice_staff','name':'学徒长杖','type':'长杖','stack_max':1,'grid_w':1,'grid_h':4,
    'weaponTypeTag':'长杖','staff_revision':1,'melee_damage':3,'melee_reach_cm':165,'attack_seconds':.5,
    'ue_static_mesh':'/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_Base.SM_Staff_Base',
    'ue_icon':'Icons/apprentice_staff.png',
    'world_mesh':'/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_Base.SM_Staff_Base',
    'staff_body_mesh':'/Game/Weapons/ApprenticeStaff20260927/Meshes/SM_Staff_Body.SM_Staff_Body',
    'staff_slots':'head_crystal,crown,shaft_rune,grip_lining,tail_charm,mana_line',
    'desc':'法术学徒常用的练习长杖，以直木杖身和圆头传导魔力。可单手持握，近身时用杖身挥击，也可按修习的元素更换杖头、杖冠与导魔部件。'})
def mesh(slot,id):
    name=f'SM_Staff_{slot}_{id}'
    return f'/Game/Weapons/ApprenticeStaff20260927/Meshes/{name}.{name}'
columns=[]
names={'head_crystal':'原木杖头','crown':'无杖冠','shaft_rune':'无符文','grip_lining':'原木握柄','tail_charm':'无尾坠','mana_line':'无导魔线'}
for slot in legacy['craft']['slots']:
    key=slot['id'];default=mesh(key,'false') if key in ('head_crystal','grip_lining') else ''
    item['staff_part_'+key+'_mesh']=default
    col={'key':key,'name':slot['name'],'default':names[key],'description':'恢复本槽原装部件。','factory_mesh':default,'options':[]}
    for o in legacy['craft']['options'][key]:
        part={'id':o['id'],'name':o['name'],'description':o['desc'],'effects':o['effects'],
              'mesh':mesh(key,o['id']),'icon':f"/Game/Weapons/ApprenticeStaff20260927/Icons/T_{o['id']}.T_{o['id']}"}
        if key=='crown':part['requires_specialty']={'spike_crown':'ice','current_crown':'electric','wreath_crown':'light','heat_crown':'fire'}[o['id']]
        col['options'].append(part)
    columns.append(col)
catalog={'version':1,'weapons':[{'id':'ue_apprentice_staff','traits':[{'icon':'magic','text':'当前主手增加魔法攻击；六槽改造随武器实例保存。'},{'icon':'mechanic','text':'单手持握，物理挥击；杖冠须匹配杖头专精才能激活。'}]}],
         'ticket':'reforge_ticket','first_cost':1,'replace_cost':4,'columns':columns}
for filename,value in [('staffs.json',{'ue_apprentice_staff':item}),('staff-gunsmith.json',catalog)]:
    (CONTENT/filename).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
