"""Update only the existing KV option; retain the stable saved-part ID."""
import json,re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2];f=P/'Content/ColdSteelData/gunsmith.json'
old=f.read_bytes();text=old.decode('utf-8-sig');decoder=json.JSONDecoder();changes=[]
for match in re.finditer(r'\{\s*"id"\s*:\s*"kv_scope_4x"',text):
    at=match.start();option,n=decoder.raw_decode(text[at:])
    option['description']='长目镜筒、独立调节鼓与双脚导轨座，采用中心十字分划；瞄准时滚轮切换 1×、2×、4× 三档倍率。'
    option['stats']['stability_mult']=1.05
    option['effects']=[x for x in option['effects'] if '枪械稳定性' not in x['text']]+[{'text':'枪械稳定性提高5%','benefit':1}]
    lines=json.dumps(option,ensure_ascii=False,indent=2).splitlines()
    changes.append((at,at+n,'\n'.join([lines[0]]+['          '+line for line in lines[1:]])))
for a,b,new in reversed(changes):text=text[:a]+new+text[b:]
if f.read_bytes()!=old:raise RuntimeError('Catalog changed during update; preserve parallel edits')
(O/'catalog-before.json').write_bytes(old)
with f.open('w',encoding='utf-8',newline='') as out:out.write(text)
(O/'catalog_receipt.json').write_text(json.dumps({'updated_options':len(changes),'magnifications':[1,2,4],'stability_mult':1.05,'ads_percent':.1,'runtime_tested':False},indent=2))
print('KV_ZOOM124_CATALOG_SAVED',len(changes),flush=True)
