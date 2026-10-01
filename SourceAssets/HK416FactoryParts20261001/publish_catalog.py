"""Scoped publication of 416 furniture for M4/M16/HK416/QBZ191 and HK416 defaults."""
import json,re,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];decoder=json.JSONDecoder()
def fields(text,start):
 result={};i=start+1
 while True:
  while text[i].isspace() or text[i]==',':i+=1
  if text[i]=='}':return result
  key,n=decoder.raw_decode(text[i:]);i+=n
  while text[i].isspace() or text[i]==':':i+=1
  value,n=decoder.raw_decode(text[i:]);result[key]=(i,i+n,value);i+=n
def formatted(value,indent):return json.dumps(value,ensure_ascii=False,indent=2).replace('\n','\n'+' '*indent)
def write(path,old,replacements):
 text=old
 for start,end,new in sorted(replacements,reverse=True):text=text[:start]+new+text[end:]
 if path.read_text(encoding='utf-8-sig')!=old:raise RuntimeError('Concurrent catalog change: '+str(path))
 path.write_text(text,encoding='utf-8')
parts={
 'stock':{'id':'hk416_stock','name':'416后托','description':'带缓冲管与贴肩垫的伸缩枪托。'},
 'reargrip':{'id':'hk416_reargrip','name':'416后握','description':'带防滑纹理的聚合物后握把。'}
}
for option in parts.values():
 option['effects']=[{'text':'后坐力降低10%','benefit':1},{'text':'腰射随机散布减少10%','benefit':1}]
 option['stats']={'recoil_mult':.9,'hip_spread_mult':.9}
defaults={slot:option['id'] for slot,option in parts.items()}
path=P/'Content/ColdSteelData/gunsmith.json';old=path.read_text(encoding='utf-8-sig');replacements=[]
start,end,weapons=fields(old,old.index('{'))['weapons'];i=start+1
while True:
 while old[i].isspace() or old[i]==',':i+=1
 if old[i]==']':break
 weapon,n=decoder.raw_decode(old[i:]);wf=fields(old,i)
 if weapon['id'] in ('ue_m4a1','ue_m16a2','ue_hk416','ue_qbz191'):
  of=fields(old,wf['options'][0])
  for slot,option in parts.items():
   a,b,options=of[slot];updated=[]
   for existing in options:
    if existing['id']==option['id']:continue
    if weapon['id']=='ue_hk416' and existing['id']=='false':updated.append(option)
    else:updated.append(existing)
   if not any(x['id']==option['id'] for x in updated):updated.insert(1,option)
   indent=len(old[old.rfind('\n',0,a)+1:a])-len(old[old.rfind('\n',0,a)+1:a].lstrip())
   replacements.append((a,b,formatted(updated,indent)))
  if weapon['id']=='ue_hk416':
   if 'default_parts' in wf:
    a,b,_=wf['default_parts'];replacements.append((a,b,formatted(defaults,6)))
   else:
    last=max(v[1] for v in wf.values());replacements.append((last,last,',\n      "default_parts": '+formatted(defaults,6)))
 i+=n
write(path,old,replacements)
path=P/'Content/ColdSteelData/items.json';old=path.read_text(encoding='utf-8-sig');a,b,_=fields(old,old.index('{'))['ue_hk416'];item=fields(old,a)
if 'gunsmith_parts' in item:
 a,b,existing=item['gunsmith_parts'];existing.update(defaults);replacements=[(a,b,formatted(existing,4))]
else:
 last=max(v[1] for v in item.values());replacements=[(last,last,',\n    "gunsmith_parts": '+formatted(defaults,4))]
write(path,old,replacements)
for folder in ('','FramedFirearms'):
 root=P/'Content/ColdSteelData/AttachmentIcons20260913'/folder
 for slot,option in parts.items():shutil.copyfile(root/('ue_hk416_'+slot+'_false.png'),root/(slot+'_'+option['id']+'.png'))
print('416_AR_CATALOG_PUBLISHED: M4/M16/QBZ191 optional; HK416 named defaults; existing overrides retained')
