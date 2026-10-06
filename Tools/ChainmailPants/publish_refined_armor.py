"""Publish the saved V2 visuals without replacing item identity or attributes."""
import copy
import json
import re
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChainmailPants20261004/ArmorRefineV2'
D=P/'Content/ColdSteelData';ITEM='ue_chainmail_pants'

def replace_entry(raw,value):
    text=raw.decode('utf-8-sig')
    match=re.search(r'(?m)^(\s*)"'+ITEM+r'"\s*:\s*',text)
    start=match.end();_,length=json.JSONDecoder().raw_decode(text[start:])
    indent=len(match.group(1));dump=json.dumps(value,ensure_ascii=False,indent=2).splitlines()
    replacement=dump[0]+'\n'+'\n'.join(' '*indent+line for line in dump[1:])
    prefix=b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    return prefix+(text[:start]+replacement+text[start+length:]).encode('utf-8')

saved=json.loads((R/'saved_assets.json').read_text())
paths=[D/'items.json',D/'modular_outfits.json'];raw=[p.read_bytes() for p in paths]
catalog,config=[json.loads(x.decode('utf-8-sig')) for x in raw]
old_item=catalog[ITEM];old_recipe=config['items'][ITEM]
item=copy.deepcopy(old_item);recipe=copy.deepcopy(old_recipe)
item.update(world_mesh=saved['pickup'],world_material='',ue_equipment_icon_mesh=saved['icon'])
recipe['rig_meshes']['Jason']=saved['standard']
recipe.setdefault('shoe_fit_meshes',{}).setdefault('ue_boots',{})['Jason']=saved['boots']
recipe['appearance_family']='ChainmailPantsArmorRefineV2'
outputs=[replace_entry(raw[0],item),replace_entry(raw[1],recipe)]
if not (R/'before-publication.json').exists():
    (R/'before-publication.json').write_text(json.dumps(dict(item=old_item,recipe=old_recipe),ensure_ascii=False,indent=2),encoding='utf-8')
if any(p.read_bytes()!=before for p,before in zip(paths,raw)):raise RuntimeError('Catalog changed during publication; no writes made')
for path,output in zip(paths,outputs):path.write_bytes(output)
(R/'published.json').write_text(json.dumps(dict(item=item,recipe=recipe,saved=saved,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('CHAINMAIL_ARMOR_V2_PUBLISHED',flush=True)
