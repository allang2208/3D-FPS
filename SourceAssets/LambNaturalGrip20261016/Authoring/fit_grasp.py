"""Bounded surface grasp authoring, independent left/right; production untouched."""
import sys,copy,json,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import review_pose as R
import numpy as np
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
OUT=Path(__file__).resolve().parent
m=json.loads((OUT/'fitted.json').read_text())
food=BVHTree.FromPolygons(R.geometry['vertices'],R.geometry['faces'])
def inside(p):
    votes=0
    for dr in [(1,.371,.619),(-.417,1,.293),(.269,-.529,1)]:
        dr=Vector(dr).normalized(); origin=Vector(p);n=0
        for _ in range(20):
            hit,_,_,_=food.ray_cast(origin,dr,100)
            if hit is None:break
            n+=1;origin=hit+dr*.0001
        votes+=n%2
    return votes>=2
class Fit:
    def __init__(self,side):
        self.side=side;self.sign=1 if side=='l' else -1
        self.digits=m['digits'] if side=='l' else m['right_digits']
        self.center=m['grip_in_palm'] if side=='l' else m['right_grip_in_palm']
        self.rotation=m['palm_rotation'] if side=='l' else m['right_palm_rotation']
        h='hand_'+side
        self.children=[n for n in R.order if R.below(n,h)]
        self.palm=R.frame(R.rest['middle_01_'+side].translation-R.rest[h].translation,(R.rest['index_01_'+side].translation-R.rest[h].translation).cross(R.rest['pinky_01_'+side].translation-R.rest[h].translation)*self.sign)
        self.corrections={};self.pad_ids={}
        skin=np.array(R.skin['positions'])
        self.ids=np.array([i for i,w in enumerate(R.skin['weights']) if sum(w.get(n,0) for n in self.children)>.05])
        for digit in self.digits:
            for j in range(3):
                n=f'{digit}_{j+1:02}_{side}'; nxt=f'{digit}_{j+2:02}_{side}'
                v=R.rest[nxt].translation-R.rest[n].translation if nxt in R.rest else R.rest[n].to_3x3()@R.rest[R.parent[n]].to_3x3().inverted()@(R.rest[n].translation-R.rest[R.parent[n]].translation)
                ref=R.frame(v,self.palm.col[2]);self.corrections[n]=ref.inverted()@R.rest[n].to_3x3()
                delta=skin-np.array(R.rest[n].translation);along=delta@np.array(v.normalized())/v.length;depth=delta@np.array(ref.col[2])
                ids=np.where((R.weights[n]>.5)&(along>.22)&(along<.85))[0]
                ids=sorted(ids,key=lambda i:depth[i],reverse=True)
                self.pad_ids[n]=np.array(ids[:max(6,min(20,len(ids)//4))])
        handlocal=(skin-np.array(R.rest[h].translation))@np.array(self.palm)
        palmweight=R.weights[h]+sum((R.weights[n] for n in self.children if 'metacarpal' in n),np.zeros(len(skin)))
        normals=np.zeros_like(skin)
        np.add.at(normals,np.array(R.skin['triangles']).reshape(-1),np.array(R.skin['normals']).reshape(-1,3))
        normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-8)
        normals=normals@np.array(self.palm)
        self.palmids=np.where((palmweight>.65)&(handlocal[:,0]>2.5)&(handlocal[:,0]<7.7)&(normals[:,2]>.45))[0][::3]
        self.sampleids=self.ids
        self.lookup={v:i for i,v in enumerate(self.sampleids)}
        self.ixpad={n:np.array([self.lookup[i] for i in ids if i in self.lookup]) for n,ids in self.pad_ids.items()}
        self.palmix=np.array([self.lookup[i] for i in self.palmids])
        self.pos=R.pos[self.sampleids];self.weights={n:R.weights[n][self.sampleids] for n in R.order if np.any(R.weights[n][self.sampleids])}
        self.setup()
    def setup(self):
        _,obj,goal,info=R.solve(m,2.75)
        self.info=info[self.side]
        self.fixed={n:obj.inverted()@g for n,g in goal.items()}
        self.desired=R.rot(m['object_rotation']).inverted()@Matrix(((1,0,0),(0,0,self.sign),(0,-self.sign,0)))@R.rot(self.rotation)
    def points(self):
        goal=self.fixed.copy()
        for n in self.children:
            if n=='hand_'+self.side:continue
            goal[n]=goal[R.parent[n]]@R.local[n]
            if n in self.corrections:
                digit,num,_=n.split('_');i=int(num)-1;dp=self.digits[digit]
                q=self.desired@Matrix.Rotation(math.radians(dp['spread'][i])*self.sign,3,'Z')@Matrix.Rotation(-math.radians(dp['flex'][i]),3,'Y')@self.corrections[n]
                goal[n]=R.mat(q,goal[n].translation)
        out=np.zeros((len(self.sampleids),3))
        for n,w in self.weights.items():out+=(self.pos@np.array(goal[n]@R.inv[n]).T)[:,:3]*w[:,None]
        return out
    def evaluate(self,details=False,only=None):
        pts=self.points();ds=np.full(len(pts),np.nan)
        selected=np.arange(len(pts)) if only is None else np.where(sum((w for n,w in self.weights.items() if n.startswith(only+'_')),np.zeros(len(pts)))>.05)[0]
        for i in selected:
            p=pts[i]
            near,normal,_,d=food.find_nearest(Vector(p))
            ds[i]=-d if d<3 and inside(p) else d
        used=ds[selected];score=1500*np.mean(np.minimum(used-.02,0)**2)+2500*max(0,-float(used.min())-.005)**2
        row={}
        for n,ix in self.ixpad.items():
            if only and not n.startswith(only+'_'):continue
            if not len(ix):continue
            # Broad pad contact, not the nearest single skinned vertex.
            arr=np.sort(np.abs(ds[ix]));contact=np.mean(arr[:max(3,len(arr)//2)])
            weight=1.2 if '_03_' in n else .6 if '_02_' in n else .08
            if n.startswith('thumb'):weight*=2
            score+=weight*(contact-.08)**2
            row[n]=round(float(contact),4)
        for digit in ([only] if only else self.digits):
            ix=np.where(self.weights[f'{digit}_03_{self.side}']>.7)[0]
            a=np.sort(np.abs(ds[ix]));gap=float(np.mean(a[:max(8,len(a)//10)]))
            score+=(40 if digit=='thumb' else 8 if digit!='pinky' else 1)*max(0,gap-.08)**2
        if only is None and len(self.palmix):
            pd=np.sort(np.abs(ds[self.palmix]));palmgap=float(np.mean(pd[:max(4,len(pd)//4)]));score+=.5*max(0,palmgap-.35)**2
        else:palmgap=None
        if details:return {'cost':score,'skin_samples':len(ds),'max_penetration_cm':max(0,-float(ds.min())),'penetration_over_0_5mm':int(np.sum(ds<-.05)),'deepest_weights':R.skin['weights'][self.sampleids[ds.argmin()]],'pad_half_mean_distance_cm':row,'palm_patch_distance_cm':palmgap,'wrist':self.info}
        return score
    def valid(self,d):
        a,b,c=d['flex']
        return (-5<=a<=55 and 8<=b-a<=45 and 5<=c-b<=40 and c<=115) if d is self.digits['thumb'] else (20<=a<=80 and 25<=b-a<=65 and 15<=c-b<=45 and c<=175)
    def optimize(self):
        before=self.evaluate(True)
        for step in (8,4,2,1,.5):
            for iteration in range(2):
                for digit,dp in self.digits.items():
                    for j in range(3):
                        original=dp['flex'].copy();best=original.copy();score=self.evaluate(only=digit)
                        for delta in (-step,step):
                            dp['flex']=[v+(delta if k>=j else 0) for k,v in enumerate(original)]
                            if self.valid(dp):
                                val=self.evaluate(only=digit)
                                if val<score:score=val;best=dp['flex'].copy()
                        dp['flex']=best
                    old=dp['spread'][0];best=old;score=self.evaluate(only=digit)
                    for delta in (-step*.5,step*.5):
                        v=old+delta
                        if not (-85<=v<=-25 if digit=='thumb' else -12<=v<=12):continue
                        dp['spread']=[v]*3;val=self.evaluate(only=digit)
                        if val<score:score=val;best=v
                    dp['spread']=[best]*3
                for j in range(3):
                    old=self.center[j];best=old;score=self.evaluate()
                    for delta in (-step*.035,step*.035):
                        v=old+delta
                        if not ([4.5,-2,2][j]<=v<=[8.5,2,6][j]):continue
                        self.center[j]=v;self.setup();val=self.evaluate()
                        if val<score:score=val;best=v
                    self.center[j]=best;self.setup()
                for j in range(3):
                    old=self.rotation[j];best=old;score=self.evaluate()
                    for delta in (-step,step):
                        v=old+delta
                        if not ([18,-58 if self.side=='l' else 25,-20][j]<=v<=[48,-25 if self.side=='l' else 58,20][j]):continue
                        self.rotation[j]=v;self.setup();val=self.evaluate()
                        if val<score:score=val;best=v
                    self.rotation[j]=best;self.setup()
            print('FIT',self.side,step,json.dumps(self.evaluate(True)),flush=True)
            (OUT/'fitted.json').write_text(json.dumps(m,indent=2))
        return {'before':before,'after':self.evaluate(True)}
report={}
for s in ['l','r']:
    report[s]=Fit(s).optimize()
(OUT/'fit_report.json').write_text(json.dumps(report,indent=2))
(OUT/'fitted.json').write_text(json.dumps(m,indent=2))
