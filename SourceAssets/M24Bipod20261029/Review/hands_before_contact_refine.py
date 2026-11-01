"""Author V9 left-hand hinge contacts, preserving gun/right-hand and bone lengths."""
from pathlib import Path
exec(compile((Path(__file__).parent.parent/'M24QuickMeleeContact20261028/library.py').read_text().split("if __name__=='__main__':")[0],'library','exec'))
import gzip
from mathutils import Euler
geo=json.loads((O/'geometry.json').read_text());idle,locals0=pose('idle',0)
native_frame=rest['WPN_root']@idle['WPN_root'].inverted();back=native_frame.inverted()
native={n:native_frame@m for n,m in idle.items()}
pivots=[K.to_3x3()@Vector(geo['parts'][k]['pivot_cm'])/100 for k in ('LegA','LegB')]
tips=[K.to_3x3()@Vector(v)/100 for v in geo['tips_cm']]
closed=[tips[i].normalized().rotation_difference(Vector((-.005 if i==0 else .005,tips[i].length,0)).normalized()) for i in (0,1)]
def leg(i,t):return closed[i].slerp(Quaternion(),ease((t-(.45 if i==0 else 1.20))/.40))
def palm_frame(long_axis,across):
    x=long_axis.normalized();y=(across-x*across.dot(x)).normalized();return Matrix((x,y,x.cross(y))).transposed()
long_axis=(native['middle_01_l'].translation-native['hand_l'].translation).normalized()
native_across=native['index_01_l'].translation-native['pinky_01_l'].translation
native_palm=palm_frame(long_axis,native_across)
def grip_rotation(i,t):
    # Roll around the hand's long axis as the leg swings down. Rotating the
    # complete wrist with the hinge instead creates a >100-degree wrist bend.
    axis=leg(i,t)@tips[i].normalized()
    return (palm_frame(long_axis,axis)@native_palm.transposed()).to_quaternion()@native['hand_l'].to_quaternion()
grasp=[];grip_centers=[]
for i in (0,1):
    # Palm below the slim upper leg, fingers curled around it, thumb along its side.
    center=pivots[i]+closed[i]@tips[i].normalized()*.02
    m=Matrix.LocRotScale(center+Vector((-.037,-.065,-.025)),grip_rotation(i,0),Vector((1,1,1)));grasp.append(m)
    grip_centers.append(m.inverted()@(pivots[i]+closed[i]@tips[i].normalized()*.02))
def held(i,t):
    q=grip_rotation(i,t);center=pivots[i]+leg(i,t)@tips[i].normalized()*.02
    return Matrix.LocRotScale(center-q@grip_centers[i],q,Vector((1,1,1)))
def shifted(m,v):
    a=m.copy();a.translation+=Vector(v);return a
def blend(a,b,w):
    p,q,sc=a.decompose();pp,qq,ss=b.decompose();return Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w))
H=native['hand_l'];keys=[(0,H),(.14,shifted(H,(-.025,0,-.025))),(.32,shifted(grasp[0],(-.012,-.01,-.014))),(.45,grasp[0]),
 (.85,held(0,.85)),(1.20,grasp[1]),(1.60,held(1,1.60)),
 (1.87,shifted(H,(-.025,-.025,-.065))),(2.05,H),(2.4,H)]

def hand(t):
    if .45<=t<=.85:return held(0,t)
    if 1.20<=t<=1.60:return held(1,t)
    if .85<t<1.20:
        w=(t-.85)/.35
        return shifted(blend(held(0,.85),grasp[1],ease(w)),(-.016*math.sin(math.pi*w),-.01*math.sin(math.pi*w),-.028*math.sin(math.pi*w)))
    j=max(0,min(len(keys)-2,bisect.bisect_right([v[0] for v in keys],t)-1));a,b=keys[j],keys[j+1]
    return blend(a[1],b[1],ease((t-a[0])/(b[0]-a[0])))

digits=[f'{d}_{j:02d}_l' for d in ('index','middle','ring','pinky','thumb') for j in (1,2,3)]
opened={};curled={}
for n in digits:
    d,j,_=n.split('_');j=int(j);e=(local_rest[n].inverted()@locals0[n]).to_euler()
    if d!='thumb':
        # Retain the measured V9 abduction axes; use only local flexion for the new grip.
        e.z=math.radians({1:18,2:26,3:12}[j]);opened[n]=local_rest[n].to_quaternion()@e.to_quaternion()
        e.z=math.radians({1:62,2:76,3:40}[j]);curled[n]=local_rest[n].to_quaternion()@e.to_quaternion()
    else:
        opened[n]=local_rest[n].to_quaternion()@e.to_quaternion()
        e.z+=math.radians({1:3,2:-14,3:-8}[j]);curled[n]=local_rest[n].to_quaternion()@e.to_quaternion()
