"""Full-rate hand surface and native joint-offset review; no UE asset writes."""
from pathlib import Path
import sys,json,numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'QuickMeleeSVDReferenceR2_20261019'))
from surface import *
O=HERE

class Surface:
    def __init__(self,data,correctives=False,extra=None):
        self.v=np.array(data['positions']);self.inv=np.linalg.inv(matrices(data['reference']))
        self.weights=np.zeros((len(self.v),len(names)))
        for i,row in enumerate(data['weights']):
            for b,w in row:self.weights[i,ids[data['weight_bones'][b]]]=w
        self.used=np.flatnonzero(self.weights.max(0)>0);self.correctives=correctives;self.extra=extra
        _,self.first,self.weld=np.unique(np.round(self.v,5),axis=0,return_index=True,return_inverse=True)
        self.counts=np.bincount(self.weld);self.T=self.weld[np.array(data['triangles'])]
        bn=[names[j] for j in self.weights.argmax(1)]
        self.mask=np.array([sum(bn[j].endswith('_r') and bn[j].startswith(('hand','thumb','index','middle','ring','pinky')) for j in tri)>=2 for tri in data['triangles']])
        self.arm_mask=np.array([sum(bn[j].endswith('_r') and bn[j].startswith(('upperarm','lowerarm','hand','thumb','index','middle','ring','pinky')) for j in tri)>=2 for tri in data['triangles']])
    def evaluate(self,p,morphs=None):
        v=self.v.copy()
        if self.correctives:
            weights=morphs if morphs is not None else driver.weights(matrix_pose(p))
            for n,w in weights.items():
                if w>=.001 and n in deltas:v+=deltas[n]*w
        if self.extra:
            weights=morphs if morphs is not None else driver.weights(matrix_pose(p))
            for n,d in self.extra.items():
                if weights.get(n,0)>=.001:v+=d*weights[n]
        result=np.zeros_like(v)
        for j in self.used:
            m=p[j]@self.inv[j];result+=(v@m[:3,:3].T+m[:3,3])*self.weights[:,j,None]
        return result
    def folds(self,v,mask=None):
        x=np.zeros((len(self.first),3));np.add.at(x,self.weld,v);x/=self.counts[:,None];T=self.T
        fn=np.cross(x[T[:,1]]-x[T[:,0]],x[T[:,2]]-x[T[:,0]]);vn=np.zeros_like(x)
        for k in range(3):np.add.at(vn,T[:,k],fn)
        vn/=np.maximum(np.linalg.norm(vn,axis=1)[:,None],1e-10)
        return int(((np.einsum('ij,ij->i',fn,vn[T].mean(1))<0)&(self.mask if mask is None else mask)).sum())

bare=Surface(arms,True);blue=Surface(glove)
checked=['upperarm_r','lowerarm_r','lowerarm_twist_01_r','lowerarm_twist_02_r','upperarm_twist_01_r','upperarm_twist_02_r','hand_r']
checked += [n for n in names if n.endswith('_r') and n.startswith(('thumb','index','middle','ring','pinky'))]
def offsets(p):
    out={}
    for n in checked:
        j=ids[n];par=parents[j];a=relative(p[par],p[j]);b=relative(ref[par],ref[j])
        out[n]=float(np.linalg.norm((a[:3,3]-b[:3,3])*np.linalg.norm(p[par,:3,:3],axis=0)))
    return out
def collect(label,sequences):
    report={'label':label,'frames':[]}
    for family,rows in sequences:
        for i,p,morphs,alpha in rows:
            errs=offsets(p);sig=driver.signature(matrix_pose(p),'r')
            skin=bare.evaluate(p,morphs)
            report['frames'].append({'family':family,'frame':i,'alpha':alpha,
                'bare_hand_folds':bare.folds(skin),'bare_arm_folds':bare.folds(skin,bare.arm_mask),
                'glove_hand_folds':blue.folds(blue.evaluate(p,morphs)),
                'maximum_joint_offset_error_cm':max(errs.values()),'worst_joint':max(errs,key=errs.get),
                'wrist_flex_dev_deg':sig[1:3]})
    f=report['frames'];report['summary']={'frames':len(f),'maximum_bare_hand_folds':max(r['bare_hand_folds'] for r in f),
        'maximum_bare_arm_folds':max(r['bare_arm_folds'] for r in f),
        'maximum_glove_hand_folds':max(r['glove_hand_folds'] for r in f),'maximum_joint_offset_error_cm':max(r['maximum_joint_offset_error_cm'] for r in f),
        'maximum_wrist_flex_dev_deg':np.max([np.abs(r['wrist_flex_dev_deg']) for r in f],axis=0).tolist()}
    (O/(label+'-surface-check.json')).write_text(json.dumps(report,indent=2))
    print(label,json.dumps(report['summary']),flush=True)

if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'source'
    if mode!='baseline' and (O/'glove-correctives.npz').exists():
        fields=np.load(O/'glove-correctives.npz');blue.extra={k:fields[k] for k in fields.files}
    if mode=='source':
        p=np.load(O/'poses.npz');collect('source',[(f,[(i,q,None,1.) for i,q in enumerate(p[f])]) for f in ['base']])
    else:
        d=json.loads((O/('native-'+mode+'.json')).read_text());seq=[]
        for f in d['families']:
            order=[f['names'].index(n) for n in names]
            seq.append((f['family'],[(r['frame'],matrices(np.array(r['bones'])[order]),r['morphs'],r['action_alpha']) for r in f['frames']]))
        collect('native-'+mode,seq)
