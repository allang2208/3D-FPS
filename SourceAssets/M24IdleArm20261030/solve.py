from pathlib import Path
exec(compile((Path(__file__).parent/'inspect.py').read_text().split("\nif __name__=='__main__':")[0],'setup','exec'))
from itertools import product
from collections import Counter
u,l,h='upperarm_l','lowerarm_l','hand_l'
base=pose('idle',0)[0];root=base['WPN_root']@rest['WPN_root'].inverted()
RU=rest[l].translation-rest[u].translation;RL=rest[h].translation-rest[l].translation
A,B=RU.length,RL.length;RN=RU.cross(RL).normalized();ax=rest[l].to_quaternion().inverted()@RL.normalized()
hand_rel=rest[l].to_quaternion().inverted()@rest[h].to_quaternion()
grip_clearance=Vector((-.006,0,-.012))
grip_deltas=json.loads((O/'grip_deltas.json').read_text()) if (O/'grip_deltas.json').exists() else {}
edges=Counter(tuple(sorted((p.vertices[i],p.vertices[(i+1)%len(p.vertices)]))) for p in skin.data.polygons for i in range(len(p.vertices)))
boundary={i for e,count in edges.items() if count==1 for i in e}
opening=[rest[u].inverted()@skin.data.vertices[i].co for i in boundary if (skin.data.vertices[i].co-rest[u].translation).length<.14]
def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x).normalized(),z)).transposed()
def solve(row,params):
    shift=Vector(params[:3]);phi=params[3];rt=row['WPN_root']@rest['WPN_root'].inverted();S=row[u].translation+rt.to_3x3()@shift;H=row[h].translation+rt.to_3x3()@(Vector((0,params[4],0))+grip_clearance);V=H-S;d=V.length;axis=V.normalized()
    if d>=A+B or d<=abs(A-B):return None
    mid=S+axis*((A*A-B*B+d*d)/(2*d));ref=row[l].translation-mid;ref=(ref-axis*ref.dot(axis)).normalized();E=mid+Quaternion(axis,phi)@ref*math.sqrt(max(0,A*A-(mid-S).length_squared))
    U=E-S;L=H-E;N=U.cross(L).normalized();uq=(frame(U,N)@frame(RU,RN).transposed()).to_quaternion()@rest[u].to_quaternion();lq=(frame(L,N)@frame(RL,RN).transposed()).to_quaternion()@rest[l].to_quaternion()
    rel=lq.inverted()@row[h].to_quaternion()@hand_rel.inverted()
    if rel.w<0:rel=-rel
    roll=2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(ax),rel.w)
    wrist=angle(L,row['middle_01_l'].translation-row[h].translation);bend=angle(U,L)
    return S,E,uq,lq,roll,wrist,bend
def cost(p):
    v=solve(base,p)
    if v is None:return 1e9
    S,E,uq,lq,roll,wrist,bend=v
    M=C@Matrix.LocRotScale(S,uq,Vector((1,1,1)))
    exposure=0.
    for point in opening:
        q=M@point
        if q.x>0 and abs(q.y)<q.x*math.tan(math.radians(37.5))*16/9:
            exposure=max(exposure,max(0,q.z+q.x*math.tan(math.radians(37.5))+1.))
    return (wrist/10)**2+max(0,wrist-18)**2*.3+max(0,abs(math.degrees(roll))-85)**2*.025+((bend-55)/12)**2+max(0,45-bend)**2*.3+Vector(p[:3]).length_squared*1000+(p[3]/math.radians(45))**2*.3+p[4]**2*300+exposure**2*15
params=min(([x,y,z,math.radians(a),d] for x,y,z,a,d in product((-.10,-.05,0,.05,.10),(-.03,0,.03),(-.04,0,.04),range(-45,46,15),(0,-.03,-.06))),key=cost)
for step in (.008,.004,.002,.001):
    for _ in range(20):
        options=[params]
        for k in range(5):
            for sign in (-1,1):
                p=list(params);p[k]+=sign*(step*100 if k==3 else step)
                limit=(.10,.05,.06)[k] if k<3 else 0
                p[k]=max(-limit,min(limit,p[k])) if k<3 else max(-math.pi/3,min(math.pi/3,p[k])) if k==3 else max(-.07,min(0,p[k]));options.append(p)
        best=min(options,key=cost)
        if best==params:break
        params=best
def apply(row,params):
    S,E,uq,lq,roll,wrist,bend=solve(row,params);out=clone(row);Um=Matrix.LocRotScale(S,uq,Vector((1,1,1)));Lm=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
    out['clavicle_l']=Um@rest[u].inverted()@rest['clavicle_l']
    for n in names:
        if under(n,h):
            out[n].translation+=(row['WPN_root']@rest['WPN_root'].inverted()).to_3x3()@(Vector((0,params[4],0))+grip_clearance);continue
        if under(n,l):out[n]=Lm@rest[l].inverted()@rest[n]
        elif under(n,u):out[n]=Um@rest[u].inverted()@rest[n]
    for j,w in ((1,1.),(2,.5)):
        n=f'lowerarm_twist_{j:02d}_l';lr=local_rest[n];out[n]=Lm@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*w)@lr.to_quaternion(),Vector((1,1,1)))
    if 'ik_hand_l' in out:out['ik_hand_l']=out[h]@row[h].inverted()@row['ik_hand_l']
    for n in names:
        if n in grip_deltas:
            loc=row[parents[n]].inverted()@row[n];out[n]=out[parents[n]]@Matrix.LocRotScale(loc.translation,Quaternion(grip_deltas[n])@loc.to_quaternion(),loc.to_scale())
    return out
if __name__=='__main__':
    result=solve(base,params);report={'parameters':params,'shift_cm':[x*100 for x in params[:3]],'pole_degrees':math.degrees(params[3]),'roll_degrees':math.degrees(result[4]),'wrist_axis_degrees':result[5],'elbow_degrees':result[6]}
    report['root_scale']=list(root.to_scale());report['hand_world']=list(base[h].translation);report['shoulder_world']=list(base[u].translation)
    (O/'solve.json').write_text(json.dumps(report,indent=2));print('IDLE_SOLVE',json.dumps(report),flush=True)
    folder=O/'Candidate';folder.mkdir(exist_ok=True);row=apply(base,params);set_pose(row);s.render.resolution_x=800;s.render.resolution_y=540
    for view in ('side','wrist','fps'):
        if view=='fps':r.matrix_world=cs@C;cam.location=(0,0,0);cam.rotation_euler=(math.pi/2,0,0);cam.data.type='PERSP'
        else:
            r.matrix_world=Matrix.Identity(4);target=base[h].translation if view=='wrist' else (base[h].translation+base[u].translation)*.5
            off=Vector((-.23,.08,.15)) if view=='wrist' else Vector((-.5,-.14,.20));cam.location=target+root.to_3x3()@off;cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=.24 if view=='wrist' else .67
        s.render.filepath=str(folder/(view+'.png'));bpy.ops.render.render(write_still=True)
