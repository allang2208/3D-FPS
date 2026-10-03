"""Add a five-round loading device without changing saved equipment choices."""
import json,re
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];path=P/'Content/ColdSteelData/gunsmith.json'
text=path.read_bytes().decode('utf-8-sig');mark=text.index('"id": "ue_rsh12"');start=text.rfind('{',0,mark)
weapon,length=json.JSONDecoder().raw_decode(text[start:]);original=text[start:start+length]
before=O/'BeforeCatalog';before.mkdir(exist_ok=True)
if not (before/'rsh12.json').exists():(before/'rsh12.json').write_text(original,encoding='utf8')
options=weapon['options']['reload_device'];options[:]=[p for p in options if p['id']!='rsh12_speedloader_5']
options.append(dict(id='rsh12_speedloader_5',name='五发快速装填器',
    description='五孔装填器，携带子弹后对孔压入、释放并抽离。每次换弹先退出弹巢内全部弹药，未击发余弹不返还背包；按可用弹药最多装入五发。',
    effects=[dict(text='普通与空仓换弹使用同一快速装填动作',benefit=1),dict(text='换弹丢弃弹巢内余弹，不返还背包',benefit=-1)],stats={}))
updated=json.dumps(weapon,ensure_ascii=False,indent=2)
path.write_bytes((text[:start]+updated+text[start+length:]).encode('utf8'))
(O/'catalog_receipt.json').write_text(json.dumps(dict(weapon='ue_rsh12',option='rsh12_speedloader_5',default_unchanged=True),indent=2))
