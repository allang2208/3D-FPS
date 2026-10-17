"""Merge the new weapon into the current catalogs without touching existing items."""
from pathlib import Path
import json,copy,hashlib,runpy
O=Path(__file__).parent;P=O.parents[1];root=P/'Content/ColdSteelData'
def update(name,fn):
 f=root/name;old=f.read_bytes();data=json.loads(old.decode('utf-8-sig'));fn(data)
 if f.read_bytes()!=old:raise RuntimeError('Catalog changed during merge: '+name)
 backup=O/'Before/Content/ColdSteelData'/name;backup.parent.mkdir(parents=True,exist_ok=True)
 if not backup.exists():backup.write_bytes(old)
 f.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def items(d):
 item=copy.deepcopy(d['ue_super90']);item.update(id='ue_m870',name='M870 Tactical',icon='Icons/ue_m870.png',ue_icon='Icons/ue_m870.png',desc='雷明顿 870 系列的战术型泵动霰弹枪，采用管式弹仓和传统枪托。每次射击后拉动护木退壳，再前推完成供弹。适合近距离掌握节奏逐发射击；装填时从机匣下方逐发补弹，也可提前结束补弹。');item['stats']=[{'name':'物理攻击','value':'80'},{'name':'弹匣容量','value':'7'}];d['ue_m870']=item
def gunsmith(d):
 donor=next(x for x in d['weapons'] if x['id']=='ue_super90');w=copy.deepcopy(donor);w.update(id='ue_m870',model='M870',name='M870 Tactical');w['base'].update(fire_interval=.90,reload_time=1.65,empty_reload_time=424/60,recoil=290,camera_shake=120,spread_mult=1.2375,mag_size=7,damage=80)
 w['allowed']=[s for s in w['allowed'] if s!='reargrip']
 w['options']={k:[dict(id='false',name={'optic':'原厂机械瞄具','muzzle':'原厂枪口','underbarrel':'泵动护木','stock':'原厂枪托','magazine':'原厂管式弹仓','reload_device':'逐发装填','tactical':'无战术装置'}.get(k,'原厂组件'),description='使用 M870 Tactical 的原装结构。',effects=[],stats={})] for k in w['allowed']}
 w['options']['tactical']=copy.deepcopy(donor['options']['tactical'])
 w['traits']=[dict(icon='special',text='泵动上膛：每发射击后完成后拉退壳与前推供弹。'),dict(icon='special',text='管式弹仓逐发补弹，开火或瞄准可在当前入弹完成后结束装填。')]
 existing=next((x for x in d['weapons'] if x['id']=='ue_m870'),None)
 if existing:
  for slot in w['allowed']:
   if slot=='tactical':continue
   w['options'][slot]+=copy.deepcopy([x for x in existing.get('options',{}).get(slot,[]) if x['id']!='false'])
 runpy.run_path(str(O.parent/'M870LightweightTrigger20261017/catalog_option.py'))['merge'](w)
 d['weapons']=[x for x in d['weapons'] if x['id']!='ue_m870']+[w]
update('items.json',items);update('gunsmith.json',gunsmith)
def formula(d):
 row=copy.deepcopy(d['ue_super90']);row['source']='M870 (whole-cartridge aggregate)';d['ue_m870']=row
update('combat-weapon-formulas.json',formula)
def assembly(d):
 recipe=json.loads((O/'Assembly/recipe.json').read_text(encoding='utf-8'));d['recipes']=[r for r in d['recipes'] if r['id']!='assemble_m870']+[recipe]
update('gun-assembly.json',assembly)
config=P/'Config/DefaultGame.ini';old=config.read_text(encoding='utf-8-sig');line='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/M870")'
if line not in old:
 anchor='+DirectoriesToAlwaysCook=(Path="/Game/Weapons/Super90/Cransh20261006")'
 if anchor not in old:raise RuntimeError('Missing firearm cook section anchor')
 config.write_text(old.replace(anchor,anchor+'\n'+line,1),encoding='utf-8')
receipt=dict(model='M870 Tactical',author='WillisChiejina',source='https://sketchfab.com/3d-models/m870-tactical-fad4289d1083447d9c8cc833362b04c6',license='CC BY 4.0',license_url='https://creativecommons.org/licenses/by/4.0/',archives={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in (O/'Original').glob('m870_*') if f.is_file()},runtime_tested=False)
(O/'acquisition_receipt.json').write_text(json.dumps(receipt,indent=2));print('M870_CATALOG_REGISTERED')
