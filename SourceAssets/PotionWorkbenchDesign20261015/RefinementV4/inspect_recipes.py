"""Requested static inspection of the installed eight recipes; does not run UE."""
import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
recipes=json.loads((PROJECT/'Content/ColdSteelData/alchemy-recipes.json').read_text(encoding='utf-8-sig'))['recipes']
items=json.loads((PROJECT/'Content/ColdSteelData/items.json').read_text(encoding='utf-8-sig'))
errors=[];rows=[];seen=set()
for r in recipes:
    name=r['id'];problems=[]
    if name in seen:problems.append('duplicate recipe id')
    seen.add(name)
    paid=Counter()
    for v in r['inputs']:
        paid[v['item']]+=v['count']
        if v['item'] not in items:problems.append('missing input '+v['item'])
    if r['output'] not in items:problems.append('missing output '+r['output'])
    if len(r['inputs'])>3:problems.append('more materials than available controls')
    poured=Counter();grind=set()
    for step in r['steps']:
        if step['action'] not in ('pour','grind','heat','stir','cool'):problems.append('unsupported operation')
        if step['amount']<=0 or step['minHeat']>step['maxHeat']:problems.append('invalid step range')
        if step['action']=='pour':poured[step['item']]+=step['amount']
        if step['action']=='grind':
            grind.add(step['item'])
            if poured[step['item']]>0:problems.append('grinding required after pouring that material')
        if step['action']=='stir' and step['direction'] not in (-1,1):problems.append('invalid stirring direction')
        if step['action']=='heat' and (step['minHeat']>94 or step['maxHeat']<20):problems.append('unreachable temperature')
    if poured!=paid:problems.append('paid and poured quantities differ')
    if r['steps'][-1]['action']!='cool' or r['steps'][-1]['maxHeat']>40:problems.append('bottling cooling gate missing')
    if r['count']<1 or r['bonus']<0:problems.append('invalid output count')
    errors.extend(name+': '+p for p in problems)
    rows.append({'id':name,'materials':dict(paid),'steps':len(r['steps']),'book_spreads':max(1,(len(r['steps'])+8)//6),
        'finished_refund':{k:v//2 for k,v in paid.items()},'errors':problems})
report={'recipes':rows,'errors':errors,'scope':'installed recipe/item data, operation reachability and paid quantity correspondence','runtime_tested':False}
(ROOT/'recipe-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'recipes':len(rows),'errors':errors},ensure_ascii=False))
if errors:raise SystemExit(1)
