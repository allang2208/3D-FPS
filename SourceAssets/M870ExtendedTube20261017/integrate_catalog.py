"""Merge the M870 option and correct the earlier mis-targeted spread edit."""
import json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
raw=path.read_bytes();text=raw.decode('utf-8-sig');decoder=json.JSONDecoder()
option={'id':'m870_tube_extension','name':'弹仓延长管',
    'description':'深灰管身沿原厂弹仓向前延伸，收口套环与端盖延续原枪的简洁轮廓。',
    'effects':[{'text':'弹仓容量增加3发','benefit':1}], 'stats':{'mag_delta':3}}
pos=text.index('[',text.index('"weapons"'))+1;edits=[];receipt={}
while True:
    while text[pos].isspace() or text[pos]==',':pos+=1
    if text[pos]==']':break
    obj,end=decoder.raw_decode(text,pos);identity=obj['id'];changed=False
    if identity=='ue_m870':
        rows=obj['options'].setdefault('magazine',[])
        rows[:]=[r for r in rows if r['id']!=option['id']]+[option]
        if 'magazine' not in obj['allowed']:obj['allowed'].append('magazine')
        obj['base']['spread_mult']=1.2375;changed=True
        receipt['m870']={'base_capacity':obj['base']['mag_size'],'option':option,'spread_mult':1.2375}
    elif identity=='ue_super90' and obj['base']['spread_mult']==1.2375:
        # Our icon/spread task accidentally patched this matching numeric block.
        # Restore that one value only; current unrelated SUPER90 edits are retained.
        obj['base']['spread_mult']=2.25;changed=True
        receipt['super90_spread_correction']={'before':1.2375,'after':2.25}
    if changed:
        indent=text[text.rfind('\n',0,pos)+1:pos]
        edits.append((pos,end,json.dumps(obj,ensure_ascii=False,indent=2).replace('\n','\n'+indent)))
    pos=end
if 'm870' not in receipt:raise RuntimeError('M870 entry missing')
before=O/'Before/gunsmith.json';before.parent.mkdir(parents=True,exist_ok=True)
if not before.exists():before.write_bytes(raw)
for start,end,replacement in reversed(edits):text=text[:start]+replacement+text[end:]
if path.read_bytes()!=raw:raise RuntimeError('Catalog changed while merging')
path.write_text(text,encoding='utf-8',newline='\n')
(O/'catalog_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('M870_EXTENSION_CATALOG_SAVED')
