from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'surface helpers','exec'))
report={}
for stock in ('stock','carbon'):
    v,f=geometry[stock];bv=BVHTree.FromPolygons(v,f,all_triangles=True)
    data={}
    for t in (.08,.125,.15,.25,.40,.46,.50,.55,.60,.65,.70,.75):
        row,_=compose(entry('skeleton_base','quick_melee'),t)
        root=rest['WPN_root']@row['WPN_root'].inverted();bindrow={n:root@m for n,m in row.items()}
        X=skin_points(bindrow,hand_ids[::4],True);dist=signed_distance(bv,X,True)
        data[str(t)]={'wrist':list(bindrow['hand_r'].translation),'middle':list(bindrow['middle_02_r'].translation),'min_mm':float(dist.min()),'inside_1mm':int((dist<-1).sum())}
    report[stock]=data
    for y in (-.14,-.10,-.07,-.04,-.01):
        pts=[p for p in v if abs(p.y-y)<.005]
        if pts:print('SECTION',stock,y,[(min(p[a] for p in pts),max(p[a] for p in pts)) for a in (0,2)],flush=True)
(O/'before_contact.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report),flush=True)
