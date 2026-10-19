"""Promote the existing 12K exclusive parts into their actual option arrays.

The option object is preserved, including its gameplay values and text. Only the
Saiga magazine/stock arrays are rewritten; the surrounding catalog is retained.
"""
import json,re,shutil
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/Saiga12KDrumCatalogFix20261018'
f=P/'Content/ColdSteelData/gunsmith.json';text=f.read_text(encoding='utf-8-sig');original=text;decoder=json.JSONDecoder()
# Anchor to the weapon object, rather than the first effects array after an ID.
weapon_id=text.index('"id": "ue_saiga12k"');start=text.rfind('{',0,weapon_id)
weapon,end=decoder.raw_decode(text,start);segment=text[start:end]
changed=[]
for slot,part in [('magazine','saiga12k_drum20'),('stock','saiga12k_bump_stock')]:
 options=weapon['options'][slot]
 existing=next((o for o in options if o.get('id')==part),None)
 nested=[]
 for option in options:
  effects=option.get('effects',[])
  nested.extend(e for e in effects if e.get('id')==part)
  option['effects']=[e for e in effects if e.get('id')!=part]
 if existing is None:
  if len(nested)!=1:raise RuntimeError('Expected one authored option for '+part)
  existing=nested[0];options.append(existing)
 if nested:
  changed.append({'slot':slot,'id':part,'name':existing['name'],'stats':existing['stats'],'promoted_from_effects':True})
 else:continue
 match=re.search(r'(?m)^( +)"'+re.escape(slot)+r'"\s*:\s*',segment)
 if not match:raise RuntimeError('Missing option array '+slot)
 array_start=match.end();previous,array_end=decoder.raw_decode(segment,array_start)
 indent=match.group(1);lines=json.dumps(options,ensure_ascii=False,indent=2).splitlines()
 replacement=lines[0]+''.join('\n'+indent+line for line in lines[1:])
 segment=segment[:array_start]+replacement+segment[array_end:]
# The same ID is now selectable, normalized, saved, and passed to the existing
# Saiga model/reload and legendary/special tier branches.
if changed:
 backup=O/'Before/gunsmith.json'
 if not backup.exists():shutil.copy2(f,backup)
 f.write_text(text[:start]+segment+text[end:],encoding='utf8')
receipt={'complete':True,'catalog':'Content/ColdSteelData/gunsmith.json','changed':changed,'runtime_tested':False,'requires_native_build':False,'reload':'Catalog is read when GunsmithSystem initializes; next game start loads the corrected options.'}
(O/'Receipts/catalog-save.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(receipt,ensure_ascii=False))
