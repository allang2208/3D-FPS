from pathlib import Path
import json
p=Path('SourceAssets/DungeonFacilityFlow20261007/Config/catalog.json');c=json.loads(p.read_text('utf8'))
r={'root_keys':list(c),'flow_keys':list(c['facility_flow'])}
m=next(m for m in c['modules'] if m['id']=='FacilityTransit');r['module_keys']=list(m)
r['hall_parts']=[p for p in m['parts'] if any(k in p['mesh'] for k in ['ArrivalFrame','Approach','Maintenance','PanelIndicators','ServiceBench','Signs','Hangers'])]
for key in c:
 if 'kit' in key or 'portal' in key:r[key]=c[key]
for key in c['facility_flow']:
 if 'kit' in key or 'portal' in key:r[key]=c['facility_flow'][key]
Path('SourceAssets/FacilityDetailRepair20261010/Receipts/source-scope.json').write_text(json.dumps(r,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in r.items() if k.endswith('keys')},indent=2))
print('Hall selected parts',len(r['hall_parts']))
for p in r['hall_parts']:print(p['mesh'],p['position'])
