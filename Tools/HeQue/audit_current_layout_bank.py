"""Independent connectivity/occupancy/order checks for today's seven-slot routes."""
import hashlib
import itertools
import json
from collections import Counter, deque
from pathlib import Path

project=Path('D:/FPS3D/FPSGAME')
root=project/'SourceAssets/HeQueBoss20261014/DungeonE2E/Records'
reports=json.loads((project/'Saved/DungeonRoutingFix20260927/heque-current-bank-120-20261015.json').read_text(encoding='utf-8-sig'))
catalog=json.loads((root/'catalog-before.json').read_text(encoding='utf-8-sig'))
modules={m['id']:m for m in catalog['modules']}
themes={t['id']:t['sequence'] for t in catalog['themed_routes']['routes']}
sequences={tuple(s):t for t,s in themes.items()}
transitions=catalog['themed_routes'].get('inter_theme_transition_count',0)

def mates(a,b):
    return (all(abs(x-y)<1.001 for x,y in zip(a['position'],b['position'])) and
            sum(x*y for x,y in zip(a['normal'],b['normal']))<-.999 and
            abs(a['width']-b['width'])<1 and abs(a['height']-b['height'])<1)

def reachable(graph,start,allowed=lambda _:True):
    seen={start};todo=deque([start])
    while todo:
        for other in graph[todo.popleft()]:
            if other not in seen and allowed(other):seen.add(other);todo.append(other)
    return seen

results=[]
for report in reports:
    errors=[];pieces=report['pieces'];pairings=[]
    if not report['success']:
        results.append(dict(case=report.get('case_id'),passed=False,errors=[report['failure']]))
        continue
    expected=6+transitions
    if report['counts']!=[0,expected,expected,expected]:errors.append('Wrong mandatory room counts')
    missions={p['mission_id']:i for i,p in enumerate(pieces) if p['mission_id']}
    if len(missions)!=sum(bool(p['mission_id']) for p in pieces):errors.append('Duplicate mission identities')
    for route in range(1,4):
        ids=[missions.get(f'Route{route}.{slot}') for slot in range(expected)]
        if None in ids:errors.append(f'Route{route}: missing room');continue
        rooms=[pieces[i] for i in ids]
        pair=[sequences.get(tuple(p['module'] for p in rooms[:3])),sequences.get(tuple(p['module'] for p in rooms[3+transitions:6+transitions]))]
        if None in pair:errors.append(f'Route{route}: broken/reversed theme');continue
        pairings.append(pair)
        for p in rooms:
            if any(abs(s-1)>.0001 for s in p['scale']):errors.append('Scaled room')
        for p in rooms[3:3+transitions]:
            if modules[p['module']].get('family_id',p['module']) not in catalog['themed_routes']['transition_families']:errors.append('Invalid transition room')
    if Counter(t for pair in pairings for t in pair)!=Counter(themes.keys()):errors.append('Missing/duplicate theme')
    if Counter(map(tuple,pairings))!=Counter(map(tuple,report['drawn_theme_pairs'].values())):errors.append('Drawn pair changed')
    for key in ('entry','reception','fork.late','confluence','archive','boss'):
        if key not in missions:errors.append('Missing '+key)
    ports=[(-1,report['start'])]+[(i,p) for i,piece in enumerate(pieces) for p in piece['ports']]
    graph={i:set() for i in range(-1,len(pieces))};shared={}
    for idx,(owner,port) in enumerate(ports):
        matches=[(other,remote) for j,(other,remote) in enumerate(ports) if idx!=j and owner!=other and mates(port,remote)]
        if len(matches)!=1:errors.append(f'Port {owner}/{port.get("index","start")} has {len(matches)} mates')
        for other,remote in matches:
            graph[owner].add(other)
            if owner>=0 and other>=0:shared.setdefault(tuple(sorted((owner,other))),[]).append(port)
    if len(reachable(graph,-1))!=len(pieces)+1:errors.append('Disconnected graph')
    for edge in report['mission_edges']:
        if edge['optional'] or edge['to']=='reward.final':continue
        a,b=missions.get(edge['from']),missions.get(edge['to'])
        if a is None or b is None or b not in reachable(graph,a,lambda i:i==b or (i>=0 and not pieces[i]['mission_id'])):errors.append('Mission edge disconnected: '+edge['from']+' -> '+edge['to'])
    for i,a in enumerate(pieces):
        for j,b in enumerate(pieces[:i]):
            for ca,cb in itertools.product(a['cells'],b['cells']):
                low=[max(x,y) for x,y in zip(ca['min'],cb['min'])];high=[min(x,y) for x,y in zip(ca['max'],cb['max'])]
                if any(hi-lo<=8.001 for lo,hi in zip(low,high)):continue
                legal=False
                depth=max(45 if 'Treasure' in (a['module'],b['module']) else 30,modules[a['module']].get('port_seam_depth_cm',30),modules[b['module']].get('port_seam_depth_cm',30))+.101
                for port in shared.get((j,i),[]):
                    axis=0 if abs(port['normal'][0])>.5 else 1;side=1-axis;at=port['position'];width=port['width']/2+30.001
                    if low[axis]>=at[axis]-depth and high[axis]<=at[axis]+depth and low[side]>=at[side]-width and high[side]<=at[side]+width:legal=True;break
                if not legal:errors.append(f'Illegal overlap {i}/{a["module"]} {j}/{b["module"]}');break
    if report['corridor_cm']>report['corridor_budget_cm']+.1:errors.append('Global corridor budget exceeded')
    for detail in report['route_length_details']:
        if detail['link_walk_cm']>detail['link_budget_cm']+.1:errors.append('Route corridor budget exceeded')
    results.append(dict(case=report.get('case_id'),seed=report['seed'],passed=not errors,errors=errors,pairs=pairings,pieces=len(pieces)))
summary=dict(total=len(results),passed=sum(x['passed'] for x in results),pairings=len({tuple(sorted(map(tuple,x.get('pairs',[])))) for x in results}),results=results)
(root/'layout-bank-independent.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k!='results'}))
for row in results:
    if not row['passed']:print(row['case'],row['errors'][:3])
raise SystemExit(0 if summary['total']==120 and summary['passed']==120 and summary['pairings']==120 else 1)
