"""Native-bound hand/garment authoring. UE centimeters, column matrices."""
import json,shutil
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation as R
from scipy.spatial import cKDTree
import trimesh

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ThirdPersonStaffSurfaceRepair20261009'
CHECK=ROOT/'SourceAssets/ThirdPersonStaffCheck20261009'
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def matrix(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
def unit(v):return v/max(np.linalg.norm(v),1e-10)
def frame(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y));return np.column_stack([x,y,np.cross(x,y)])
def align(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b)
    if np.linalg.norm(v)<1e-9:return np.eye(3)
    return R.from_rotvec(unit(v)*np.arctan2(np.linalg.norm(v),np.dot(a,b))).as_matrix()
geos={n:read(OUT/(n+'-input.json')) for n in ['body','ue_chainmail_shirt','ue_steel_gauntlets']}
names=[b['name'] for b in geos['body']['bones']]
parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in geos['body']['bones']}
rest={b['name']:matrix(np.array(b['axes']).T,b['position']) for b in geos['body']['bones']}
local={n:np.linalg.inv(rest[parents[n]])@rest[n] if parents[n] else rest[n] for n in names}
def descendants(hand):
    keep={hand}
    for n in names:
        if parents[n] in keep:keep.add(n)
    return [n for n in names if n in keep and n!=hand]
def from_sample(row):
    return {n:matrix(R.from_quat(t[3:7]).as_matrix()@np.diag(t[7:10]),t[:3]) for n,t in row['bones'].items()}
def skin(geo,world):
    p=np.array(geo['positions']);out=np.zeros_like(p);groups={}
    for i,ws in enumerate(geo['weights']):
        for b,w in ws:groups.setdefault(names[b],[]).append((i,w))
    for n,ws in groups.items():
        rows=np.array(ws);ids=rows[:,0].astype(int);m=world[n]@np.linalg.inv(rest[n])
        out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*rows[:,1,None]
    return out
def staff_fingers(world,variant='false'):
    donor=read(ROOT/'SourceAssets/ApprenticeStaff20260927/ReleaseAnatomy20261001/full-pose.json')
    sr={n:np.array(m) for n,m in donor['rest'].items()}
    v=donor['variants'][variant];sp={'hand_r':np.array(v['hand'])}
    for n in donor['order']:
        if n in v['fingers']:sp[n]=sp[donor['parent'][n]]@np.array(v['fingers'][n])
    palms=[]
    for r in [sr,rest]:
        inv=np.linalg.inv(r['hand_r']);palms.append(np.array([(inv@r[d+'_01_r'])[:3,3] for d in ['index','middle','pinky']]))
    mount=frame(palms[1][1],palms[1][0]-palms[1][2])@frame(palms[0][1],palms[0][0]-palms[0][2]).T
    mapping=world['hand_r'][:3,:3]@mount@sp['hand_r'][:3,:3].T
    desired={}
    for digit in ['thumb','index','middle','ring','pinky']:
        chain=[f'{digit}_{i:02d}_r' for i in [1,2,3]]
        for j,n in enumerate(chain):
            a,b=(j,j+1) if j<2 else (1,2)
            ta=rest[n][:3,:3].T@(rest[chain[b]][:3,3]-rest[chain[a]][:3,3])
            sa=sr[n][:3,:3].T@(sr[chain[b]][:3,3]-sr[chain[a]][:3,3])
            desired[n]=mapping@sp[n][:3,:3]@align(ta,sa)
    w={n:m.copy() for n,m in world.items()}
    for n in descendants('hand_r'):
        pn=parents[n];lm=local[n].copy()
        if n in desired:lm[:3,:3]=w[pn][:3,:3].T@desired[n]
        elif '_half_' in n and pn in desired:
            delta=local[pn][:3,:3].T@(w[parents[pn]][:3,:3].T@w[pn][:3,:3])
            lm[:3,:3]=R.from_rotvec(-.5*R.from_matrix(delta).as_rotvec()).as_matrix()@lm[:3,:3]
        elif pn=='hand_r':lm=np.linalg.inv(world[pn])@world[n]
        w[n]=w[pn]@lm
    return w
