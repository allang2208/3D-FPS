"""Publish only this weapon's catalog entries after its real assets are saved."""
import json,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=P/'Content/ColdSteelData';ID='ue_rsh12'
if not json.loads((O/'import_receipt.json').read_text())['complete']:raise RuntimeError('Assets have not finished saving')
def write(path,text,new):
 if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Concurrent catalog edit '+str(path))
 backup=O/'BeforeCatalog'/path.name;backup.parent.mkdir(exist_ok=True,parents=True)
 if not backup.exists():backup.write_text(text,encoding='utf8')
 path.write_text(new,encoding='utf8')
def key(path,k,v):
 text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
 if k in data:
  a=text.index(json.dumps(k)+':')+len(json.dumps(k))+1
  while text[a].isspace():a+=1
  _,n=json.JSONDecoder().raw_decode(text[a:]);new=text[:a]+json.dumps(v,ensure_ascii=False,indent=2)+text[a+n:]
 else:
  a=text.rfind('}');new=text[:a].rstrip()+(',\n' if data else '\n')+json.dumps(k)+': '+json.dumps(v,ensure_ascii=False,indent=2)+'\n'+text[a:]
 write(path,text,new)
# RSH12_SINGLE_ACTION_AMENDMENT: preserve the saved single-action revision on reimport.
amendment=O.parent/'RSH12SingleAction20261003'
single_action=None
if (amendment/'import_receipt.json').exists() and json.loads((amendment/'import_receipt.json').read_text(encoding='utf8')).get('complete'):
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_single_action_catalog',amendment/'publish_catalog.py')
 single_action=importlib.util.module_from_spec(spec);spec.loader.exec_module(single_action)
items=json.loads((D/'items.json').read_text(encoding='utf-8-sig'));item=copy.deepcopy(items['ue_dan_wesson715'])
item.update(id=ID,name='RSH-12',icon='Icons/ue_rsh12.png',ue_icon='Icons/ue_rsh12.png',icon_fallback='RSH12',gunsmith_base_mag=5,
 weaponTypeTag='左轮手枪',type='武器',desc='俄罗斯大口径双动左轮，使用12.7毫米弹药，五发弹巢。枪管位于弹巢下方，低轴线结构减小枪口上跳；黑色聚合物握柄与上下导轨保留原厂外形。逐发装填，非空仓保留余弹，空仓先退壳再补弹。',
 stats=[{'name':'物理攻击','value':'90'},{'name':'弹巢容量','value':'5'}])
if single_action:single_action.apply_item(item)
key(D/'items.json',ID,item)
defaults={'trigger':('原厂双动扳机','每次扣动发射一发。'),'reload_device':('逐发装填','五发弹巢；非空仓保留余弹，空仓先退壳。'),
 'optic':('原厂机械瞄具','使用原厂照门和准星。'),'muzzle':('原厂枪口','保留低轴线枪管。'),'reargrip':('原厂握柄','保留黑色聚合物握柄。'),'tactical':('无战术挂件','保持原厂导轨外形。')}
options={k:[dict(id='false',name=v[0],description=v[1],effects=[],stats={})] for k,v in defaults.items()}
options['trigger'].append(dict(id='rsh12_lightweight_fast',name='轻型快速扳机',description='保持双动单发输入，缩短射击间隔20%。',effects=[dict(text='射击间隔降低20%',benefit=1)],stats=dict(fire_interval_mult=.8)))
w=dict(id=ID,model='RSH12',name='RSH-12',allowed=list(defaults),options=options,
 base=dict(ammo_item_id='ammo_127',mag_size=5,ads_smooth=13.616964,recoil=180,camera_shake=140,fire_interval=.38,reload_time=5.7,empty_reload_time=7.7,damage=90,bullet_speed=300,effective_range=60,automatic=False),
 traits=[dict(icon='mechanic',text='双动左轮；12.7毫米弹药；五发弹巢'),dict(icon='special',text='下置枪管；逐发装填，非空仓保留余弹'),dict(icon='neutral',text='支持单持、双持和法杖副手；每手独立装填')])
if single_action:single_action.apply_weapon(w)
# Preserve the explicit 2026-10-04 recoil / stability tuning on a source rebuild.
balance=O.parent/'RSH12CubeConcept20261004/publish_balance.py'
if balance.exists():
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_base_balance',balance)
 balance_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(balance_module)
 balance_module.apply_weapon(w)
path=D/'gunsmith.json';text=path.read_text(encoding='utf-8-sig');data=json.loads(text);old=next((v for v in data['weapons'] if v['id']==ID),None)
# Retain the explicitly installed RSH surface-treatment family on source reimport.
grip_surface=O.parent/'RSH12GripSurfaces20261004'
if (grip_surface/'import_receipt.json').exists() and json.loads((grip_surface/'import_receipt.json').read_text(encoding='utf8')).get('complete'):
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_grip_surface_catalog',grip_surface/'publish_catalog.py')
 grip_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(grip_module)
 grip_module.apply_weapon(w,data)
# Keep the approved exclusive cube option when rebuilding this weapon's catalog.
cube=O.parent/'RSH12CubeSuppressor20261004'
if (cube/'catalog_receipt.json').exists():
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_cube_catalog',cube/'publish_catalog.py')
 cube_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(cube_module)
 cube_module.apply_weapon(w)
# The accepted RSH base-spread and square-sight revision survives source rebuilds.
square_optics=O.parent/'RSH12SquareOpticsBalance20261004/publish_catalog.py'
if square_optics.exists():
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_square_optics',square_optics)
 square_module=importlib.util.module_from_spec(spec);spec.loader.exec_module(square_module)
 square_module.apply_weapon(w)
foregrips=O.parent/'RSH12Foregrips20261004/publish_catalog.py'
if foregrips.exists():
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_foregrips',foregrips)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.apply_weapon(w)
heavy_grip=O.parent/'RSH12HeavyGrip20261004/Integration20261005/publish_catalog.py'
if heavy_grip.exists() and (heavy_grip.parent/'import_receipt.json').exists():
 import importlib.util
 spec=importlib.util.spec_from_file_location('rsh12_heavy_grip',heavy_grip)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.apply_weapon(w)
quick_grip=O.parent/'RSH12QuickDrawGrip20261005/Integration20261005/publish_catalog.py'
if quick_grip.exists() and (quick_grip.parent/'import_receipt.json').exists():
 if json.loads((quick_grip.parent/'import_receipt.json').read_text()).get('complete'):
  import importlib.util
  spec=importlib.util.spec_from_file_location('rsh12_quickdraw_grip',quick_grip)
  module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.apply_weapon(w)
needle=json.dumps(ID if old else 'ue_dan_wesson715');pos=text.index(needle,text.index('"weapons"'));a=text.rfind('{',0,pos);_,n=json.JSONDecoder().raw_decode(text[a:]);b=a+n
new=text[:a]+json.dumps(w,ensure_ascii=False,indent=2)+text[b:] if old else text[:b]+',\n'+json.dumps(w,ensure_ascii=False,indent=2)+text[b:]
write(path,text,new)
formula=dict(source='RSH12_IMPORT_INITIAL',base=36,enhanceFlat=1.,attrs=[dict(key='dex',base=.8,perEnhance=.1),dict(key='wis',base=1.6,perEnhance=.15)])
key(D/'combat-weapon-formulas.json',ID,formula)
(O/'catalog.json').write_text(json.dumps(dict(item=item,weapon=w,combat_formula=formula,balance='Initial values; user testing pending',factory_geometry_only=True),ensure_ascii=False,indent=2),encoding='utf8')
print('RSH12_CATALOG_PUBLISHED')
