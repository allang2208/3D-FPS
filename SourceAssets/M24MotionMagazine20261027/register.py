import json,copy
from pathlib import Path
O=Path(__file__).resolve().parent;P=O.parents[1]
receipt=json.loads((O/'install_receipt.json').read_text())
if not receipt['complete']:raise RuntimeError('Complete the actual asset import first')
path=P/'Content/ColdSteelData/gunsmith.json';raw=path.read_bytes();text=raw.decode('utf-8-sig')
start=text.rfind('{',0,text.index('"id": "ue_m24"'))
row,end=json.JSONDecoder().raw_decode(text[start:]);end+=start
if 'magazine' not in row['allowed']:row['allowed'].append('magazine')
row['base']['mag_size']=5
row['options']['magazine']=[
 {'id':'false','name':'5发原厂弹匣','description':'紧凑短壳体与独立底板，保留原装插接段。','effects':[],'stats':{},'special_effects':[]},
 {'id':'m24_extended_mag_10','name':'10发扩容弹匣','description':'加长金属壳体与下移底板，沿用原装插接段。',
  'effects':[{'text':'弹匣容量增加5发','benefit':1}],'stats':{'mag_delta':5},'special_effects':[]}]
row['default_parts']['magazine']='false'
encoded=json.dumps(row,ensure_ascii=False,indent=2).splitlines();replacement=encoded[0]+'\n'+'\n'.join('    '+line for line in encoded[1:])
new=text[:start]+replacement+text[end:]
backup=O/'before_gunsmith.json'
if not backup.exists():backup.write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Gunsmith catalog changed concurrently; rerun registration')
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+new.encode('utf-8'))
path=P/'Content/ColdSteelData/modular_outfits.json';raw=path.read_bytes();data=json.loads(raw)
sources=('/Game/Weapons/M24/Surface20261027/SK_M24_SurfaceV9.SK_M24_SurfaceV9','/Game/Weapons/M24/Hold20261027/SK_M24_HoldV9.SK_M24_HoldV9')
def register(node):
 if not isinstance(node,dict):return False
 for source in sources:
  if source in node:
   profile=copy.deepcopy(node[source]);profile['hide_source_materials']=receipt['arm_materials'];node[receipt['mesh']]=profile;return True
 return any(register(v) for v in node.values())
if not register(data):raise RuntimeError('Source M24 outfit profile missing')
backup=O/'before_modular_outfits.json'
if not backup.exists():backup.write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Outfit catalog changed concurrently; rerun registration')
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(O/'registration_receipt.json').write_text(json.dumps({'weapon':'ue_m24','default_capacity':5,'extended_capacity':10,'option':'m24_extended_mag_10','mesh':receipt['mesh'],'outfit_registered':True,'runtime_tested':False},indent=2))
print('M24_CATALOG_REGISTERED')
