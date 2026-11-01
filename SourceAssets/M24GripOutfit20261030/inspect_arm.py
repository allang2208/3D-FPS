from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
u,l,h='upperarm_r','lowerarm_r','hand_r'
RU=rest[l].translation-rest[u].translation;RL=rest[h].translation-rest[l].translation
A,B=RU.length,RL.length;RN=RU.cross(RL).normalized();ax=rest[l].to_quaternion().inverted()@RL.normalized()
hand_rel=rest[l].to_quaternion().inverted()@rest[h].to_quaternion()
idle=pose('idle',0)[0]
def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x).normalized(),z)).transposed()
def solve_arm(row,t,duration,side):
    u,l,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    RU=rest[l].translation-rest[u].translation;RL=rest[h].translation-rest[l].translation
    A,B=RU.length,RL.length;RN=RU.cross(RL).normalized();ax=rest[l].to_quaternion().inverted()@RL.normalized()
    hand_rel=rest[l].to_quaternion().inverted()@rest[h].to_quaternion()
    w=ease(t/.32)*ease((duration-t)/.32)
    if w<1e-7:return row
    # Keep the gun/wrist fixed. Shoulder moves back into the player's body;
    # solve the native-length arm to that wrist, never scale a forearm.
    shift=C.to_3x3().inverted()@Vector((-4.0,0,-2.5)) if side=='r' else Vector((0,0,0))
    S=row[u].translation.lerp(idle[u].translation+shift,w);H=row[h].translation
    V=H-S;d=V.length;axis=V.normalized()
    if d>=A+B-.002:raise RuntimeError('Inspect shoulder is outside native arm reach')
    mid=S+axis*((A*A-B*B+d*d)/(2*d));pole=row[l].translation-mid;pole=(pole-axis*pole.dot(axis)).normalized()
    # Move the elbow around its reachable circle toward a straighter wrist.
    # Cap the swivel and ease it with the shoulder correction at both ends.
    forward=(row['middle_01_'+side].translation-H).normalized();desired=H-forward*B-mid
    desired=desired-axis*desired.dot(axis)
    # A signed atan2 would switch between +/-25 degrees when the preferred
    # elbow crosses behind the current pole. A bounded tangent step is smooth
    # through that antipodal case and through a vanishing projection.
    swivel=math.radians(20)*w*axis.dot(pole.cross(desired))/max(.10,desired.length)
    pole=Quaternion(axis,swivel)@pole
    E=mid+pole*math.sqrt(max(0,A*A-(mid-S).length_squared));U=E-S;L=H-E;N=U.cross(L).normalized()
    uq=(frame(U,N)@frame(RU,RN).transposed()).to_quaternion()@rest[u].to_quaternion()
    lq=(frame(L,N)@frame(RL,RN).transposed()).to_quaternion()@rest[l].to_quaternion()
    rel=lq.inverted()@row[h].to_quaternion()@hand_rel.inverted()
    if rel.w<0:rel=-rel
    roll=2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(ax),rel.w)
    Um=Matrix.LocRotScale(S,uq,Vector((1,1,1)));Lm=Matrix.LocRotScale(E,lq,Vector((1,1,1)));out=clone(row)
    clav='clavicle_'+side;out[clav]=Um@rest[u].inverted()@rest[clav]
    for n in names:
        if under(n,h):continue
        if under(n,l):out[n]=Lm@rest[l].inverted()@rest[n]
        elif under(n,u):out[n]=Um@rest[u].inverted()@rest[n]
    for j,weight in ((1,1.),(2,.5)):
        n=f'lowerarm_twist_{j:02d}_{side}';lr=local_rest[n];out[n]=Lm@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*weight)@lr.to_quaternion(),Vector((1,1,1)))
    return out
def solve_inspect(row,t,duration):
    return solve_arm(solve_arm(row,t,duration,'r'),t,duration,'l')
def metrics(row):
    U=row[l].translation-row[u].translation;L=row[h].translation-row[l].translation
    return {'upper_cm':U.length*100,'fore_cm':L.length*100,'elbow':angle(U,L),'wrist':angle(L,row['middle_01_r'].translation-row[h].translation),'shoulder_camera_cm':list(C@row[u].translation)}
if __name__=='__main__':
    path=next(p for p in roles if p.endswith('A_M24_inspect'));clip=roles[path];entry=next(x for x in ue['profiles']['base'] if x['base']==path);duration=(clip['keys']-1)/clip['fps']
    report=[]
    for i in range(clip['keys']):
        t=i/clip['fps'];row,_=local_pose(clip,entry,t);fixed=solve_inspect(row,t,duration)
        report.append({'t':t,'before':metrics(row),'after':metrics(fixed),'wrist_difference_cm':(row[h].translation-fixed[h].translation).length*100})
    (O/'inspect_metrics.json').write_text(json.dumps(report,indent=2))
    for t in (.5,1.5,2.5):
        row,_=local_pose(clip,entry,t);view(solve_inspect(row,t,duration),O/'Candidate'/('inspect_'+str(t)+'.png'))
    print('INSPECT_METRICS',json.dumps(report[len(report)//2]),flush=True)
