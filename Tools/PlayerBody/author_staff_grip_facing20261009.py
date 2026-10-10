"""Jason staff grip from the accepted VRE whole-hand grasp.

Keep the source's coordinated MCP/PIP/DIP flexion. Fit five bounded closure
weights and the rigid palm, never independent unconstrained fingertip targets.
Native positions, lengths, bind matrices and skin weights stay unchanged.
"""
import json
from pathlib import Path
import numpy as np
from scipy.optimize import least_squares, minimize
from scipy.spatial.transform import Rotation as R

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/ThirdPersonStaffGripFacing20261009'
OUT.mkdir(parents=True,exist_ok=True)
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def unit(v):return np.asarray(v)/max(np.linalg.norm(v),1e-12)
def matrix(q,p):
    m=np.eye(4);m[:3,:3]=q;m[:3,3]=p;return m
def frame(x,y):
    x=unit(x);y=unit(y-x*np.dot(x,y));return np.column_stack((x,y,np.cross(x,y)))
def align(a,b):
    a,b=unit(a),unit(b);v=np.cross(a,b);s=np.linalg.norm(v)
    return np.eye(3) if s<1e-9 else R.from_rotvec(v/s*np.arctan2(s,np.dot(a,b))).as_matrix()

target=read('SourceAssets/JasonPlayer20261003/Jason.json')
staff=read('SourceAssets/ApprenticeStaff20260927/ReleaseAnatomy20261001/full-pose.json')
surface=read('SourceAssets/ApprenticeStaff20260927/BowBasedGripV12/grip-surfaces.json')
vre=read('SourceAssets/MannyGraspDonor20260912/vre_pose.json')['bones']
bones=target['bones'];names=[b['name'] for b in bones]
parents={b['name']:names[b['parent']] if b['parent']>=0 else None for b in bones}
rest={b['name']:matrix(np.array(b['axes']).T,b['position']) for b in bones}
local={n:np.linalg.inv(rest[parents[n]])@rest[n] if parents[n] else rest[n] for n in names}
def below(n):
    while parents[n]:
        n=parents[n]
        if n=='hand_r':return True
    return False
children=[n for n in names if below(n)]
hand_inv=np.linalg.inv(rest['hand_r'])
native={n:hand_inv@rest[n] for n in ['hand_r',*children]}
digits=['thumb','index','middle','ring','pinky']
joints=[f'{d}_{j:02}_r' for d in digits for j in range(1,4)]
metas=[d+'_metacarpal_r' for d in digits[1:]]
driven=[n for n in children if n in joints+metas]
sr={n:np.linalg.inv(vre['hand_r']['rest'])@np.array(b['rest']) for n,b in vre.items() if n.endswith('_r')}
sp={n:np.linalg.inv(vre['hand_r']['pose'])@np.array(b['pose']) for n,b in vre.items() if n.endswith('_r')}
def palm(w):
    return frame(w['middle_01_r'][:3,3],w['index_01_r'][:3,3]-w['pinky_01_r'][:3,3])
# The donor JSON contains Blender bone matrices; Jason was exported directly
# from UE. Their anatomical frames have opposite parity. Transfer rest-relative
# rotations by conjugation, including this reflection, not absolute bone roll.
bridge=palm(native)@np.diag([1.,1.,-1.])@palm(sr).T
desired={'hand_r':np.eye(3)}
closed={}
for n in children:
    if n in driven:
        change=sp[n][:3,:3]@sr[n][:3,:3].T
        desired[n]=bridge@change@bridge.T@native[n][:3,:3]
        closed[n]=desired[parents[n]].T@desired[n]
    else:
        desired[n]=desired[parents[n]]@local[n][:3,:3]
delta={n:R.from_matrix(local[n][:3,:3].T@closed[n]).as_rotvec() for n in driven}

