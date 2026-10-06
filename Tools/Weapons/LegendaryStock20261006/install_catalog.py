"""Install this stock only on its fitted hosts, preserving unrelated JSON bytes."""
import json,re
from pathlib import Path
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/LegendaryStock20261006';I=O/'Integration'
definition=json.loads((O/'attachment-definition.json').read_text(encoding='utf-8'))
option=definition['option'];ident=option['id']
families={'ue_m4a1':'M4','ue_akm':'AKM','ue_qbz191':'QBZ191','ue_m16a2':'M16',
 'ue_a762':'A762','ue_svd':'SVD','ue_pkm_lowpoly':'PKM','ue_lmg201':'LMG201','ue_hk416':'HK416'}
path=P/'Content/ColdSteelData/gunsmith.json';raw=path.read_bytes();text=raw.decode('utf-8-sig');decoder=json.JSONDecoder()
start=re.search(r'"weapons"\s*:\s*\[',text).end();offset=start;edits=[];installed=[]
def skip(s,pos):
 while pos<len(s) and s[pos].isspace():pos+=1
 return pos
while True:
 offset=skip(text,offset)
 if text[offset]==']':break
 if text[offset]==',':offset=skip(text,offset+1)
 weapon,end=decoder.raw_decode(text,offset)
 if weapon['id'] in families:
  local=text[offset:end];found=re.search(r'"stock"\s*:\s*\[',local)
  if found is None:raise RuntimeError('Fitted host has no stock options: '+weapon['id'])
  array_start=offset+found.end()-1;items,array_end=decoder.raw_decode(text,array_start)
  current=next((x for x in items if x['id']==ident),None)
  block=json.dumps(option,ensure_ascii=False,indent=2)
  block='\r\n'.join('          '+line for line in block.splitlines())
  if current is None:
   insert=array_end-1
   while text[insert-1].isspace():insert-=1
   edits.append((insert,insert,',\r\n'+block));installed.append(weapon['id'])
  else:
   item_pos=skip(text,array_start+1)
   while item_pos<array_end:
    item,item_end=decoder.raw_decode(text,item_pos)
    if item['id']==ident:
     edits.append((item_pos,item_end,block.lstrip()));installed.append(weapon['id']);break
    item_pos=skip(text,item_end)
    if text[item_pos]==',':item_pos=skip(text,item_pos+1)
    else:break
 offset=end
if set(installed)!=set(families):raise RuntimeError('Not all fitted hosts were found in the current catalog')
for start,end,block in sorted(edits,reverse=True):text=text[:start]+block+text[end:]
backup=I/'Before';backup.mkdir(parents=True,exist_ok=True)
if not (backup/'gunsmith.json').exists():(backup/'gunsmith.json').write_bytes(raw)
if path.read_bytes()!=raw:raise RuntimeError('Catalog changed during preparation; preserve concurrent changes and rerun')
path.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'))
definition['integration'].update(status='catalog_installed_for_nine_fitted_hosts',runtime_enabled=True,
 supported_definitions=list(families),game_tested=False,
 compatibility='Nine replaceable-stock firearm hosts have fitted models. Pistols and integral-stock hosts are excluded.',
 catalog_install='Installed in the nine fitted weapons stock options; common_options is unchanged.',
 fitted_models=str(I/'fitted-models.json'),
 icon='/Game/Weapons/LegendaryStock20261006/Icons/T_TacticalStockIcon')
(O/'attachment-definition.json').write_text(json.dumps(definition,ensure_ascii=False,indent=2),encoding='utf-8')
authoring_path=O/'authoring.json'
authoring=json.loads(authoring_path.read_text(encoding='utf-8'))
authoring.update(stage=definition['integration']['status'],host_fitted=True,runtime_integrated=True,
 fitted_models=str(I/'fitted-models.json'),supported_definitions=list(families),game_tested=False)
authoring_path.write_text(json.dumps(authoring,ensure_ascii=False,indent=2),encoding='utf-8')
(I/'catalog-install-receipt.json').write_text(json.dumps({'id':ident,'weapons':installed,'stats':option['stats'],
 'common_options_modified':False,'game_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('TACTICAL_STOCK_CATALOG_INSTALLED '+json.dumps(installed))
