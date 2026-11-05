"""Jointly clear opposed stock faces with small palm and digit adjustments."""
from pathlib import Path
exec(compile((Path(__file__).parent/'surface.py').read_text(),'native contact','exec'))
import copy

FPS=240
source=json.load(gzip.open(O/'digit_path_patch.json.gz','rt'))
exported={};final={};report={'profiles':{}}
ids=np.unique(np.r_[hand_ids[::2],hand_ids[::3],arm_ids[::12],arm_ids[::15]])
axes=[]
for digit in ('thumb','index','middle','ring','pinky'):
    for joint in range(1,4):
        name=f'{digit}_{joint:02d}_r'
        for axis in (range(3) if joint==1 and digit=='thumb' else (1,2) if joint==1 else (2,)):
            weights=W[ids][:,[ri[n] for n in RIGHT if under(n,name)]].sum(axis=1)
            axes.append((name,axis,weights))
basis=np.eye(3);dimensions=3+len(axes)
caps=np.array([8.]*3+[16. if name.startswith('thumb') else (8. if axis==1 else 12.) for name,axis,_ in axes])
regularization=np.array([.06]*3+[.035]*len(axes))

def apply_pose(original,params):
    row=clone(original);root=row['WPN_root']@rest['WPN_root'].inverted()
    offset=root.to_3x3()@Vector(params[:3])*.001
    angles={}
    for value,(name,axis,_) in zip(params[3:],axes):
        angles.setdefault(name,[0.]*3)[axis]=math.radians(value)
    for n in ['clavicle_r',*RIGHT,'ik_hand_r']:
        if under(n,'hand_r') and n!='hand_r':
            p,q,s=local(original,n).decompose()
            if n in angles:q=q@Euler(angles[n],'XYZ').to_quaternion()
            row[n]=row[parents[n]]@Matrix.LocRotScale(p,q,s)
        else:row[n].translation+=offset
    return row

def linear_constraints(row,tree):
    inv=rest['WPN_root']@row['WPN_root'].inverted()
    X=(np.c_[skin_points(row,ids,True),np.ones(len(ids))]@np.asarray(inv).T)[:,:3]
    normals=[];points=[];gaps=[]
    for i,p in enumerate(X):
        v=Vector(p);nearest,n,_,dist=tree.find_nearest(v)
        if dist>.012:continue
        side=(v-nearest).dot(n)
        if side>=0:
            if dist>.002:continue
            distance=dist*1000
        else:
            if signed_distance(tree,[v],True)[0]>=0:continue
            distance=-dist*1000
        points.append(i);normals.append(n);gaps.append(.22-distance)
    if not points:return np.zeros((0,dimensions)),np.zeros(0)
    N=np.array(normals);J=np.zeros((len(points),dimensions));J[:,:3]=N
    transforms={name:inv@row[name] for name,_,_ in axes}
    for j,(name,axis,weights) in enumerate(axes):
        transform=transforms[name];pivot=np.asarray(transform.translation)
        direction=np.asarray(transform.to_quaternion()@Vector(basis[axis]))
        velocity=np.cross(direction,X[points]-pivot)*weights[points,None]*math.radians(1)*1000
        J[:,j+3]=np.einsum('ij,ij->i',velocity,N)
    return J,np.asarray(gaps)

def fit(original,tree,previous,envelope):
    values=previous*.75
    for _ in range(6):
        J,gap=linear_constraints(apply_pose(original,values),tree)
        if len(gap)==0 or max(gap)<.27:break
        delta=np.zeros(dimensions)
        for _ in range(65):
            remaining=gap-J@delta;k=np.argmax(remaining)
            if remaining[k]<.07:break
            # Weighted projection. Both fingertip rotation and whole-hand
            # motion can resolve a contact without crushing the opposite pad.
            direction=J[k]/regularization
            delta+=direction*(remaining[k]/(direction@J[k]+.01))
            delta=np.clip(delta+values,-caps*envelope,caps*envelope)-values
        values+=delta*.8
    return values

take=[i/120 for i in range(109)]
for family,clip in source.items():
    kind=next((k for k in ('balanced','phantom','stable') if family.endswith('_'+k)),'Default')
    tree=weapon_tree(kind,'mag10' if 'mag10' in family else 'mag5');route=[]
    for i,t in enumerate(take):
        if i in (0,108):route.append(np.zeros(dimensions));continue
        original,_=compose(clip,t)
        route.append(fit(original,tree,route[-1],smooth(t/.024)*smooth((.9-t)/.024)))
    route=np.array(route);curve=route.copy();curve[1:-1]=.88*route[1:-1]+.06*(route[:-2]+route[2:])
    # With a stationary grasp, use the impact solution throughout contact.
    for i,t in enumerate(take):
        weight=smooth((t-.14)/.02)*smooth((.46-t)/.015)
        curve[i]=curve[i]*(1-weight)+curve[30]*weight
    clip_out=copy.deepcopy(clip);rows=[];last={}
    tracks={tr['bone']:tr for tr in clip_out['tracks'] if tr['bone'] in {'clavicle_r','ik_hand_r',*[n for n,_,_ in axes]}}
    for i in range(217):
        t=i/FPS;j=min(i//2,107);w=i/2-j
        original,_=compose(clip,t);row=apply_pose(original,curve[j]*(1-w)+curve[j+1]*w);rows.append(row)
        for n,tr in tracks.items():
            if i in (0,216):continue
            p,q,s=(K@local(row,n)@K).decompose();bp,bq,bs=raw(D['clips'][clip['base']],t,n).decompose()
            dq=q@bq.inverted();dq.normalize()
            baseline=tr['values'][i*10+3:i*10+7];baseline=Quaternion((baseline[3],*baseline[:3]))
            if baseline.dot(dq)<0:dq.negate()
            tr['values'][i*10:i*10+10]=[*(p-bp),dq.x,dq.y,dq.z,dq.w,*(s-bs)]
    final[family]=rows;exported[family]=clip_out
    report['profiles'][family]={'parameters':curve.tolist()};print('CLEARANCE_AUTHORED',family,flush=True)
with gzip.open(O/'quick_melee_patch.json.gz','wt',compresslevel=1) as fp:json.dump(exported,fp,separators=(',',':'))
with gzip.open(O/'contact_fit_patch.json.gz','wt',compresslevel=1) as fp:json.dump(exported,fp,separators=(',',':'))
(O/'finger_palm_clearance.json').write_text(json.dumps(report))
code=(S/'M24QuickMeleeGrip20261104/author.py').read_text().split('# Native editable rig plus the current V9 skin and runtime-equivalent JC tracks.')[1]
code=code.replace('M24_QuickMelee_CurrentGrip_Editable.blend','M24_QuickMelee_RightHandR3_Editable.blend').replace('s.render.fps = 200','s.render.fps = 240').replace('(len(rows) - 1) / 200','(len(rows) - 1) / 240').replace('s.frame_end=180','s.frame_end=216').replace("O/'authoring.json'","O/'final_export.json'")
exec(compile(code,'native editable export','exec'))
print('M24_COMBINED_CLEARANCE_COMPLETE',flush=True)
