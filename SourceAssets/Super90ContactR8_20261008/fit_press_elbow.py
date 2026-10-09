from pathlib import Path
script=Path(__file__).with_name('fit_loader_elbow.py')
code=script.read_text().split('rows=[]')[0].replace("for key in ('weapon','props'):","for key in ('weapon',):")
exec(compile(code,str(script),'exec'))
rows=[]
for angle in range(-60,61,10):
    s['support_fit']['left_press_pole_degrees']=angle;s['pose_cache'].clear();counts=[];swings=[]
    for f in (139,146,158,165):
        p=s['pose'](f,7,True)[0];vs=deform(p)
        at=BVHTree.FromPolygons(vs,arm,all_triangles=True);bt=BVHTree.FromPolygons(vs,solid,all_triangles=True)
        counts.append(len({a for a,b in at.overlap(bt) if cuts([vs[i] for i in arm[a]],[vs[i] for i in solid[b]])}))
        ql=p['lowerarm_l'].to_quaternion();qh=p['hand_l'].to_quaternion();axis=(p['hand_l'].translation-p['lowerarm_l'].translation).normalized()
        neutral=ql@rest['lowerarm_l'].to_quaternion().inverted()@rest['hand_l'].to_quaternion();dq=qh@neutral.inverted()
        twist=2*math.atan2(Vector((dq.x,dq.y,dq.z)).dot(axis),dq.w);swing=(dq@Quaternion(axis,twist).inverted()).angle
        swings.append(math.degrees(min(swing,2*math.pi-swing)))
    row={'angle':angle,'counts':counts,'swing_degrees':swings,'score':sum(counts)*100+max(swings)**2+angle*angle*.02};rows.append(row)
best=min(rows,key=lambda r:r['score']);result=json.loads((O/'support_fit.json').read_text());result['left_press_pole_degrees']=best['angle'];result['left_press_clearance']={'selected':best,'candidates':rows}
(O/'support_fit.json').write_text(json.dumps(result,indent=2));print('PRESS_ELBOW',best)
