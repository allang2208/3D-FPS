"""Transfer complete native FK grip chains; retain 201 action mechanics and timing."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
O=Path(__file__).parent;S=json.loads((O/'sources.json').read_text());G=json.loads((O/'geometry.json').read_text())
K=O/'Keys';K.mkdir(exist_ok=True)
def mat(t):
    m=np.eye(4);m[:3,:3]=Rotation.from_quat(t['q']).as_matrix()@np.diag(t['s']);m[:3,3]=t['p'];return m
def unpack(m):
    s=np.linalg.norm(m[:3,:3],axis=0);return {'p':m[:3,3].tolist(),'q':Rotation.from_matrix(m[:3,:3]/s).as_quat().tolist(),'s':s.tolist()}
def mixq(a,b,w):
    a=np.array(a);b=np.array(b);dot=np.dot(a,b)
    if dot<0:b=-b;dot=-dot
    if dot>.9995:q=a+(b-a)*w
    else:
        angle=np.arccos(np.clip(dot,-1,1));q=(np.sin((1-w)*angle)*a+np.sin(w*angle)*b)/np.sin(angle)
    return (q/np.linalg.norm(q)).tolist()
def ramp(t,a,b):
    x=max(0.,min(1.,(t-a)/(b-a)));return x*x*x*(x*(x*6-15)+10)
flip=np.diag([1,-1,1,1]);mount=flip@np.array(G['grip_transform_blender'])@flip
bones=S['201']['bones'];names=[n for n in bones if n.endswith('_l') and n.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky'))]
idle=json.loads(Path(S['clips']['idle']['file']).read_text())['poses'][0]
idlehand=(np.linalg.inv(mat(idle['WPN_root']['world']))@mat(idle['hand_l']['world']))[:3,3]
report={'method':'Native complete FK donor chain; rigid root/contact placement; no IK or twist rewrite','clips':{},'runtime_tested':False}
for family,src in S['donors'].items():
    donor=json.loads(Path(src['file']).read_text())['poses'][0]
    # Shoulder, elbow, wrist and every helper retain the same native chain.
    rootcontact=mount@np.linalg.inv(mat(donor['WPN_root']['world']))@mat(donor['clavicle_l']['world'])
    for key,base in S['clips'].items():
        if key.startswith('reload'):continue  # Magazine24 owns magazine reloads; belt feed retired.
        rows=json.loads(Path(base['file']).read_text())['poses'];tracks={n:[] for n in names}
        for i,row in enumerate(rows):
            t=base['seconds']*i/max(1,len(rows)-1);end=base['seconds']
            if key.startswith('reload_belt'):
                ret=6.40 if key.endswith('empty') else 6.12
                w=1-ramp(t,0,.28)+ramp(t,ret,end)
                fingers=1-ramp(t,0,.20)+ramp(t,min(ret+.07,end-.07),end)
            elif key.startswith('reload'):
                w=1-ramp(t,.10,.3167)+ramp(t,1.9833,2.20)
                fingers=1-ramp(t,.08,.27)+ramp(t,2.04,2.25)
            elif key=='sprint_enter':
                w=1-ramp(t,0,end*.65);fingers=1-ramp(t,0,end*.4)
            elif key=='sprint_loop':w=fingers=0.
            elif key=='sprint_exit':
                w=ramp(t,end*.35,end);fingers=ramp(t,end*.60,end)
            elif key=='inspect':
                hp=(np.linalg.inv(mat(row['WPN_root']['world']))@mat(row['hand_l']['world']))[:3,3]
                w=1-ramp(float(np.linalg.norm(hp-idlehand)),.025,.09);fingers=w
            else:w=fingers=1.
            parent=bones['clavicle_l']['parent']
            goal=unpack(np.linalg.inv(mat(row[parent]['world']))@mat(row['WPN_root']['world'])@rootcontact)
            for n in names:
                old=row[n]['local'];new=goal if n=='clavicle_l' else donor[n]['local']
                weight=fingers if n.startswith(('thumb','index','middle','ring','pinky')) else w
                value={'p':old['p'],'s':old['s'],'q':old['q'] if weight==0 else mixq(old['q'],new['q'],weight)}
                if n=='clavicle_l' and weight>0:value['p']=(np.array(old['p'])*(1-weight)+np.array(new['p'])*weight).tolist()
                tracks[n].append(value)
        path=K/(family+'_'+key+'.json');path.write_text(json.dumps(tracks,separators=(',',':')))
        report['clips'][family+'/'+key]={'source':base['asset'],'source_sha256':base['sha256'],'donor':src['asset'],'donor_sha256':src['sha256'],'seconds':base['seconds'],'count':base['count'],'fps':base['fps'],'keys':str(path),'destination':f'/Game/Weapons/LMG201/Accessories22/Animations/{family}/A_LMG201_{family}_{key}'}
    print('LMG20122_NATIVE_FK',family,flush=True)
(O/'animations.json').write_text(json.dumps(report,indent=2))
