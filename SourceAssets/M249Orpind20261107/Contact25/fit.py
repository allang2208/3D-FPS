"""Weighted native hand fitting against actual mounted M249 part surfaces.

Runs in Blender for its native BVH. Changes joint rotations, never finger
lengths/scales or skin weights. Saved candidate poses are not UE publication.
"""
from pathlib import Path
import pickle,json,sys,time
import numpy as np
from mathutils import Vector,Quaternion,Matrix
from mathutils.bvhtree import BVHTree

r=Path(__file__).resolve().parent
data=pickle.load(open(r/'geometry.pkl','rb'));g=data['native']
poses=pickle.load(open(r/'poses.pkl','rb'))
names=g['names'];parents=g['parents'];ix={n:i for i,n in enumerate(names)}
def mat(v):
    a=np.eye(4);a[:3,:3]=np.array(Quaternion((v[6],*v[3:6])).to_matrix())*np.array(v[7:]);a[:3,3]=v[:3];return a
def unit(v):return v/max(np.linalg.norm(v),1.e-12)
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def spin(axis,degrees):return np.array(Matrix.Rotation(np.radians(float(degrees)),3,Vector(axis)))
def rigid(m):
    v=m.copy();v[:3,:3]=rot(v);return v
B=np.array([mat(v) for v in g['bind']]);ib=np.linalg.inv(B)
finger_ids=[i for i,n in enumerate(names) if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
hand_ids=[ix['hand_l']]+finger_ids
hand_weight=np.array([sum(w for b,w in ws if b in hand_ids) for ws in g['weights']])
skin_ids=np.flatnonzero(hand_weight>.98)
bind_vertices=np.array(g['vertices'])[skin_ids]
groups={}
for j,i in enumerate(skin_ids):
    for b,weight in g['weights'][i]:
        ids,points=groups.setdefault(b,([],[]));ids.append(j);points.append(np.r_[bind_vertices[j],1.]*weight)
groups=[(b,np.array(ids),np.array(points)) for b,(ids,points) in groups.items()]
dom=np.array([max(g['weights'][i],key=lambda x:x[1])[0] for i in skin_ids])
digit_groups={finger:np.array([names[b].startswith(finger) for b in dom]) for finger in ['thumb','index','middle','ring','pinky']}
def skin(w):
    points=np.zeros_like(bind_vertices);xf=w@ib
    for bone,ids,weighted in groups:points[ids]+=weighted@xf[bone,:3,:].T
    return points

palm_normal=unit(np.cross(B[ix['index_01_l'],:3,3]-B[ix['pinky_01_l'],:3,3],B[ix['middle_01_l'],:3,3]-B[ix['hand_l'],:3,3]))
params=[]
for finger in ['thumb','index','middle','ring','pinky']:
    if finger!='thumb':
        bone=finger+'_metacarpal_l';i=ix[bone]
        forward=unit(B[ix[finger+'_01_l'],:3,3]-B[i,:3,3])
        for label,axis,limit in [('splay',palm_normal,12.),('cup',unit(np.cross(forward,palm_normal)),15.)]:
            params.append(dict(bone=bone,axis=(rot(B[i]).T@axis).tolist(),label=label,limit=limit))
    for number in [1,2,3]:
        bone=f'{finger}_{number:02d}_l';i=ix[bone]
        if number<3:forward=unit(B[ix[f'{finger}_{number+1:02d}_l'],:3,3]-B[i,:3,3])
        else:forward=unit(B[i,:3,3]-B[parents[i],:3,3])
        axis=unit(np.cross(forward,palm_normal))
        params.append(dict(bone=bone,axis=(rot(B[i]).T@axis).tolist(),label='flex',limit=[35.,28.,22.][number-1]))
        if finger=='thumb' and number==1:params.append(dict(bone=bone,axis=(rot(B[i]).T@palm_normal).tolist(),label='oppose',limit=25.))
for finger in ['index','middle','ring','pinky']:
    bone=finger+'_01_l';i=ix[bone]
    params.append(dict(bone=bone,axis=(rot(B[i]).T@palm_normal).tolist(),label='spread',limit=18.))
limits=np.array([3.,3.,3.,25.,25.,25.]+[p['limit'] for p in params])

class Fit:
    def __init__(self,w,family,obstacles=None,stride=3):
        self.original=w.copy();self.family=family
        self.root=rigid(w[ix['WPN_root']]);self.w=np.linalg.inv(self.root)@w
        self.local=self.w.copy()
        for i,p in enumerate(parents):
            if p>=0:self.local[i]=np.linalg.inv(self.w[p])@self.w[i]
        self.trees=[]
        for name,part in data['parts'][family].items():
            if obstacles is not None and name not in obstacles:continue
            v,f=part['vertices'],part['faces']
            self.trees.append((name,BVHTree.FromPolygons(v.tolist(),f.tolist(),all_triangles=True),v.min(0),v.max(0)))
        self.sample=np.arange(0,len(skin_ids),stride)
        self.directions=[Vector(v).normalized() for v in [(1,.231,.417),(.319,1,.173),(.137,.293,1)]]
        self.grip=next((tree for name,tree,lo,hi in self.trees if name=='SM_M249_'+family or name=='M249_Factory_Foregrip'),None)
    def pose(self,x):
        w=self.w.copy();local=self.local.copy()
        hand=w[ix['hand_l']].copy();hand[:3,3]+=x[:3]
        rr=np.eye(3)
        for i in range(3):rr=rr@spin(np.eye(3)[i],x[3+i])
        hand[:3,:3]=rr@hand[:3,:3];w[ix['hand_l']]=hand
        for value,p in zip(x[6:],params):
            i=ix[p['bone']];local[i,:3,:3]=local[i,:3,:3]@spin(p['axis'],value)
        for i in finger_ids:w[i]=w[parents[i]]@local[i]
        w[ix['ik_hand_l']]=hand
        return w
    def measure(self,points,indices):
        depths=np.zeros(len(points));near=np.full(len(points),100.)
        for name,tree,lo,hi in self.trees:
            query=np.flatnonzero(np.all(points>=lo-1,axis=1)&np.all(points<=hi+1,axis=1))
            for i in query:
                point=Vector(points[i]);closest,normal,face,distance=tree.find_nearest(point)
                near[i]=min(near[i],distance)
                if distance<.015 or np.any(points[i]<lo) or np.any(points[i]>hi):continue
                votes=0
                for direction in self.directions:
                    origin=point.copy();count=0
                    for _ in range(64):
                        hit,n,fi,length=tree.ray_cast(origin,direction,1000.)
                        if hit is None:break
                        count+=1;origin=hit+direction*.0001
                    votes+=count%2
                if votes>=2:depths[i]=max(depths[i],distance)
        return depths,near
    def score(self,x,details=False):
        w=self.pose(x);points=skin(w)[self.sample]
        dep,near=self.measure(points,self.sample)
        excess=np.maximum(dep-.025,0)
        penalty=.35*float(x[:3]@x[:3])+.004*float(x[3:6]@x[3:6])+.0015*float(x[6:]@x[6:])
        contact=0.
        for finger,group in digit_groups.items():
            digit_points=points[group[self.sample]][::3]
            # Actual mounted grip contact, not a nearby receiver/rail surface.
            dd=np.array([self.grip.find_nearest(Vector(p))[3] for p in digit_points]) if self.grip else near[group[self.sample]]
            if len(dd):contact+=60*max(0.,float(np.quantile(dd,.03))-.22)**2
        value=250*float(excess@excess)+1400*float(excess.max(initial=0))**2+penalty+contact
        if details:return dict(score=value,max_depth_cm=float(dep.max(initial=0)),inside_vertices=int(np.sum(dep>.08)),offset_cm=x[:3].tolist(),rotation_deg=x[3:6].tolist(),joint_max_deg=float(np.max(abs(x[6:]))))
        return value
    def optimize(self,start=None,steps=None):
        x=np.zeros(len(limits)) if start is None else np.array(start).copy()
        best=self.score(x);before=self.score(x,True)
        if start is None:
            # Search the available joint range before local refinement. A
            # finger already crossing a bar can have a local distance minimum
            # on the wrong side of the bar, so tiny initial nudges are not enough.
            for sweep in range(2):
                for i in list(range(6))+list(range(6,len(x))):
                    candidates=np.linspace(-limits[i],limits[i],9)
                    for value in candidates:
                        trial=x.copy();trial[i]=value;cost=self.score(trial)
                        if cost<best-1.e-5:best,x=cost,trial
                print('CONTACT25_RANGE',self.family,sweep,self.score(x,True),flush=True)
        for translation,angle in (steps or [(.5,7.),(.25,3.),(.125,1.5),(.0625,.75)]):
            for sweep in range(3):
                changed=False
                # Repair individual fingers before making a palm-wide move.
                for i in list(range(6,len(x)))+list(range(6)):
                    step=translation if i<3 else angle
                    choices=[]
                    for sign in [-1,1]:
                        trial=x.copy();trial[i]=np.clip(trial[i]+sign*step,-limits[i],limits[i]);choices.append((self.score(trial),trial))
                    value,trial=min(choices,key=lambda q:q[0])
                    if value<best-1.e-5:best,x=value,trial;changed=True
                if not changed:break
            print('CONTACT25_STEP',self.family,translation,self.score(x,True),flush=True)
        return x,before,self.score(x,True)

if __name__=='__main__':
    wanted=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    families=wanted or ['vertical','canted','prism','angled']
    result=pickle.load(open(r/'idle_fit.pkl','rb')) if (r/'idle_fit.pkl').exists() else {}
    for family in families:
        key=next(k for k in poses if k[0]==family and k[1].endswith('_idle'))
        w=poses[key]['world'][0]
        fit=Fit(w,family,obstacles=[n for n in data['parts'][family] if 'side_mag' not in n],stride=3)
        x,before,after=fit.optimize()
        fit.sample=np.arange(len(skin_ids));full=fit.score(x,True)
        if full['max_depth_cm']>.16:
            x,_,full=fit.optimize(x,steps=[(.125,1.5),(.0625,.75)])
        new=fit.root@fit.pose(x)
        result[family]=dict(old_world=w,new_world=new,parameters=x,before=before,after=full)
        with (r/'idle_fit.pkl').open('wb') as f:pickle.dump(result,f)
        (r/'idle_fit.json').write_text(json.dumps({f:{k:v for k,v in row.items() if k in ['before','after']} for f,row in result.items()},indent=2))
        (r/'parameters.json').write_text(json.dumps(params,indent=2))
        print('CONTACT25_IDLE_FIT',family,full,flush=True)
