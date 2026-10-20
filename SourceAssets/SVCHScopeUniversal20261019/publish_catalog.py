"""Add one shared optic choice to existing long-scope-compatible catalogs."""
import json,shutil
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];f=P/'Content/ColdSteelData/gunsmith.json'
old=f.read_bytes();text=old.decode('utf-8-sig');catalog=json.loads(text)
option={'id':'kv_scope_4x','name':'KV 战术瞄准镜','description':'长目镜筒、独立调节鼓与双脚导轨座，采用中心十字分划；瞄准时滚轮切换 1×、2×、4× 三档倍率。','effects':[{'text':'开镜耗时增加10%','benefit':-1},{'text':'枪械稳定性提高5%','benefit':1}],'stats':{'ads_percent':.1,'stability_mult':1.05}}
changes=[];supported=[];decoder=json.JSONDecoder();pos=text.index('[',text.index('"weapons"'))+1
for w in catalog['weapons']:
    start=text.index('{',pos);_,length=decoder.raw_decode(text[start:]);end=start+length;pos=end
    opts=w.get('options',{}).get('optic',[])
    if not any(o['id']=='lpvo_1_6x' for o in opts):continue
    supported.append(w['id'])
    if any(o['id']==option['id'] for o in opts):continue
    seg=text[start:end];a=start+seg.index('[',seg.index('"optic"',seg.index('"options"')));_,n=decoder.raw_decode(text[a:])
    # Retain all existing formatting and parallel edits outside this insertion.
    closing=a+n-1;tail=text.rfind('}',a,closing)+1
    block=json.dumps(option,ensure_ascii=False,indent=2).splitlines();indented='\n'.join('          '+line for line in block)
    changes.append((tail,',\n'+indented))
for at,addition in reversed(changes):text=text[:at]+addition+text[at:]
if changes:
    if f.read_bytes()!=old:raise RuntimeError('Catalog changed during publication; rerun from current source')
    (O/'gunsmith-before.json').write_bytes(old)
    with f.open('w',encoding='utf-8',newline='') as out:out.write(text)
icon=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms/optic_kv_scope_4x.png'
shutil.copy2(O/icon.name,icon)
(O/'catalog_receipt.json').write_text(json.dumps({'id':option['id'],'weapons':supported,'new_entries':len(changes),'icon':str(icon),'runtime_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('KV_SCOPE_CATALOG_SAVED',len(supported),flush=True)
