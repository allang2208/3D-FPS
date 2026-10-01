"""Publish only HK416 definitions while preserving adjacent catalog text."""
import copy,json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];C=P/'Content/ColdSteelData'
decoder=json.JSONDecoder()
def snapshot(file):
    dest=O/'CodeBefore'/file.relative_to(P);dest.parent.mkdir(parents=True,exist_ok=True)
    if not dest.exists():shutil.copy2(file,dest)
def write(file,old,new):
    snapshot(file)
    if file.read_text(encoding='utf-8-sig')!=old:raise RuntimeError('Catalog changed during publication')
    file.write_text(new,encoding='utf-8')
file=C/'gunsmith.json';old=file.read_text(encoding='utf-8-sig');catalog=json.loads(old)
donor=next(w for w in catalog['weapons'] if w['id']=='ue_m4a1')
w={'id':'ue_hk416','model':'HK416Reworked','name':'HK416','allowed':['optic','muzzle','underbarrel','tactical'],'base':copy.deepcopy(donor['base']),
 'traits':[{'icon':'mechanic','text':'全自动射击，按住扳机连续开火'},
 {'icon':'neutral','text':'原厂机械瞄具，支持全息瞄准镜与消音器'},
 {'icon':'neutral','text':'RVG 垂直握把使用独立握持动作；镭射与手电可选装'}], 'options':{}}
w['base'].update(fire_interval=.075,mag_size=30,ammo_item_id='ammo_556',reload_time=2.1,empty_reload_time=2.7)
for slot,ids in {'optic':['false','holographic'],'muzzle':['false','true'],'underbarrel':['false','vertical_foregrip'],'tactical':['false','laser','flashlight']}.items():
    w['options'][slot]=[copy.deepcopy(next(o for o in donor['options'][slot] if o['id']==id)) for id in ids]
w['options']['optic'][0]['description']='使用原厂觇孔照门与护圈准星。'
w['options']['optic'][1]['description']='安装于机匣顶部导轨的环形分划全息瞄准镜。'
w['options']['muzzle'][0]['description']='保留原厂枪口装置。'
start=old.index('[',old.index('"weapons"'));_,length=decoder.raw_decode(old[start:]);end=start+length
# New HK416 only; existing weapon blocks and unrelated current work remain byte-for-byte.
if any(v['id']=='ue_hk416' for v in catalog['weapons']):
    pos=start+1
    while pos<end:
        while old[pos].isspace() or old[pos]==',':pos+=1
        entry,n=decoder.raw_decode(old[pos:])
        if entry['id']=='ue_hk416':write(file,old,old[:pos]+json.dumps(w,ensure_ascii=False,indent=2)+old[pos+n:]);break
        pos+=n
else:write(file,old,old[:end-1].rstrip()+',\n'+json.dumps(w,ensure_ascii=False,indent=2)+'\n'+old[end-1:])
file=C/'items.json';old=file.read_text(encoding='utf-8-sig');items=json.loads(old)
item=copy.deepcopy(items['ue_m4a1']);item.update(id='ue_hk416',name='HK416',icon='Icons/ue_hk416.png',ue_icon='Icons/ue_hk416.png',
 desc='德国黑克勒与科赫研制的突击步枪，采用短行程活塞导气结构。导轨护木便于配置瞄具、照明和前握把，伸缩枪托便于调整持枪姿态。适合以短点射控制远处目标，也可用连续射击应对近距离交战。')
encoded=json.dumps(item,ensure_ascii=False,indent=2)
if 'ue_hk416' in items:
    key=old.index('"ue_hk416"');start=old.index('{',key);_,n=decoder.raw_decode(old[start:]);new=old[:start]+encoded+old[start+n:]
else:
    end=old.rfind('}');new=old[:end].rstrip()+',\n  "ue_hk416": '+encoded+'\n'+old[end:]
write(file,old,new)
(O/'catalog_publication.json').write_text(json.dumps({'item':item,'weapon':w,'real_weapon_reference':'https://hk-usa.com/wp-content/uploads/2023/09/HK416_HK416-A5-Info-Sheet.pdf','balance':'Game values, not real-world performance measurements','runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('HK416_CATALOG_PUBLISHED')
