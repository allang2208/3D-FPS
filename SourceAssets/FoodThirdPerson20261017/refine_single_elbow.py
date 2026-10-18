from pathlib import Path
O=Path(__file__).parent
exec((O/'fit_elbow_helpers.py').read_text().split("frames=D['clips']")[0])
graph=json.loads((O/'graph_before.json').read_text());selected=[]
for row in graph['cases']:
    if row['case']!='unarmed' or row['food']=='roasted_large_lamb':continue
    for sample in row['samples']:
        if sample['weight']>.99:selected.append((row['food'],sample['time'],mat(np.array(sample['world']))))
result=[]
for param in [(u,c,t) for u in [.25,.3,.35] for c in [.35,.5] for t in [.75,.8,.825,.85]]:
    maximum=total=0;score=0.
    for food,time,w in selected:
        folds,penalty,_=skin_metrics(modify(w,'l',param),'l');maximum=max(maximum,folds);total+=folds;score+=penalty
    result.append({'params':param,'max':maximum,'sum':total,'score':float(score)})
result.sort(key=lambda a:(a['sum'],a['score']));(O/'single_elbow_refinement.json').write_text(json.dumps(result,indent=2));print(result[:8])
