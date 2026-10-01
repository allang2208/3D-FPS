"""Publish only G18 catalog entries after the asset import has saved."""
from pathlib import Path
import copy,json
P=Path('D:/FPS3D/FPSGAME');O=Path(__file__).parent;D=P/'Content/ColdSteelData';ROOT='/Game/Weapons/G18/Integrated20260929'
def insert_object(path,key,value):
    text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
    if key in data:
        needle=json.dumps(key)+':';a=text.index(needle)+len(needle)
        while text[a].isspace():a+=1
        _,length=json.JSONDecoder().raw_decode(text[a:]);b=a+length
        new=text[:a]+json.dumps(value,ensure_ascii=False,indent=2)+text[b:]
    else:
        at=text.rfind('}');prefix=text[:at].rstrip();new=prefix+(',\n' if data else '\n')+'  '+json.dumps(key)+': '+json.dumps(value,ensure_ascii=False,indent=2)+'\n'+text[at:]
    if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Concurrent catalog edit: '+str(path))
    path.write_text(new,encoding='utf8')
items=json.loads((D/'items.json').read_text(encoding='utf-8-sig'));item=copy.deepcopy(items['ue_m1911'])
item.update(id='ue_g18',name='G18',icon='Icons/ue_g18.png',ue_icon='Icons/ue_g18.png',
    desc='奥地利格洛克公司设计的自动手枪，采用聚合物底把与短行程后座结构，发射九毫米手枪弹。紧凑枪身适合快速拔枪与近距离连续射击；连射会迅速消耗弹匣并积累后坐，短促连射更容易控制。',
    stats=[{'name':'物理攻击','value':'18'},{'name':'弹匣容量','value':'17'}])
insert_object(D/'items.json','ue_g18',item)
p=D/'gunsmith.json';text=p.read_text(encoding='utf-8-sig');data=json.loads(text)
w=copy.deepcopy(next(w for w in data['weapons'] if w['id']=='ue_m1911'))
w.update(id='ue_g18',model='G18',name='G18')
for options in w['options'].values():
    for o in options:o['description']=o['description'].replace('M1911','G18').replace('单排','双排')
w['base']={'ammo_item_id':'ammo_9','mag_size':17,'ads_smooth':16.64295707529995,'recoil':70,'camera_shake':105,'fire_interval':.05,'reload_time':1.75,'empty_reload_time':2.25,'damage':18,'bullet_speed':375,'effective_range':40,'spread_mult':1.05,'automatic':True}
w['options']['trigger']=[{'id':'false','name':'标准扳机','description':'保持 G18 的全自动射击节奏。','effects':[],'stats':{}},
    {'id':'g18_controlled_trigger','name':'稳控扳机','description':'放缓连射节奏，改善连续射击时的枪口控制。','effects':[{'text':'射击间隔增加20%','benefit':-1},{'text':'后坐力降低10%','benefit':1}],'stats':{'fire_interval_mult':1.2,'recoil_mult':.9}}]
w['options']['magazine']=[{'id':'false','name':'原厂弹匣','description':'原厂双排弹匣，保持紧凑外形。','effects':[],'stats':{}},
    {'id':'ext_mag','name':'扩容弹匣','description':'沿原厂弹匣壳体向下延长，保留插接口、卡笋槽和抓握区。','effects':[{'text':'弹匣容量增加16发','benefit':1},{'text':'装填耗时增加10%','benefit':-1},{'text':'开镜耗时增加5%','benefit':-1}],'stats':{'mag_delta':16,'reload_mult':1.1,'ads_percent':.05}}]
w['pistol_grip_surface']={'mesh':ROOT+'/Attachments/SM_G18_GripSurface','bone':'WPN_root'}
w['traits']=[{'icon':'mechanic','text':'全自动，按住扳机连续射击；原厂 17 发双排弹匣'},
    {'icon':'drawback','text':'连续射击会迅速消耗弹药并积累后坐与散布'},
    {'icon':'special','text':'支持单持、双持以及作为法杖副手；每只手独立连射与换弹'},
    {'icon':'neutral','text':'瞄具、枪口、弹匣、枪管、握把防滑层、扳机与战术挂件可改造'}]
old=next((v for v in data['weapons'] if v['id']=='ue_g18'),None)
if old:
    idpos=text.index('"id": "ue_g18"');a=text.rfind('{',0,idpos);_,n=json.JSONDecoder().raw_decode(text[a:]);b=a+n
    new=text[:a]+json.dumps(w,ensure_ascii=False,indent=2)+text[b:]
else:
    idpos=text.index('"id": "ue_m1911"');a=text.rfind('{',0,idpos);_,n=json.JSONDecoder().raw_decode(text[a:]);b=a+n
    new=text[:b]+',\n    '+json.dumps(w,ensure_ascii=False,indent=2)+text[b:]
if p.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Concurrent gunsmith edit')
p.write_text(new,encoding='utf8')
(O/'catalog.json').write_text(json.dumps({'item':item,'weapon':w,'reference':'https://eu.glock.com/en/Technology/Full-Auto','game_balance':'Damage, recoil, range and timing are game values; no live test'},ensure_ascii=False,indent=2),encoding='utf8')
print('G18 catalog published')