# Fit closed flexion to the actual cylindrical contact, with bounded joint angles.
# Fingertip targets never move bones or change scale/rest/skin weights.
axis_center=pivots[0]+closed[0]@tips[0].normalized()*.02;axis=closed[0]@tips[0].normalized()
def finger_points(d,angles):
    matrices={'hand_l':grasp[0]};points=[]
    for n in names:
        if not under(n,'hand_l') or n=='hand_l':continue
        p,q,sc=locals0[n].decompose()
        if n in digits:
            q=curled[n]
            if n.startswith(d+'_'):
                j=int(n.split('_')[1])-1;e=(local_rest[n].inverted()@locals0[n]).to_euler();e.z=angles[j]
                if d=='thumb' and j==0 and len(angles)>3:e.x+=angles[3];e.y+=angles[4]
                q=local_rest[n].to_quaternion()@e.to_quaternion()
        matrices[n]=matrices[parents[n]]@Matrix.LocRotScale(p,q,sc)
        if n.startswith(d+'_') and n in digits:points.append(matrices[n].translation)
    distal=f'{d}_03_l';direction=(rest[distal].translation-rest[f'{d}_02_l'].translation).normalized()
    length=(rest[distal].translation-rest[f'{d}_02_l'].translation).length*.75
    tip_local=rest[distal].to_quaternion().inverted()@(direction*length)
    points.append(matrices[distal]@tip_local);return points
fitting={}
for d in ('index','middle','ring','pinky'):
    start=[math.radians(v) for v in (62,76,40)];q=start[:];bounds=[(20,82),(30,95),(8,60)]
    def cost(a):
        pts=finger_points(d,a);score=0.
        for k in range(3):
            for f in (.2,.5,.8):
                p=pts[k].lerp(pts[k+1],f)-axis_center;rad=(p-axis*p.dot(axis)).length
                score+=max(0,.012-rad)**2*18000
        p=pts[-1]-axis_center;rad=(p-axis*p.dot(axis)).length
        score+=(rad-.014)**2*7500
        score+=sum((a[i]-start[i])**2 for i in range(3))*.018
        return score
    for step in (8,4,2,1):
        for _ in range(8):
            improved=False
            for j in range(3):
                choices=[q[:]]
                for sign in (-1,1):
                    a=q[:];a[j]=max(math.radians(bounds[j][0]),min(math.radians(bounds[j][1]),a[j]+math.radians(step)*sign));choices.append(a)
                best=min(choices,key=cost)
                if cost(best)<cost(q)-1e-9:q=best;improved=True
            if not improved:break
    fitting[d]=[math.degrees(v) for v in q]
    for j in range(3):
        n=f'{d}_{j+1:02d}_l';e=(local_rest[n].inverted()@locals0[n]).to_euler();e.z=q[j];curled[n]=local_rest[n].to_quaternion()@e.to_quaternion()
# The thumb opposes the thin leg rather than keeping the broad stock's open wrap.
thumb_start=[(local_rest[f'thumb_{j:02d}_l'].inverted()@locals0[f'thumb_{j:02d}_l']).to_euler().z for j in (1,2,3)]+[0.,0.]
thumb=thumb_start[:];thumb_bounds=[(v-math.radians(30),v+math.radians(30)) for v in thumb[:3]]+[(-math.radians(25),math.radians(25))]*2
def thumb_cost(a):
    pts=finger_points('thumb',a);score=sum((a[i]-thumb_start[i])**2 for i in range(5))*.006
    for k in range(3):
        for f in (.25,.5,.75):
            delta=pts[k].lerp(pts[k+1],f)-axis_center;rad=(delta-axis*delta.dot(axis)).length
            score+=max(0,.011-rad)**2*15000
    delta=pts[-1]-axis_center;score+=((delta-axis*delta.dot(axis)).length-.014)**2*10000
    return score
for step in (8,4,2,1):
    for _ in range(12):
        changed=False
        for j in range(5):
            choices=[thumb[:]]
            for sign in (-1,1):
                a=thumb[:];a[j]=max(thumb_bounds[j][0],min(thumb_bounds[j][1],a[j]+math.radians(step)*sign));choices.append(a)
            best=min(choices,key=thumb_cost)
            if thumb_cost(best)<thumb_cost(thumb)-1e-9:thumb=best;changed=True
        if not changed:break
for j in range(3):
    n=f'thumb_{j+1:02d}_l';e=(local_rest[n].inverted()@locals0[n]).to_euler();e.z=thumb[j]
    if j==0:e.x+=thumb[3];e.y+=thumb[4]
    curled[n]=local_rest[n].to_quaternion()@e.to_quaternion()
fitting['thumb']=[math.degrees(v) for v in thumb]
u,l,h='upperarm_l','lowerarm_l','hand_l';iu=native[l].translation-native[u].translation;il=native[h].translation-native[l].translation;A=iu.length;B=il.length
def frame(x,z):
    x=x.normalized();z=(z-x*z.dot(x)).normalized();return Matrix((x,z.cross(x).normalized(),z)).transposed()
