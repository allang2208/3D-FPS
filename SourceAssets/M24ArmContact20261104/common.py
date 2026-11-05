"""Contact-driven M24 grip: native palm, segment pads and bounded finger flexion."""
from pathlib import Path
ARM_CONTACT_TASK=Path(__file__).resolve().parent
__file__=str(ARM_CONTACT_TASK.parent/'M24SurfaceGrip20261103/fit.py')
exec(compile(Path(__file__).read_text().split("if __name__=='__main__':")[0],'native skin and surfaces','exec'))
import copy,struct,hashlib
TASKOUT=ARM_CONTACT_TASK
D['profiles']=json.load(gzip.open(TASKOUT/'input_profiles.json.gz','rt'))
D['clips'].update(json.load(gzip.open(TASKOUT/'input_clips.json.gz','rt')))
digits=[n for n in names if n.endswith('_l') and n.startswith(('index_','middle_','ring_','pinky_')) and 'metacarpal' not in n]
anchors={};FINGERS=('index','middle','ring','pinky')
for family in ('base','mag10'):
    anchors[family]={}
    for stage,f in [('old',18),('new',38)]:
        row,local=compose(entry(family,'reload'),f/30)
        axes={}
        for d in FINGERS:
            a=row[d+'_01_l'].translation;b=row[d+'_02_l'].translation;c=row[d+'_03_l'].translation
            ax=(b-a).cross(c-b).normalized()
            if ax.length<.1:ax=(row['index_01_l'].translation-row['pinky_01_l'].translation).normalized()
            for j in (1,2,3):
                n=f'{d}_{j:02d}_l';axes[n]=row[n].to_quaternion().inverted()@ax
        pts=skin_corrected(row)[:len(P0)]
        origin=row['hand_l'].translation;forward=(row['middle_01_l'].translation-origin).normalized()
        across=(row['index_01_l'].translation-row['pinky_01_l'].translation).normalized()
        palmar=forward.cross(across).normalized()
        if palmar.dot(row['middle_03_l'].translation-row['middle_01_l'].translation)<0:palmar=-palmar
        length=(row['middle_01_l'].translation-origin).length
        palm=[]
        for i,ws in G['weights'].items():
            palm_weight=ws.get('hand_l',0)+sum(ws.get(d+'_metacarpal_l',0) for d in FINGERS)
            if palm_weight<.6:continue
            v=Vector(pts[int(i)])-origin
            if .3*length<v.dot(forward)<.9*length and abs(v.dot(across))<.032:palm.append((v.dot(palmar),int(i)))
        # Keep both sides initially; select the actual closest palm surface below.
        # A curled fingertip cannot reliably determine which skin side is palmar.
        palm=[i for value,i in palm]
        anchors[family][stage]={'relative':row['WPN_Magazine'].inverted()@row['hand_l'],'local':local,'axes':axes,'palm':palm}

