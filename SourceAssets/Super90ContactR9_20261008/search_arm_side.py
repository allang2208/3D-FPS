import itertools
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
coarse=[]
for roll,side,standoff,dx,dy,dz,pole in itertools.product((60,90,120),(-.08,-.06,.06,.08),(-.03,-.05,-.07),(-.04,0.,.04),(.06,),(-.04,0.),(-30,0,30)):
    s['PLUNGER_SIDE']=side
    s['PLUNGER_STANDOFF']=standoff
    s['handle_turn']=Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Rotation(math.radians(roll),4,'Z')
    s['support_fit']['left_loader_pole_degrees']=pole;s['support_fit']['left_shoulder_offset_m']=[dx,dy,dz]
    ps=[];sw=[];clear=[]
    for f in (87,100,114):
        s['twist_context'].clear();p,handle,tube=s['pose_sample'](f,7,False)
        ps.append(p);sw.append(wrist_swing(p,'l'))
        inv=tube.inverted();a=inv@p['lowerarm_l'].translation;b=inv@p['hand_l'].translation
        distances=[]
        for t in np.linspace(0,1,9):
            v=a.lerp(b,float(t));distances.append(math.hypot(v.x,v.z) if -.36<v.y<.01 else .2)
        clear.append(min(distances))
    score=max(0,max(sw)-45)**2*50+sum(max(0,.043-c)**2 for c in clear)*2e6+(dx*dx+dy*dy+dz*dz)*300
    coarse.append({'roll':roll,'side':side,'standoff':standoff,'pole':pole,'shift':[dx,dy,dz],'swings':sw,'axis_clearance':clear,'score':score})
coarse.sort(key=lambda r:r['score']);out=[]
for row in coarse[:50]:
    s['PLUNGER_STANDOFF']=row['standoff'];s['PLUNGER_SIDE']=row['side']
    s['handle_turn']=Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Rotation(math.radians(row['roll']),4,'Z')
    s['support_fit']['left_loader_pole_degrees']=row['pole'];s['support_fit']['left_shoulder_offset_m']=row['shift'];counts=[]
    for f in (87,100,114):
        s['twist_context'].clear();p=s['pose_sample'](f,7,False)[0];r=collision(p,sides=('left',));counts.append(r['left'])
    row['collision']=counts
    row['exact_score']=sum(c[k]['count'] for c in counts for k in c)*10+row['score'];out.append(row)
    print('SUPPORT_CANDIDATE',row,flush=True)
out.sort(key=lambda r:r['exact_score']);(O/'Diagnostics/arm_side_search.json').write_text(json.dumps({'best':out[0],'shortlist':out,'coarse':coarse},indent=2))
print('SUPPORT_BEST',out[0],flush=True)