def arm_twist(world):
    w={n:m.copy() for n,m in world.items()}
    s,e,h=[w[n] for n in ['upperarm_r','lowerarm_r','hand_r']]
    axis=unit(local['hand_r'][:3,3]);direction=unit(h[:3,3]-e[:3,3])
    no_roll=s[:3,:3]@local['lowerarm_r'][:3,:3]
    no_roll=align(no_roll@axis,direction)@no_roll
    roll=float(R.from_matrix(e[:3,:3]@no_roll.T).as_rotvec()@direction)
    length=np.linalg.norm(local['hand_r'][:3,3])
    for n in ['lowerarm_twist_02_r','lowerarm_twist_01_r','lowerarm_correctiveRoot_r']:
        amount=np.clip(np.dot(local[n][:3,3],axis)/length,0,1)
        lm=local[n].copy();lm[:3,:3]=R.from_rotvec(axis*(-roll*(1-amount))).as_matrix()@lm[:3,:3]
        w[n]=w['lowerarm_r']@lm
        for c in descendants(n):w[c]=w[parents[c]]@local[c]
    return w
def repair_layers():
    g=json.loads(json.dumps(geos['ue_steel_gauntlets']))
    p=np.array(g['positions']);t=np.array(g['triangles']);mat=np.array(g['triangle_materials'])
    armor=np.unique(t[mat==1]);liner=trimesh.Trimesh(p,t[mat==0],process=False)
    liner.fix_normals(multibody=True)
    if liner.volume<0:liner.invert()
    cp,dist,ti=trimesh.proximity.closest_point(liner,p[armor])
    normals=liner.face_normals[ti];signed=np.einsum('ij,ij->i',p[armor]-cp,normals)
    # Move both walls of each thin metal panel together. The old skin-only
    # fit left the larger glove liner cutting through the plate perimeter.
    amount=np.maximum(.12-signed,0)
    ds,ix=cKDTree(p[armor]).query(p[armor],k=24)
    kernel=np.exp(-ds**2/.45**2);kernel/=kernel.sum(1)[:,None]
    for _ in range(4):amount=np.maximum(amount,(amount[ix]*kernel).sum(1))
    displacement=normals*amount[:,None]
    displacement=(displacement[ix]*kernel[:,:,None]).sum(1)
    p[armor]+=displacement
    # Include the closed hand and the casting wrist. Fit in the final posed
    # surface, then pull corrections back through each vertex's blended skin.
    for label in ['idle','cast_Release_14']:
        row=next(r for r in read(CHECK/'poses.json')['samples'] if r['label']==label)
        w=arm_twist(from_sample(row))
        matrices=np.array([(w[n]@np.linalg.inv(rest[n]))[:3,:3] for n in names])
        blend=np.array([sum(matrices[b]*v for b,v in g['weights'][i]) for i in armor])
        for iteration in range(2):
            g['positions']=p.tolist();posed=skin(g,w)
            surface=trimesh.Trimesh(posed,t[mat==0],process=False);surface.fix_normals(multibody=True)
            if surface.volume<0:surface.invert()
            cp,dist,ti=trimesh.proximity.closest_point(surface,posed[armor]);nn=surface.face_normals[ti]
            gap=np.einsum('ij,ij->i',posed[armor]-cp,nn)
            push=nn*np.clip(.10-gap,0,.45)[:,None]
            delta=np.linalg.solve(blend,push[:,:,None])[:,:,0]
            delta=(delta[ix]*kernel[:,:,None]).sum(1)
            p[armor]+=delta
    g['positions']=p.tolist()
    (OUT/'steel-repaired.json').write_text(json.dumps(g,separators=(',',':')))
    return g
def write_views(samples,meshset=geos):
    out=OUT/'Views';out.mkdir(exist_ok=True)
    report={'meshes':{},'samples':[]}
    for n,g in meshset.items():
        np.array(g['triangles'],dtype='<u4').tofile(out/(n+'.indices'))
        np.array(g['triangle_materials'],dtype='<u4').tofile(out/(n+'.materials'))
        report['meshes'][n]={'asset':g['source']}
    for label,w,staff in samples:
        row={'label':label,'staff':staff,'bones':{}}
        for n,m in w.items():row['bones'][n]=m[:3,3].tolist()+R.from_matrix(m[:3,:3]).as_quat().tolist()+[1,1,1]
        report['samples'].append(row)
        for n,g in meshset.items():skin(g,w).astype('<f4').tofile(out/(label+'.'+n+'.vertices'))
    for f in ['staff.vertices','staff.indices']:shutil.copy2(CHECK/f,out/f)
    (out/'poses.json').write_text(json.dumps(report))

if __name__=='__main__':
    row=read(CHECK/'poses.json')['samples'][0]
    w=from_sample(row)
    meshset={**geos,'ue_steel_gauntlets':repair_layers()}
    cast=next(r for r in read(CHECK/'poses.json')['samples'] if r['label']=='cast_Release_14')
    write_views([('layers',w,row['staff']),('cast_fixed',arm_twist(from_sample(cast)),cast['staff'])],meshset)
    print('AUTHOR_INPUT_VIEWS_READY')
