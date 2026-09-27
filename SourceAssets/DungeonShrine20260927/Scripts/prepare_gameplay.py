"""Publish shrine status-card definitions from the same authored blessing catalog."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parents[1]
statues=json.loads((ROOT/'Config/shrine.json').read_text(encoding='utf-8'))['statues']
path=PROJECT/'Content/ColdSteelData/status_effects.json'
data=json.loads(path.read_text(encoding='utf-8-sig'))
ids={s['buff_id'] for s in statues}
data['effects']=[e for e in data['effects'] if e['type'] not in ids]
data['effects'].extend(dict(type=s['buff_id'],name=s['blessing_name'],icon=s['icon'],color=s['color'],
    description=s['description']) for s in statues)
path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('SHRINE_STATUS_DEFINITIONS_SAVED',len(statues))
