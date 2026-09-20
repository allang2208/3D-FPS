"""Replace only the M16 weapon object; copy the current common option values."""
import json,copy,re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]/'Content/ColdSteelData/gunsmith.json'
text=P.read_text(encoding='utf-8-sig');catalog=json.loads(text)
m4=next(w for w in catalog['weapons'] if w['id']=='ue_m4a1');m16=next(w for w in catalog['weapons'] if w['id']=='ue_m16a2')
updated=copy.deepcopy(m16);slots=['optic','magazine','muzzle','underbarrel','stock','reargrip','tactical']
for slot in slots:
 existing=next((p for p in m16['options'].get(slot,[]) if p['id']=='false'),None)
 options=copy.deepcopy(m4['options'][slot])
 for i,part in enumerate(options):
  if part['id']=='false' and existing:options[i]=copy.deepcopy(existing)
  else:part['description']=part['description'].replace('M4A1','M16A2').replace('M4 ','M16A2 ')
 updated['options'][slot]=options
updated['allowed']=list(dict.fromkeys(m16['allowed']+slots))
# All gameplay multipliers, effects and names are copied together from M4;
# M16 base ballistics and its three-shot burst contract stay untouched.
for p in updated['options']['optic']:
 if p['id']!='false':p['description']+=' 通过 M16 提把专用座安装。'
for p in updated['options']['underbarrel']:
 if p['id']!='false':p['description']+=' 使用圆护木夹座与对应抓握动作。'
for p in updated['options']['magazine']:
 if p['id']=='ext_mag':p['description']='保留 M16 原厂金属弹匣接口，加长下部弹匣壳体。'
 if p['id']=='large_drum':p['description']='通用弹鼓采用 M16 弹匣井接口，使用独立取鼓、插入动作；空仓后拉机柄复进。'
needle=re.search(r'"id"\s*:\s*"ue_m16a2"',text);start=text.rfind('{',0,needle.start());old,end=json.JSONDecoder().raw_decode(text[start:])
if old['id']!='ue_m16a2':raise RuntimeError('M16 catalog object boundary')
replacement=json.dumps(updated,ensure_ascii=False,indent=2);replacement=replacement.replace('\n','\n    ')
P.write_text(text[:start]+replacement+text[start+end:],encoding='utf-8')
(O/'catalog.json').write_text(json.dumps({'weapon':updated,'common_reference':'ue_m4a1 current catalog','testing':'Not run'},ensure_ascii=False,indent=2),encoding='utf-8')
print('M16_COMMON_CATALOG_PUBLISHED',sum(len(updated['options'][s])-1 for s in slots))
