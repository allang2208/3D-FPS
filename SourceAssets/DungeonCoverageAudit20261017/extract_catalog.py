from pathlib import Path
import struct,json,hashlib
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/DungeonCoverageAudit20261017'
p=root/'Content/__ExternalActors__/GameMaps/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH.uasset'
data=p.read_bytes();found=[]
for enc in ['utf-16-le','utf-8']:
 marker='{"version"'.encode(enc);offset=0
 while True:
  at=data.find(marker,offset)
  if at<0:break
  offset=at+len(marker)
  n=struct.unpack_from('<i',data,at-4)[0]
  if enc=='utf-16-le' and n<0:raw=data[at:at+(-n-1)*2]
  elif enc=='utf-8' and n>0:raw=data[at:at+n-1]
  else:continue
  try:c=json.loads(raw.decode(enc))
  except (ValueError,UnicodeDecodeError):continue
  if isinstance(c,dict) and 'modules' in c and 'facility_flow' in c:found.append((at,c))
if len(found)!=1:raise RuntimeError('Expected one saved production catalog, found '+str(len(found)))
at,c=found[0];(out/'saved-catalog.json').write_text(json.dumps(c,ensure_ascii=False),encoding='utf-8')
author=json.loads((root/'SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json').read_text(encoding='utf-8-sig'))
r={'generator_package':str(p),'sha256':hashlib.sha256(data).hexdigest(),'serialized_offset':at,'matches_author_catalog':c==author,'modules':len(c['modules']),'room_ids':c['room_ids'],'themed_routes':c['themed_routes'],'flow_keys':list(c['facility_flow'])}
(out/'catalog-source.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False)[:13000])
for k,v in c['facility_flow'].items():
 if k=='layout_bank':print('BANK',type(v).__name__, list(v) if isinstance(v,dict) else len(v));continue
 print('FLOW',k,json.dumps(v,ensure_ascii=False)[:2000])
for m in c['modules']:
 print('MODULE',m['id'],m.get('name'),m.get('role'), 'scene',len(m.get('scene_containers',[])),'runtime',len(m.get('runtime_actors',[])),'recipes',len(m.get('scene_recipes',[])),'selection',m.get('selection'))
