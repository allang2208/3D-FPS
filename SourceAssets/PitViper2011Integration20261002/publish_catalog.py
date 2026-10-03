"""Publish this weapon after real packages have been imported and saved."""
import copy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];D=P/'Content/ColdSteelData';ID='ue_pit_viper2011'
def replace_key(path,key,value):
    text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
    if key in data:
        needle=json.dumps(key)+':';a=text.index(needle)+len(needle)
        while text[a].isspace():a+=1
        _,n=json.JSONDecoder().raw_decode(text[a:]);new=text[:a]+json.dumps(value,ensure_ascii=False,indent=2)+text[a+n:]
    else:
        at=text.rfind('}');new=text[:at].rstrip()+(',\n' if data else '\n')+'  '+json.dumps(key)+': '+json.dumps(value,ensure_ascii=False,indent=2)+'\n'+text[at:]
    if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Catalog changed during publication: '+str(path))
    path.write_text(new,encoding='utf8')
items=json.loads((D/'items.json').read_text(encoding='utf-8-sig'));item=copy.deepcopy(items['ue_m1911'])
item.update(id=ID,name='Pit Viper 2011',icon='Icons/'+ID+'.png',ue_icon='Icons/'+ID+'.png',weaponTypeTag='手枪',type='武器',
    desc='双排弹匣半自动手枪，使用9mm弹药。铜色枪管、黑色套筒与前端补偿结构保留原厂外形，装配15发弹匣。支持单持、双持和法杖副手。',
    stats=[{'name':'物理攻击','value':'22'},{'name':'弹匣容量','value':'15'}])
replace_key(D/'items.json',ID,item)
path=D/'gunsmith.json';text=path.read_text(encoding='utf-8-sig');data=json.loads(text)
defaults={
 'optic':('原厂机械瞄具','使用原厂照门与绿色准星。'),
 'muzzle':('原厂补偿结构','保持模型的前端补偿结构。'),
 'magazine':('原厂15发弹匣','使用本模型附带的15发双排弹匣。'),
 'reargrip':('原厂握柄','保持原厂聚合物握柄。'),
 'tactical':('无战术挂件','保持原厂外形。'),
 'trigger':('标准扳机','每次按下只发射一发，射击间隔150毫秒。')}
options={k:[{'id':'false','name':v[0],'description':v[1],'effects':[],'stats':{}}] for k,v in defaults.items()}
options['trigger'].append({'id':'pit_viper_lightweight_fast','name':'轻型快速扳机','description':'缩短合法点射间隔，保持半自动输入。','effects':[{'text':'射击间隔降低25%','benefit':1}],'stats':{'fire_interval_mult':.75}})
w={'id':ID,'model':'PitViper2011','name':'Pit Viper 2011','allowed':list(defaults),'options':options,
 'base':{'ammo_item_id':'ammo_9','mag_size':15,'ads_smooth':16.64295707529995,'recoil':65,'camera_shake':90,'fire_interval':.15,'reload_time':1.75,'empty_reload_time':2.25,'damage':22,'bullet_speed':375,'effective_range':50,'spread_mult':1.,'automatic':False},
 'traits':[{'icon':'mechanic','text':'半自动；9mm弹药；原厂15发双排弹匣'},{'icon':'special','text':'支持单持、双持及法杖副手，每只手独立射击与换弹'},{'icon':'neutral','text':'原厂机械瞄具与补偿结构；可改造快速扳机'}]}
old=next((x for x in data['weapons'] if x['id']==ID),None)
attachments=O.parent/'PitViper2011Attachments20261002'
receipt=attachments/'import_receipt.json'
if receipt.exists() and json.loads(receipt.read_text(encoding='utf8')).get('status')=='imported_and_saved':
    import importlib.util
    spec=importlib.util.spec_from_file_location('pit_viper_common_catalog',attachments/'publish_catalog.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    w=module.augment_weapon(w,data)
needle=json.dumps(ID if old else 'ue_m1911');pos=text.index(needle,text.index('"weapons"'));a=text.rfind('{',0,pos);_,n=json.JSONDecoder().raw_decode(text[a:]);b=a+n
new=text[:a]+json.dumps(w,ensure_ascii=False,indent=2)+text[b:] if old else text[:b]+',\n    '+json.dumps(w,ensure_ascii=False,indent=2)+text[b:]
if path.read_text(encoding='utf-8-sig')!=text:raise RuntimeError('Gunsmith changed during publication')
path.write_text(new,encoding='utf8')
(O/'catalog.json').write_text(json.dumps({'item':item,'weapon':w,'balance':'initial game values; not tested','geometry_options':'common attachments published' if 'pistol_grip_surface' in w else 'factory only; numeric trigger option'},ensure_ascii=False,indent=2),encoding='utf8')
print('PitViper2011 catalog published')
