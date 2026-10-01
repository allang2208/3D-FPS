"""Add the two existing 416 options to QBZ without changing its defaults."""
import ast,json,copy
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];decoder=json.JSONDecoder()
source=O.parent/'HK416FactoryParts20261001/publish_catalog.py'
tree=ast.parse(source.read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef)],type_ignores=[]),str(source),'exec'))
path=P/'Content/ColdSteelData/gunsmith.json';old=path.read_text(encoding='utf-8-sig');start,end,weapons=fields(old,old.index('{'))['weapons']
donor=next(w for w in weapons if w['id']=='ue_m4a1')
parts={slot:copy.deepcopy(next(x for x in donor['options'][slot] if x['id']==key)) for slot,key in [('stock','hk416_stock'),('reargrip','hk416_reargrip')]}
parts['stock']['description']='带缓冲管与贴肩垫的伸缩枪托。';parts['reargrip']['description']='带防滑纹理的聚合物后握把。'
replacements=[];i=start+1
while True:
 while old[i].isspace() or old[i]==',':i+=1
 if old[i]==']':break
 weapon,n=decoder.raw_decode(old[i:]);wf=fields(old,i)
 if weapon['id'] in ('ue_m4a1','ue_m16a2','ue_hk416','ue_qbz191'):
  of=fields(old,wf['options'][0])
  for slot,part in parts.items():
   a,b,options=of[slot];found=False;updated=[]
   for option in options:
    if option['id']==part['id']:option=part;found=True
    updated.append(option)
   if not found:updated.insert(1,part)
   prefix=old[old.rfind('\n',0,a)+1:a];indent=len(prefix)-len(prefix.lstrip())
   replacements.append((a,b,formatted(updated,indent)))
 i+=n
write(path,old,replacements)
print('416_QBZ_CATALOG_PUBLISHED; factory defaults and installed loadouts retained')
