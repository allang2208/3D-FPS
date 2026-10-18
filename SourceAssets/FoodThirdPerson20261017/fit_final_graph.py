from pathlib import Path
O=Path(__file__).parent
exec((O/'fit_elbow_helpers.py').read_text().split("frames=D['clips']")[0])
graph=json.loads((O/'graph_before.json').read_text());results={}
for side in ['l','r']:
    selected=[]
    for row in graph['cases']:
        if row['case']!='unarmed' or (side=='r' and row['food']!='roasted_large_lamb'):continue
        valid=[s for s in row['samples'] if s['weight']>.99]
        for j in np.linspace(0,len(valid)-1,7).astype(int):
            sample=valid[j];world=mat(np.array(sample['world']));selected.append((row['food'],sample['time'],world,skin_metrics(world,side)))
    candidates=[]
    for param in itertools.product([.1,.2,.3,.4],[.35,.5,.65,.8],[.65,.75,.875,1.]):
        counts=[];score=0.;maxmove=0.
        for food,time,w,old in selected:
            metrics=skin_metrics(modify(w,side,param),side);move=np.linalg.norm(metrics[2]-old[2],axis=1);maxmove=max(maxmove,float(move.max()));counts.append(metrics[0]);score+=metrics[1]+.000025*np.mean(move**2)
        candidates.append({'params':param,'folds':counts,'score':float(score),'max_vertex_move_cm':maxmove})
    candidates.sort(key=lambda c:c['score']);results[side]={'samples':[(f,t,o[0]) for f,t,w,o in selected],'best':candidates[:6]};print(side,'best',candidates[0],flush=True)
(O/'final_graph_fit.json').write_text(json.dumps(results,indent=2))
