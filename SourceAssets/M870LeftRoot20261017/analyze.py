"""Offline M870 opening diagnosis using current saved mesh weights and poses."""
import gzip,json,math
from collections import Counter
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R, Slerp

O=Path(__file__).parent
def read(name):return json.load(gzip.open(O/name,'rt',encoding='utf-8'))
D=read('poses.json.gz');N=read('native.json.gz');S=read('shirt.json.gz');K=read('skin.json.gz')
names=D['names'];parents=D['parents'];I=np.eye(4)
def unit(v):return v/max(np.linalg.norm(v),1e-12)
def mat(v):
    m=I.copy();m[:3,:3]=R.from_quat(v[3:7]).as_matrix()*v[7:10];m[:3,3]=v[:3];return m
def rot(m):return m[:3,:3]/np.linalg.norm(m[:3,:3],axis=0)
def world(local):
    out={}
    def get(n):
        if n not in out:out[n]=(get(parents[n]) if parents[n] else I)@local[n]
        return out[n]
    for n in names:get(n)
    return out
def ease(x):
    x=np.clip(x,0,1);return x*x*(3-2*x)
def swing(a,b):
    a,b=unit(a),unit(b);c=np.cross(a,b)
    return I[:3,:3].copy() if np.linalg.norm(c)<1e-10 else R.from_rotvec(unit(c)*np.arctan2(np.linalg.norm(c),a@b)).as_matrix()
def blend(a,b,t):return Slerp([0.,1.],R.from_matrix([a,b]))([float(t)]).as_matrix()[0]
def frame(x,y):
    x=unit(x);y=unit(y-x*(x@y));return np.column_stack((x,y,np.cross(x,y)))
def xz(x,z):
    x=unit(x);y=unit(np.cross(z,x));return np.column_stack((x,y,np.cross(x,y)))
rest={n:mat(v) for n,v in N['rest'].items()}
def decode(role,family='base'):
    c=D['clips'][role];rows=np.array(c['rows']);times=np.array(c['times'])
    if family!='base':
        entry=next((x for x in D['profiles'][family]['clips'] if x['base']==c['path']),None)
        if entry:
            if entry['retained']:raise RuntimeError('Retained clip '+str(entry['retained']))
            for track in entry['tracks']:
                n=names.index(track['bone']);v=np.array(track['values']).reshape(-1,10);t=np.array(track['times'])
                a=np.tile(v[0],(len(times),1)) if len(t)==1 else np.array([np.interp(times,t,v[:,j]) for j in range(10)]).T
                if len(t)>1:a[:,3:7]=Slerp(t,R.from_quat(v[:,3:7]))(np.clip(times,t[0],t[-1])).as_quat()
                rows[:,n,:3]+=a[:,:3];rows[:,n,3:7]=(R.from_quat(a[:,3:7])*R.from_quat(rows[:,n,3:7])).as_quat();rows[:,n,7:]+=a[:,7:]
    return [world({n:mat(v) for n,v in zip(names,row)}) for row in rows]
m4={n:mat(v) for n,v in D['ruler'].items()};yaw=R.from_euler('z',90,degrees=True).as_matrix()
target=yaw@xz(m4['WPN_FrontSight'][:3,3]-m4['WPN_RearSight'][:3,3],rot(m4['WPN_root'])@np.array([0,0,1]))
hand=np.array([0.,7.,-7.])+yaw@m4['hand_r'][:3,3]+np.array([-1.900510,1.680418,9.498009])
def camera(family='base'):
    idle=decode('idle',family)[0];c=I.copy()
    c[:3,:3]=target@xz(idle['WPN_FrontSight'][:3,3]-idle['WPN_RearSight'][:3,3],rot(idle['WPN_root'])@np.array([0,-1,0])).T
    c[:3,3]=hand-c[:3,:3]@idle['hand_r'][:3,3];return c
def beneath(n,root):
    while n:
        if n==root:return True
        n=parents[n]
    return False
arm=[n for n in names if beneath(n,'clavicle_l') and not beneath(n,'hand_l')]
def support(p):
    # Mirror the existing final Super90SupportArmNode (also used by M870).
    p={n:m.copy() for n,m in p.items()};old={n:m.copy() for n,m in p.items()}
    a,e,h=[p[n][:3,3].copy() for n in ['upperarm_l','lowerarm_l','hand_l']]
    ru=rest['lowerarm_l'][:3,3]-rest['upperarm_l'][:3,3];rf=rest['hand_l'][:3,3]-rest['lowerarm_l'][:3,3]
    width=rest['index_01_l'][:3,3]-rest['pinky_01_l'][:3,3]
    axis=unit(h-a);distance=np.linalg.norm(h-a);la=np.linalg.norm(e-a);lb=la*np.linalg.norm(rf)/np.linalg.norm(ru)
    if distance<1e-8 or distance>=la+lb-1e-8:return old
    short=max(0.,.935*(la+lb)-distance);shift=-axis*(short*short/(short+.0142*(la+lb)));a+=shift
    reach=np.linalg.norm(h-a);pole=unit((e-(a-shift))-axis*(axis@(e-(a-shift))))
    hd=rot(old['hand_l'])@rot(rest['hand_l']).T;dp=-hd@unit(rf);dp=unit(dp-axis*(dp@axis))
    angle=math.atan2(axis@np.cross(pole,dp),pole@dp);pole=R.from_rotvec(axis*np.clip(angle,-math.radians(32),math.radians(32))).apply(pole)
    along=(la*la-lb*lb+reach*reach)/(2*reach);e=a+axis*along+pole*np.sqrt(max(0.,la*la-along*along))
    fd=frame(h-e,hd@width)@frame(rf,width).T;ud=swing(fd@unit(ru),unit(e-a))@fd
    p['clavicle_l'][:3,3]+=shift;p['upperarm_l'][:3,3]=a;p['upperarm_l'][:3,:3]=ud@rest['upperarm_l'][:3,:3]
    for n,mix in [('lowerarm_l',1.),('lowerarm_aux_l',.5),('lowerarm_twist_02_l',.88),('lowerarm_twist_01_l',1.)]:
        p[n][:3,3]=e+fd@(rest[n][:3,3]-rest['lowerarm_l'][:3,3])*(la/np.linalg.norm(ru))
        p[n][:3,:3]=blend(ud,fd,mix)@rest[n][:3,:3]
    changed={'clavicle_l','upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_02_l','lowerarm_twist_01_l','hand_l'}
    for n in names:
        if n not in changed and parents[n]:p[n]=p[parents[n]]@np.linalg.inv(old[parents[n]])@old[n]
    return p
