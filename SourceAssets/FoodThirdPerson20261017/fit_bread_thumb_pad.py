from pathlib import Path
O=Path(__file__).parent
exec((O/'fit_thumb_hinge.py').read_text().split('for row in graph')[0])
row=next(r for r in graph['cases'] if r['food']=='bread' and r['case']=='unarmed');sample=min(row['samples'],key=lambda a:abs(a['time']-1.0));world=mat(np.array(sample['world']));b=ix['thumb_01_side_inn_l'];p=parents[b]
candidates=[]
for offset in itertools.product(np.arange(-.4,.401,.1),repeat=3):
    result=world.copy();result[b,:3,3]+=world[p,:3,:3]@np.array(offset);folds,penalty,v=skin_metrics(result,'l');move=np.linalg.norm(offset)
    candidates.append({'offset_cm':offset,'folds':folds,'score':float(penalty+.00003*move**2),'length':move})
candidates.sort(key=lambda a:(a['folds'],a['score']));print(candidates[:8])
(O/'bread_thumb_pad_fit.json').write_text(json.dumps(candidates[:8],indent=2))
