from pathlib import Path
exec(compile((Path(__file__).parent/'clearance.py').read_text().split("if __name__=='__main__':")[0],'current surfaces','exec'))
patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'));report={}
sample=hand_ids[::5]
for family in patch:
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default')
    magazine='mag10' if 'mag10' in family else 'mag5'
    stock_names=('stock','carbon','stock_native','carbon_native') if kind=='Default' else ('stock','carbon')
    trees={stock:assembly_tree(stock,kind,magazine) for stock in stock_names}
    result={'before':{},'after':{}}
    for label,clip in (('before',entry(family,'quick_melee')),('after',patch[family])):
        rows=[]
        for i in range(109):
            t=i/120;row,_=compose(clip,t);normalized=rest_row(row);pts=skin_points(normalized,sample,True)
            values={stock:signed_distance(bv,pts,True) for stock,bv in trees.items()}
            stats={stock:{'min_mm':float(v.min()),'inside_1mm':int((v<-1).sum())} for stock,v in values.items()}
            if any(v['min_mm']<-1 for v in stats.values()):rows.append({'time':t,**stats})
        result[label]=rows
    measures={}
    for label,clip in (('before',entry(family,'quick_melee')),('after',patch[family])):
        poses=[compose(clip,i/60)[0] for i in range(55)]
        measures[label]={'maximum_wrist_step_cm_at_60hz':max((poses[i]['hand_r'].translation-poses[i-1]['hand_r'].translation).length*100 for i in range(1,len(poses)))}
    result['motion']=measures
    report[family]=result
    print('SURFACE_REVIEW',family,{k:{'frames':len(v),'worst_mm':min((min(r[s]['min_mm'] for s in trees) for r in v),default=0)} for k,v in result.items() if k in ('before','after')},measures,flush=True)
(O/'contact_review.json').write_text(json.dumps(report,indent=2))
