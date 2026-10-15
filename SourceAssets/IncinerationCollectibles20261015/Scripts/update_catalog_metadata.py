"""Update only reward-authoring annotations, preserving the rest of each source catalog."""
from pathlib import Path
import json,re,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
modules={'ShoredBreach','AbandonedIncineratorHall','AbandonedFlueGasStation'}
results=[]
for rel in ('SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json','SourceAssets/IncineratorContainers20261003/Config/catalog.json'):
 p=PROJECT/rel
 if not p.exists():continue
 raw=p.read_text('utf-8-sig');match=re.search(r'"modules"\s*:\s*\[',raw)
 if not match:continue
 pos=match.end();decoder=json.JSONDecoder();edits=[]
 while True:
  while raw[pos] in ' \r\n\t,':pos+=1
  if raw[pos]==']':break
  item,end=decoder.raw_decode(raw,pos)
  if item.get('id') in modules and item.get('warehouse_containers',{}).get('rewards_deferred') is True:
   block=raw[pos:end];block=block.replace('"rewards_deferred": true','"rewards_deferred": false').replace('"rewards_deferred":true','"rewards_deferred":false')
   edits.append((pos,end,block));results.append(dict(source=rel,module=item['id']))
  pos=end
 if edits:
  dest=ROOT/'Before'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
  if not dest.exists():shutil.copy2(p,dest)
  for start,end,block in reversed(edits):raw=raw[:start]+block+raw[end:]
  p.write_text(raw,encoding='utf-8')
(ROOT/'Receipts/catalog-metadata.json').write_text(json.dumps(dict(updated=results,map_save_required=False,note='Authoring annotation only; runtime reads scene_search_loot.json'),ensure_ascii=False,indent=2),encoding='utf-8')
print('INCINERATION_CATALOG_ANNOTATIONS',len(results))
