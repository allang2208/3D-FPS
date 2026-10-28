"""Rename the existing weapon and replace its innate critical bonus with range."""
from pathlib import Path
import json,datetime,os
P=Path(__file__).parent
root=Path('D:/FPS3D/FPSGAME/Content/ColdSteelData')
before=P/('Before-catalog-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));before.mkdir()
description='高地哨卫以层压长木为弓胎，用暗色钢片包护弓根与叶形弓梢。旧革缠带与侧置箭台保留了山地猎人的习惯，修长弓臂为越过谷地的远射蓄力。使用者须先站稳脚跟，再以沉着的拉放节奏寻找远处的破绽。'
saved=[]
def edit(name,mutate):
    path=root/(name+'.json');raw=path.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    mutate(data)
    output=(json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8')
    if output==raw:return
    if raw!=path.read_bytes():raise RuntimeError('Catalog changed during edit '+name)
    (before/path.name).write_bytes(raw)
    temp=path.with_suffix('.highland.tmp');temp.write_bytes(output);os.replace(temp,path);saved.append(str(path))
def bow(data):
    w=data['bow_woodsteel']
    w.update(name='高地长弓',desc=description,range_cm=4800,critDamageBonus=0)
    w['bow_traits_revision']=max(2,w.get('bow_traits_revision',0))
def gunsmith(data):
    w=next(x for x in data['weapons'] if x['id']=='bow_woodsteel')
    w['traits']=[{'icon':'special','text':'有效射程+50%'},
                 {'icon':'mechanic','text':'无声射击：拉弓、放箭与箭矢命中不会通过声音引起怪物警觉'}]
def woodworking(data):
    w=next(x for x in data['patterns'] if x['id']=='bow_woodsteel_limb')
    w['name']='弓 · 高地长弓'
    w['description']='加工长木弓胎并装配金属结构，加工达标后返回工作面板领取高地长弓。'
edit('bows',bow);edit('bow-gunsmith',gunsmith);edit('woodworking',woodworking)
(P/'catalog-receipt.json').write_text(json.dumps({'saved':saved,'backup':str(before),'weapon_id':'bow_woodsteel','name':'高地长弓','range_cm':4800,'replaced_critDamageBonus':0,'bow_traits_revision':2,'exclusive_riser':'concept_only','gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf8')
print('HIGHLAND_BOW_CATALOG_SAVED')
