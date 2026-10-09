import itertools
from pathlib import Path
O=Path(__file__).parent
exec(compile((O/'collision_core.py').read_text(),str(O/'collision_core.py'),'exec'))
data=json.loads((O.parent/'Super90ContactR8_20261008/Diagnostics/saved_assets.json').read_text())
def frame(key,up):
 d=data['framing'][key];root=s['uemat'](d['WPN_root']);x=(Vector(d['WPN_FrontSight'][:3])-Vector(d['WPN_RearSight'][:3])).normalized();z=root.to_quaternion()@Vector(up);y=z.cross(x).normalized();z=x.cross(y).normalized();return Matrix((x,y,z)).transposed().to_quaternion()
base=Quaternion((0,0,1),math.pi/2);cq=base@frame('M4',(0,0,1))@frame('Super90',(0,-1,0)).inverted();cp=Vector((6,7,-7))+base@Vector(data['framing']['M4']['hand_r'][:3])-cq@Vector(data['framing']['Super90']['hand_r'][:3]);view=Matrix(((0,1,0,0),(0,0,1,0),(-1,0,0,0),(0,0,0,1)))@Matrix.LocRotScale(cp/100,cq,Vector((1,-1,1)))
def project(p):
 v=view@p;return .5+v.y/(max(.03,-v.z)*2*math.tan(math.radians(75/2)))
coarse=[]
for roll,dx,dy,dz,pole in itertools.product((90,),(-.08,-.04,0.,.04),(-.04,.02,.06),(-.12,-.08,-.04,0.),range(-180,181,15)):
    s['handle_turn']=Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Rotation(math.radians(roll),4,'Z')
    s['support_fit']['left_loader_pole_degrees']=pole;s['support_fit']['left_shoulder_offset_m']=[dx,dy,dz]
    ps=[];sw=[];clear=[];height=[]
    for f in (87,100,114):
        s['twist_context'].clear();p,handle,tube=s['pose_sample'](f,7,False)
        ps.append(p);sw.append(wrist_swing(p,'l'));height.append(project(p['lowerarm_l'].translation))
        inv=tube.inverted();a=inv@p['lowerarm_l'].translation;b=inv@p['hand_l'].translation
        distances=[]
        for t in np.linspace(0,1,9):
            v=a.lerp(b,float(t));distances.append(math.hypot(v.x,v.z) if -.36<v.y<.01 else .2)
        clear.append(min(distances))
    score=sum(max(0,h-.10)**2 for h in height)*20000+sum(max(0,w-55)**2 for w in sw)*2+(dx*dx+dy*dy+dz*dz)*200
    coarse.append({'roll':roll,'pole':pole,'shift':[dx,dy,dz],'swings':sw,'heights':height,'axis_clearance':clear,'score':score})
coarse.sort(key=lambda r:r['score']);out=[]
for row in coarse[:60]:
    s['handle_turn']=Matrix.Rotation(math.pi/2,4,'Y')@Matrix.Rotation(math.radians(row['roll']),4,'Z')
    s['support_fit']['left_loader_pole_degrees']=row['pole'];s['support_fit']['left_shoulder_offset_m']=row['shift'];counts=[]
    for f in (87,100,114):
        s['twist_context'].clear();p=s['pose_sample'](f,7,False)[0];r=collision(p,sides=('left',));counts.append(r['left'])
    row['collision']=counts
    row['exact_score']=sum(c[k]['count'] for c in counts for k in c)*30+row['score'];out.append(row)
    print('SUPPORT_CANDIDATE',row,flush=True)
out.sort(key=lambda r:r['exact_score']);(O/'Diagnostics/elbow_view_search.json').write_text(json.dumps({'best':out[0],'shortlist':out,'coarse':coarse},indent=2))
print('SUPPORT_BEST',out[0],flush=True)