def existing_clearance(p,c):
    p={n:m.copy() for n,m in p.items()};a,e,h=[(c@p[n])[:3,3] for n in ['upperarm_l','lowerarm_l','hand_l']]
    w=ease((a[0]+4)/8)*ease((a[2]+12)/8)*(1-ease((abs(a[1])-24)/16))
    target=np.array([min(a[0],-10),-max(-a[1],18),min(a[2],-18)])
    target=a+(target-a)*w;q=c[:3,:3].T@swing(a-h,target-h)@c[:3,:3]
    wrist=p['hand_l'][:3,3];delta=I.copy();delta[:3,:3]=q;delta[:3,3]=wrist-q@wrist
    for n in arm:p[n]=delta@p[n]
    return p
def geometry(data):
    v=np.array(data['positions']);f=np.array(data['triangles']);weights=data['weights']
    bind={n:mat(t) for n,t in data['rest'].items()};left=np.array([sum(w for n,w in row.items() if n.endswith('_l')) for row in weights])
    a=bind['upperarm_l'][:3,3];e=bind['lowerarm_l'][:3,3];axis=unit(e-a)
    station=(v-a)@axis
    # The shoulder cut is oblique: its lowest points are 18 cm farther along
    # the arm than its highest points. Select the entire topological boundary.
    minimum=float(np.min(station[left>.99]))
    _,weld=np.unique(np.round(v,4),axis=0,return_inverse=True)
    counts=Counter(tuple(sorted((int(a),int(b)))) for tri in weld[f] for a,b in zip(tri,np.roll(tri,-1)) if a!=b)
    boundary={i for edge,count in counts.items() if count==1 for i in edge}
    proximal=np.array([sum(row.get(n,0.) for n in ('clavicle_l','upperarm_l')) for row in weights])
    ids=np.flatnonzero((left>.99)&(proximal>.99)&np.isin(weld,list(boundary)))
    groups={}
    for n in bind:
        ws=np.array([weights[i].get(n,0.) for i in ids]);active=np.flatnonzero(ws>0)
        if len(active):groups[n]=(active,(np.c_[v[ids[active]],np.ones(len(active))]@np.linalg.inv(bind[n]).T)*ws[active,None])
    return {'ids':ids,'groups':groups,'minimum':minimum,'left':left,'v':v,'f':f}
G={k:geometry(data) for k,data in [('shirt',S),('skin',K)]}
def skin(p,g):
    out=np.zeros((len(g['ids']),3))
    for n,(ids,weighted) in g['groups'].items():out[ids]+=(weighted@p[n].T)[:,:3]
    return out
tv=np.tan(np.deg2rad(75/2));th=tv*(1874/685)
def visible(v):return (v[:,0]>.01)&(abs(v[:,1])<v[:,0]*th)&(abs(v[:,2])<v[:,0]*tv)
if __name__=='__main__':
    print('OPENINGS', {k:{'points':len(g['ids']),'station_min':g['minimum'],'bones':list(g['groups'])} for k,g in G.items()},flush=True)
    results=[];worst=None
    for family in ['base','vertical','canted','prism','angled']:
        c=camera(family)
        for role,clip in D['clips'].items():
            worst_row={'family':family,'role':role,'frames':len(clip['times']),'opening_visible_frames':0,'max_visible_points':0}
            for time,raw in zip(clip['times'],decode(role,family)):
                p=existing_clearance(support(raw),c);pc={n:c@m for n,m in p.items()};v=skin(pc,G['shirt']);count=int(visible(v).sum())
                if count:
                    worst_row['opening_visible_frames']+=1
                    if count>worst_row['max_visible_points']:worst_row.update(max_visible_points=count,worst_time=time,shoulder=(pc['upperarm_l'][:3,3]).tolist(),opening_bounds=[v.min(0).tolist(),v.max(0).tolist()])
                if worst is None or count>worst[0]:worst=(count,family,role,time)
            results.append(worst_row)
        print('M870_ROOT_DIAGNOSED',family,flush=True)
    (O/'diagnosis.json').write_text(json.dumps({'opening_controls':{k:len(g['ids']) for k,g in G.items()},'worst':worst,'rows':results,'offline_only':True},indent=2))
    print('M870_ROOT_WORST',worst,flush=True)