# Build an anatomical grasp, not an offset from the rejected backward pose.
# In staff space fingers extend +X, thumb side is +Z and palm faces -Y.
# The body attachment's existing +90 degree yaw makes that forward, up,
# and inward respectively for the right hand.
grasp_frame=frame([1.,0.,0.],[0.,0.,1.])
base_h={v:matrix(grasp_frame@palm(native).T,[-7.,4.,-1.]) for v in staff['variants']}
def pose(closure,opposition=0.,spread=0.,roots=None,thumb_roll=0.):
    rotations={n:local[n][:3,:3]@R.from_rotvec(delta[n]*closure[digits.index(n.split('_')[0])]).as_matrix() for n in driven}
    # Thumb opposition is one complete proximal articulation. The two distal
    # joints retain VRE's coupled curl; they cannot fold independently.
    n='thumb_01_r'
    axis=native[n][:3,:3].T@palm(native)[:,0]
    rotations[n]=rotations[n]@R.from_rotvec(axis*opposition).as_matrix()
    axis=native[n][:3,:3].T@palm(native)[:,2]
    rotations[n]=rotations[n]@R.from_rotvec(axis*spread).as_matrix()
    rotations[n]=rotations[n]@R.from_rotvec(np.array([-1.,0.,0.])*thumb_roll).as_matrix()
    if roots is not None:
        # Large shafts need shallower MCP flexion than a closed fist while
        # retaining the donor's coordinated PIP/DIP curl.
        for d,angle in zip(digits[1:],roots):
            n=d+'_01_r'
            rotations[n]=rotations[n]@R.from_rotvec(unit(delta[n])*angle).as_matrix()
    w={'hand_r':np.eye(4)}
    for n in children:
        q=rotations.get(n,local[n][:3,:3])
        if '_half_' in n and parents[n] in rotations:
            change=local[parents[n]][:3,:3].T@rotations[parents[n]]
            q=R.from_rotvec(-R.from_matrix(change).as_rotvec()*.5).as_matrix()@local[n][:3,:3]
        w[n]=w[parents[n]]@matrix(q,local[n][:3,3])
    return rotations,w

seed_closure=np.array([.6,.6,.6,.6,.5])
_,seed=pose(seed_closure)
clouds=[]
visible=set(np.unique(np.array(target['triangles'])[np.array(target['triangle_materials'])==2]))
for label,geo in [('skin',target),('steel',read('SourceAssets/JasonPlayer20261003/ue_steel_gauntlets_fitted.json'))]:
    ids=[i for i,ws in enumerate(geo['weights']) if (label!='skin' or i in visible) and sum(w for b,w in ws if names[b] in native)>.95]
    points=(np.c_[np.asarray(geo['positions'])[ids],np.ones(len(ids))]@hand_inv.T)[:,:3]
    influence=['hand_r',*children]
    weights=np.zeros((len(ids),len(influence)))
    for row,i in enumerate(ids):
        for b,w in geo['weights'][i]:
            if names[b] in native:weights[row,influence.index(names[b])]+=w
        weights[row,0]+=1-weights[row].sum()
    # Select volar pads from native anatomy, before moving the fingers. Selecting
    # the side closest to a badly posed shaft can accidentally choose finger backs.
    palm_normal=palm(native)[:,2]
    # Jason's volar normal points toward the thumb rest ray. The source/target
    # parity conversion above must also make all four fingers curl this way.
    assert np.dot(palm_normal,native['thumb_01_r'][:3,3])>0
    patches={}
    for d in digits:
        for j in (1,2,3):
            n=f'{d}_{j:02}_r';nn=f'{d}_{min(3,j+1):02}_r'
            direction=unit(native[nn][:3,3]-native[n][:3,3]) if j<3 else unit(native[n][:3,3]-native[f'{d}_02_r'][:3,3])
            length=np.linalg.norm(local[nn][:3,3]) if j<3 else np.linalg.norm(local[n][:3,3])*.85
            center=native[n][:3,3]+direction*length*.55
            normal=unit(palm_normal-direction*np.dot(palm_normal,direction))
            if d=='thumb':
                # The thumb pad faces across the palm, not toward the index
                # MCP. The latter selects its lateral/nail surface on Jason.
                flex=unit(delta['thumb_02_r'])
                long_axis=native[n][:3,:3].T@direction
                normal=native[n][:3,:3]@unit(np.cross(flex,long_axis))
            want=center+normal*(.62 if d!='pinky' else .48)
            candidates=np.flatnonzero(sum(weights[:,k] for k,b in enumerate(influence) if b.startswith(d+'_'))>.65)
            patches[n]=candidates[np.argsort(np.linalg.norm(points[candidates]-want,axis=1))[:16]]
    # The glove's palm seam also uses proximal digit weights. A hand/metacarpal
    # dominance threshold incorrectly chose a distant metal panel on that mesh.
    palm_candidates=np.arange(len(points))
    for d in ('index','pinky'):
        center=native[d+'_01_r'][:3,3]*.8
        want=center+palm_normal*.65
        patches['palm_'+d]=palm_candidates[np.argsort(np.linalg.norm(points[palm_candidates]-want,axis=1))[:20]]
    # Include every hand vertex: a sparse cloud missed steel finger panels.
    pick=np.arange(len(ids))
    patches={n:np.searchsorted(pick,p) for n,p in patches.items()}
    points,weights=points[pick],weights[pick]
    bindings=[]
    for k,n in enumerate(influence):
        rows=np.flatnonzero(weights[:,k]>1e-6)
        if len(rows):
            inv=np.linalg.inv(native[n]);bindings.append((n,rows,points[rows]@inv[:3,:3].T+inv[:3,3],weights[rows,k,None]))
    source_triangles=target['triangles'] if label=='skin' else read('SourceAssets/JasonPlayer20261003/ue_steel_gauntlets.json')['triangles']
    remap=np.full(len(geo['positions']),-1,int);remap[ids]=np.arange(len(ids))
    faces=remap[np.array(source_triangles,int)];faces=faces[np.all(faces>=0,axis=1)]
    # Long metal-panel edges can bridge through the convex shaft even when all
    # vertices are outside. Include their edge midpoints and triangle centers.
    fp=points[faces]
    long_edges=np.maximum.reduce([np.linalg.norm(fp[:,0]-fp[:,1],axis=1),np.linalg.norm(fp[:,1]-fp[:,2],axis=1),np.linalg.norm(fp[:,2]-fp[:,0],axis=1)])>.4
    faces=faces[long_edges]
    clouds.append((label,len(points),bindings,patches,faces))