def authored(t,family):
    original,_=pose('idle',0,family);base={n:native_frame@m for n,m in original.items()};row=clone(base)
    activity=ease(t/.32)*(1-ease((t-1.60)/.45));offset=Vector((.025,.065,.003))*activity
    S=base[u].translation+offset;hm=hand(t);H=hm.translation;v=H-S;d=v.length
    if d>=A+B-.0005:raise ValueError('Bipod grip outside native left-arm reach '+str(t))
    axis=v/d;along=(A*A-B*B+d*d)/(2*d);center=S+axis*along;radius=math.sqrt(max(0,A*A-along*along))
    pole=base[l].translation+offset*.5-center;pole=(pole-axis*pole.dot(axis)).normalized();E=center+pole*radius
    U=E-S;L=H-E;N=U.cross(L).normalized();N0=iu.cross(il).normalized()
    uq=(frame(U,N)@frame(iu,N0).transposed()).to_quaternion()@base[u].to_quaternion();lq=(frame(L,N)@frame(il,N0).transposed()).to_quaternion()@base[l].to_quaternion()
    Um=Matrix.LocRotScale(S,uq,Vector((1,1,1)));Lm=Matrix.LocRotScale(E,lq,Vector((1,1,1)))
    row['clavicle_l'].translation+=offset
    for n in names:
        if under(n,h):continue
        if under(n,l):row[n]=Lm@base[l].inverted()@base[n]
        elif under(n,u):row[n]=Um@base[u].inverted()@base[n]
    row[h]=hm
    release=ease(t/.14)*(1-ease((t-1.70)/.18))
    grip=max(ease((t-.32)/.13)*(1-ease((t-.85)/.10)),ease((t-1.02)/.18)*(1-ease((t-1.60)/.15)))
    for n in names:
        if n==h or not under(n,h):continue
        p,q,sc=locals0[n].decompose()
        if n in digits:
            # Slight per-finger closing offsets avoid a simultaneous mechanical fist.
            dgt=n.split('_')[0];delay={'index':0,'middle':.015,'ring':.025,'pinky':.035,'thumb':.02}[dgt]
            close=max(ease((t-.32-delay)/(.13-delay))*(1-ease((t-.85)/.10)),ease((t-1.02-delay*.3)/(.18-delay*.3))*(1-ease((t-1.60)/.15)))
            q=q.slerp(opened[n],release).slerp(curled[n],close)
        row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,sc)
    ax=base[l].to_quaternion().inverted()@il.normalized();rel=(lq.inverted()@hm.to_quaternion())@(base[l].to_quaternion().inverted()@base[h].to_quaternion()).inverted()
    if rel.w<0:rel=-rel
    roll=2*math.atan2(Vector((rel.x,rel.y,rel.z)).dot(ax),rel.w)
    for j,w in ((1,1.),(2,.5)):
        n=f'lowerarm_twist_{j:02d}_l';lr=base[l].inverted()@base[n];row[n]=Lm@Matrix.LocRotScale(lr.translation,Quaternion(ax,roll*w)@lr.to_quaternion(),lr.to_scale())
    if 'ik_hand_l' in row:row['ik_hand_l']=row[h]@base[h].inverted()@base['ik_hand_l']
    if t<=0 or t>=2.05:row=base
    return {n:back@m for n,m in row.items()}
output={'mesh':'/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9','names':names,'clips':{},'duration':2.4,'rate':120,'finger_flexion':fitting}
for family in ('base','mag10'):
    rows=[];matrices=[];previous={}
    for i in range(289):
        row=authored(i/120,family);matrices.append(row);values=[]
        for n in names:
            local=row[parents[n]].inverted()@row[n] if parents[n] else row[n];p,q,sc=(K@local@K).decompose()
            if n in previous and previous[n].dot(q)<0:q=-q
            previous[n]=q.copy();values.append([*p,q.x,q.y,q.z,q.w,*sc])
        rows.append(values)
    output['clips'][family]={'frames':rows}
    # Keep an editable source action without FBX retargeting or an arm/model offset.
    r.animation_data_clear();r.animation_data_create();action=bpy.data.actions.new('A_M24_Bipod_'+family);r.animation_data.action=action
    s.render.fps=120;s.frame_start=0;s.frame_end=288
    for i,row in enumerate(matrices):
        for n,m in row.items():
            local=row[parents[n]].inverted()@m if parents[n] else m;basis=local_rest[n].inverted()@local;pb=r.pose.bones[n]
            pb.rotation_mode='QUATERNION';pb.location=basis.translation;pb.rotation_quaternion=basis.to_quaternion();pb.scale=basis.to_scale()
            pb.keyframe_insert('location',frame=i);pb.keyframe_insert('rotation_quaternion',frame=i);pb.keyframe_insert('scale',frame=i)
    action.use_fake_user=True
with gzip.open(O/'authored.json.gz','wt',encoding='utf-8') as f:json.dump(output,f)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Bipod_Hands_Editable.blend'))
(O/'animation_authoring.json').write_text(json.dumps({'duration':2.4,'rate':120,'left_hinge_contacts':[[.45,.85],[1.20,1.60]],'hand_return':2.05,'seat_end':2.4,'finger_flexion':fitting,'right_hand_and_weapon':'preserved from current corrected idle','runtime_tested':False},indent=2))
print('M24_BIPOD_HANDS_AUTHORED',fitting,flush=True)