class ContactFrame(SurfaceFrame):
    def __init__(self,family,f,stage,role='reload'):
        super().__init__(family,f,role)
        self.outward=True
        self.anchor=anchors['mag10' if 'mag10' in family else 'base'][stage]
        self.seed['hand_l']=self.row['WPN_Magazine']@self.anchor['relative']
        self.H=self.seed['hand_l'].translation
        self.basis=self.row['WPN_Magazine'].to_quaternion().to_matrix()
        self.segment_ids={}
        for d in FINGERS:
            for j in (2,3):
                n=f'{d}_{j:02d}_l';self.segment_ids[n]=[int(i) for i,ws in G['weights'].items() if ws.get(n,0)>.45]
        self.seed_base={n:m.copy() for n,m in self.seed.items()}
    def initial(self):
        p=skin_corrected(self.row);vs,fs=self.geo['magazine'];vs=vs[np.unique(np.array(fs).ravel())]
        forward=(self.row['WPN_FrontSight'].translation-self.row['WPN_RearSight'].translation).normalized()
        ev,vec=np.linalg.eigh(np.cov(vs.T));thin=Vector(vec[:,0]);up=thin.cross(forward).normalized()
        if up.dot((self.row['WPN_root']@rest['WPN_root'].inverted()).to_quaternion()@Vector((0,0,1)))<0:up=-up
        thin=forward.cross(up).normalized();B=Matrix((forward,thin,up));center=Vector(vs.mean(0))
        vlocal=np.array([list(B@(Vector(v)-center)) for v in vs]);lo=vlocal.min(0);hi=vlocal.max(0)
        close=sorted(self.anchor['palm'],key=lambda i:self.volumes['magazine'].find_nearest(Vector(p[i]))[3])[:12]
        palm=Vector(p[close].mean(0));pl=B@(palm-center);side=-1 if pl.y<0 else 1
        target=Vector((hi[0]-.045,lo[1]-.002 if side<0 else hi[1]+.002,lo[2]+(.035 if 'mag10' in self.family else .025)))
        delta=B.transposed()@target+center-palm
        x=np.zeros(14);x[:3]=np.array(self.basis.transposed()@delta)*1000
        for k in range(6,14,2):x[k]=40.;x[k+1]=-20.
        return x
    def pose(self,x):
        cache_key=tuple(float(v) for v in x)
        if getattr(self,'_pose_key',None)==cache_key:return self._pose_value
        for n in names:
            if n=='hand_l' or n not in handbones:continue
            p,q,sc=self.local[n].decompose()
            if n in digits:
                p0,q,sc0=self.anchor['local'][n].decompose()
                d=n.split('_')[0];j=int(n.split('_')[1]);k=6+2*FINGERS.index(d)
                angle=x[k] if j==1 else x[k+1]*(.6 if j==3 else 1.)
                if j==3 and len(x)>18:angle+=x[18+FINGERS.index(d)]
                q=q@Quaternion(self.anchor['axes'][n],math.radians(angle))
                if j==1 and len(x)>14:
                    direction=self.anchor['local'][d+'_02_l'].translation.normalized()
                    lateral=self.anchor['axes'][n].cross(direction).normalized()
                    q=q@Quaternion(lateral,math.radians(x[14+FINGERS.index(d)]))
            self.seed[n]=self.seed[parents[n]]@Matrix.LocRotScale(p,q,sc)
        target=self.H+self.basis@Vector(x[:3])*.001
        previous=self.S;v=target-self.S;limit=(self.A+self.B)*.964
        shift=v.normalized()*max(0.,v.length-limit)
        if shift.length>.065:raise RuntimeError('Grip needs excessive shoulder relocation')
        self.S=previous+shift
        try:result=super().pose(x[:6])
        finally:self.S=previous
        result['clavicle_l']=Matrix.LocRotScale(self.row['clavicle_l'].translation+shift,self.row['clavicle_l'].to_quaternion(),self.row['clavicle_l'].to_scale())
        result,_=correct_arm(result,1.)
        self._pose_key=cache_key;self._pose_value=result
        return result
    def features(self,p):
        residual=[];terms=[];info={}
        groups=[(n,ids,1.3 if not n.startswith('pinky') else (2. if 'mag10' in self.family else 6.),1.) for n,ids in self.segment_ids.items()]
        if 'mag10' not in self.family:
            groups=[(n,ids,4. if n.startswith('ring') else 10. if n.startswith('pinky') else target,
                     .5 if n.startswith('ring') else .25 if n.startswith('pinky') else w) for n,ids,target,w in groups]
        groups.append(('palm',self.anchor['palm'],2.,1.4))
        for label,ids,target,w in groups:
            rows=[]
            for i in ids:
                pos=Vector(p[i]);near,no,_,dist=self.volumes['magazine'].find_nearest(pos)
                rows.append((dist,i,np.array((pos-near).normalized())))
            rows.sort(key=lambda v:v[0]);rows=rows[:12]
            info[label]=float(np.mean([v[0] for v in rows])*1000)
            for dist,i,n in rows:residual.append((dist*1000-target)*w/len(rows)**.5);terms.append((i,n,w/len(rows)**.5))
        return np.array(residual),terms,info

def f32(v):return struct.unpack('f',struct.pack('f',v))[0]
exec(compile((TASKOUT/'arm.py').read_text(),'native hinge for contact skin','exec'))