def distance(points,radii):
    z=np.clip(np.interp(points[:,2]+32.,surface['z'],np.arange(len(surface['z']))),0,len(radii)-1.000001)
    a=np.mod(np.arctan2(-points[:,1],points[:,0]),2*np.pi)*surface['angle_count']/(2*np.pi)
    zi,ai=z.astype(int),a.astype(int);u,t=z-zi,a-ai;aj=(ai+1)%surface['angle_count']
    r=(radii[zi,ai]*(1-t)+radii[zi,aj]*t)*(1-u)+(radii[zi+1,ai]*(1-t)+radii[zi+1,aj]*t)*u
    return np.linalg.norm(points[:,:2],axis=1)-r
def evaluate(x,hand,radii):
    rotations,w=pose(x[6:11],x[11],x[12],x[13:17],x[17])
    h=matrix(R.from_rotvec(x[3:6]).as_matrix()@hand[:3,:3],hand[:3,3]+x[:3])
    contact=[]
    for label,count,bindings,patches,faces in clouds:
        points=np.zeros((count,3))
        for n,rows,bound,weight in bindings:
            m=h@w[n];points[rows]+=(bound@m[:3,:3].T+m[:3,3])*weight
        f=points[faces]
        samples=np.concatenate((points,f.mean(1),(f[:,0]+f[:,1])*.5,(f[:,1]+f[:,2])*.5,(f[:,2]+f[:,0])*.5))
        contact.append((label,distance(samples,radii),patches))
    return rotations,w,h,contact

result=dict(revision=2026100903,source='VRE GrabAnimation',
    source_file='SourceAssets/MannyGraspDonor20260912/vre_pose.json',
    source_revision='bf4c7ba554ecbbe614ed3d16669ef53d3f888f09',
    method='Blender-to-UE anatomical parity and rest-relative conjugation; coordinated volar curl; complete skinned contact surface',
    bones=driven,variants={},runtime_tested=False,rendered=False)
