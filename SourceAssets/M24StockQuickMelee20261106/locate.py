from pathlib import Path
exec(compile((Path(__file__).parent/'clearance.py').read_text().split("if __name__=='__main__':")[0],'current surfaces','exec'))
patch=json.load(gzip.open(O/'quick_melee_patch.json.gz','rt'))
trees={k:BVHTree.FromPolygons(v,f,all_triangles=True) for k,(v,f) in geometry.items()}
report={}
for family in ('skeleton_base','skeleton_mag10'):
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default');result=[]
    for t in (.7083333333333334,):
        row,_=compose(patch[family],t);X=skin_points(rest_row(row),hand_ids,True)
        for key in ('stock','carbon','stock_native','carbon_native','grip_'+kind,'native_body','native_front'):
            bv=trees[key];d=signed_distance(bv,X,True)
            if d.min()<-.7:
                i=int(d.argmin());vid=int(hand_ids[i]);result.append({'time':t,'part':key,'depth_mm':float(-d[i]),'vertex':vid,'bone':RIGHT[int(W[vid].argmax())],'point':list(X[i])})
    report[family]=result
(O/'locate.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