last_fit=None
fit_cache={}
for variant in staff['variants']:
    hand=base_h[variant];radii=np.asarray(surface['variants'][variant]['radii'])
    start=np.r_[np.zeros(6),seed_closure,0.,0.,np.zeros(5)]
    if last_fit is not None:start=last_fit.copy()
    def residual(x):
        _,w,h,contact=evaluate(x,hand,radii);terms=[]
        thumb=h@w['thumb_03_r']
        pad_normal=thumb[:3,:3]@unit(np.cross(delta['thumb_02_r'],[-1.,0.,0.]))
        inward=unit(np.r_[-thumb[:2,3],0.])
        terms.append((pad_normal-inward)*6.)
        for label,sd,patches in contact:
            # Normalize full-surface penalties so mesh density cannot open the
            # hand to beat the much smaller set of meaningful contact patches.
            # Per-vertex residuals keep small, deeply intersecting metal panels
            # significant even when most of the high-density glove is clear.
            terms.append(np.minimum(sd-.05,0.)*12.)
            for n,p in patches.items():
                weight=2. if n.startswith('palm') else (0. if '_01_' in n else .25 if '_02_' in n else 3.)
                if n=='thumb_03_r':weight=5.
                gap=.10 if label=='steel' else .28
                terms.append((sd[p]-gap)*(weight/np.sqrt(len(p))))
        terms.extend([x[:3]*.04,x[3:6]*1.,(x[6:11]-.7)*1.,x[11:13]*.5,x[13:17]*1.,x[17:]*.7])
        return np.concatenate(terms)
    lo=np.r_[[-6.,-3.,-3.],np.radians([-45.,-40.,-25.]),[.25,.4,.4,.4,.4],np.radians([-45.,-50.]),np.radians([-25.]*4),np.radians(-60.)]
    hi=np.r_[[5.,5.,3.],np.radians([45.,40.,25.]),[1.05,1.06,1.06,1.06,1.06],np.radians([45.,50.]),np.radians([25.]*4),np.radians(60.)]
    cache_key=radii.tobytes()
    fit=fit_cache.get(cache_key)
    if fit is None:
        fit=least_squares(residual,start,bounds=(lo,hi),max_nfev=180,x_scale='jac',ftol=1e-6,xtol=1e-7,gtol=1e-6)
        seed=fit.x.copy()
        scales=np.r_[[.4]*3,[.06]*3,[.05]*5,[.08]*7]
        def clearance(x):return np.array([float(sd.min())-.035 for _,sd,_ in evaluate(x,hand,radii)[3]])
        clear=minimize(lambda x:float(np.sum(((x-seed)/scales)**2)),seed,method='SLSQP',
            bounds=list(zip(lo,hi)),constraints=[dict(type='ineq',fun=clearance)],
            options=dict(maxiter=100,ftol=1e-9))
        print('CLEARANCE_FIT',variant,clear.success,clear.message,clearance(clear.x).tolist(),flush=True)
        # Save diagnostics even when a candidate cannot be published.
        (OUT/('clearance-'+variant+'.json')).write_text(json.dumps(dict(seed=seed.tolist(),candidate=clear.x.tolist(),clearance=clearance(clear.x).tolist())))
        # 0.035 cm is the solver target, 0.03 cm is the publication floor.
        if np.min(clearance(clear.x))<-.005:raise RuntimeError('Surface clearance did not converge '+variant)
        fit.x=clear.x
        fit_cache[cache_key]=fit
    last_fit=fit.x.copy()
    rotations,w,h,contact=evaluate(fit.x,hand,radii)
    result['variants'][variant]=dict(hand_in_grip=h.tolist(),mount=(np.linalg.inv(h)@np.array(staff['variants'][variant]['hand'])).tolist(),
        rotations={n:R.from_matrix(rotations[n]).as_quat().tolist() for n in driven},closure=fit.x[6:11].tolist(),
        thumb_opposition_degrees=float(np.degrees(fit.x[11])),rigid_correction=fit.x[:6].tolist(),iterations=int(fit.nfev),
        thumb_spread_degrees=float(np.degrees(fit.x[12])),mcp_adjustment_degrees=np.degrees(fit.x[13:17]).tolist(),
        thumb_roll_degrees=float(np.degrees(fit.x[17])),
        surface_metrics={label:dict(vertex_count=len(sd),minimum_clearance_cm=float(sd.min()),penetrating_vertices=int((sd<0).sum()),pad_clearance_cm={n:float(np.median(sd[p])) for n,p in patches.items()}) for label,sd,patches in contact})
    print('STAFF_VRE_AUTHORED',variant,'closure',np.round(fit.x[6:11],3).tolist(),flush=True)
(OUT/'authored-grip.json').write_text(json.dumps(result,indent=2)+'\n')
def qstr(q):return 'FQuat('+','.join(f'{v:.10f}' for v in q)+')'
lines=['// Generated by Tools/PlayerBody/author_staff_grip_facing20261009.py; anatomical VRE rest-delta transfer.', '#pragma once','#include "CoreMinimal.h"','namespace FPSBodyStaffGripData {',
       'inline constexpr int32 VariantCount=4, BoneCount=15;', 'inline const FTransform Mounts[]={']
for v in result['variants'].values():
    m=np.array(v['mount']);lines.append('FTransform('+qstr(R.from_matrix(m[:3,:3]).as_quat())+',FVector('+','.join(f'{x:.10f}' for x in m[:3,3])+')),')
lines+=['};','inline const FQuat Rotations[VariantCount][BoneCount]={']
for v in result['variants'].values():lines.append('{'+','.join(qstr(v['rotations'][n]) for n in joints)+'},')
lines+=['};','inline const FQuat Metacarpals[VariantCount][4]={']
for v in result['variants'].values():lines.append('{'+','.join(qstr(v['rotations'][n]) for n in metas)+'},')
lines+=['};','inline const FVector ReferenceLocations[]={']
for n in joints:lines.append('FVector('+','.join(f'{v:.9f}' for v in local[n][:3,3])+'),')
lines+=['};','}']
(OUT/'FPSBodyStaffGripData.h').write_text('\n'.join(lines)+'\n')
print('STAFF_VRE_DATA_SAVED',flush=True)
