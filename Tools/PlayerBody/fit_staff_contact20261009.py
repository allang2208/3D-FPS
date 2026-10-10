"""Bounded anatomical adaptation of the FPS grip to Jason's actual surfaces."""
import json
import numpy as np
from scipy.optimize import least_squares
import author_staff_surface_repair20261009 as a

row=a.read(a.CHECK/'poses.json')['samples'][0];world=a.from_sample(row)
donor=a.read(a.ROOT/'SourceAssets/ApprenticeStaff20260927/ReleaseAnatomy20261001/full-pose.json')
surfaces=a.read(a.ROOT/'SourceAssets/ApprenticeStaff20260927/BowBasedGripV12/grip-surfaces.json')
steel=a.read(a.OUT/'steel-repaired.json')
children=a.descendants('hand_r');influences=['hand_r',*children];joints=[f'{d}_{j:02d}_r' for d in ['thumb','index','middle','ring','pinky'] for j in [1,2,3]]
handinv=np.linalg.inv(a.rest['hand_r']);native={n:handinv@a.rest[n] for n in influences}
clouds=[]
critical=a.read(a.OUT/'critical-vertices.json') if (a.OUT/'critical-vertices.json').exists() else {}
for label,g in [('skin',a.geos['body']),('steel',steel)]:
    ids=np.array([i for i,ws in enumerate(g['weights']) if sum(w for b,w in ws if a.names[b] in influences)>.98])
    ids=ids[::max(1,len(ids)//2200)]
    ids=np.union1d(ids,critical.get(label,[])).astype(int)
    p=np.array(g['positions'])[ids];p=p@handinv[:3,:3].T+handinv[:3,3]
    weights=np.zeros((len(p),len(influences)))
    for k,i in enumerate(ids):
        for b,v in g['weights'][i]:
            if a.names[b] in influences:weights[k,influences.index(a.names[b])]+=v
    weights[:,0]+=1-weights.sum(1)
    inputs=[]
    for j,n in enumerate(influences):
        mm=np.linalg.inv(native[n]);inputs.append(np.c_[p@mm[:3,:3].T+mm[:3,3],np.ones(len(p))]*weights[:,j,None])
    clouds.append((label,np.array(inputs)))
source_rest={n:np.array(m) for n,m in donor['rest'].items()}
palms=[]
for r in [source_rest,a.rest]:
    inv=np.linalg.inv(r['hand_r']);palms.append(np.array([(inv@r[d+'_01_r'])[:3,3] for d in ['index','middle','pinky']]))
mq=a.frame(palms[1][1],palms[1][0]-palms[1][2])@a.frame(palms[0][1],palms[0][0]-palms[0][2]).T
mount=a.matrix(mq,palms[1].mean(0)-mq@palms[0].mean(0))
def clearance(p,variant):
    radii=np.array(surfaces['variants'][variant]['radii'])
    z=np.interp(p[:,2]+32,surfaces['z'],np.arange(len(surfaces['z'])));z=np.clip(z,0,len(radii)-1.000001)
    angle=np.mod(np.arctan2(-p[:,1],p[:,0]),2*np.pi)*surfaces['angle_count']/(2*np.pi)
    zi,ai=z.astype(int),angle.astype(int);u,t=z-zi,angle-ai;aj=(ai+1)%surfaces['angle_count']
    radius=(radii[zi,ai]*(1-t)+radii[zi,aj]*t)*(1-u)+(radii[zi+1,ai]*(1-t)+radii[zi+1,aj]*t)*u
    # Surface samples use mesh space; callers use contact space at mesh z=32.
    return np.linalg.norm(p[:,:2],axis=1)-radius
result={};views=[]
for variant in donor['variants']:
    base=a.staff_fingers(world,variant);base={n:np.linalg.inv(base['hand_r'])@base[n] for n in influences}
    bl={n:np.linalg.inv(base[a.parents[n]])@base[n] for n in children}
    axes=[]
    for n in joints:
        rv=a.R.from_matrix(a.local[n][:3,:3].T@bl[n][:3,:3]).as_rotvec();axes.append(a.unit(rv))
    contact=mount@np.linalg.inv(np.array(donor['variants'][variant]['hand']))
    def candidate(x):
        w={'hand_r':np.eye(4)};ls={}
        for n in children:
            lm=bl[n].copy();pn=a.parents[n]
            if n in joints:
                j=joints.index(n);lm[:3,:3]=lm[:3,:3]@a.R.from_rotvec(axes[j]*x[j+3]).as_matrix()
            elif '_half_' in n and pn in joints:
                delta=a.local[pn][:3,:3].T@ls[pn][:3,:3]
                lm[:3,:3]=a.R.from_rotvec(-.5*a.R.from_matrix(delta).as_rotvec()).as_matrix()@a.local[n][:3,:3]
            ls[n]=lm;w[n]=w[pn]@lm
        cc=contact.copy();cc[:3,3]+=x[:3]
        return w,cc,ls
    def evaluate(x,detail=False):
        w,cc,_=candidate(x);ci=np.linalg.inv(cc);ms=np.array([w[n][:3] for n in influences]);terms=[];stats={}
        for label,inputs in clouds:
            pp=np.einsum('bnk,bjk->nj',inputs,ms);pp=pp@ci[:3,:3].T+ci[:3,3]
            gap=clearance(pp,variant)
            terms.append(np.minimum(gap-.085,0)*18)
            # Keep the nearest surface of every finger in contact, not merely
            # outside. Each digit's skinning contribution identifies its pad.
            for d in ['thumb','index','middle','ring','pinky']:
                own=[j for j,n in enumerate(influences) if n.startswith(d+'_')]
                mask=inputs[own,:,-1].sum(0)>.75
                if np.any(mask):terms.append(np.array([max(0,np.percentile(gap[mask],8)-.18)*2]))
            stats[label]={'min_clearance_cm':float(gap.min()),'vertices_inside':int(sum(gap<0))}
        terms.extend([x[:3]*.05,x[3:]*.15,x[3:6]*2.0])
        return stats if detail else np.concatenate(terms)
    # Preserve the donor's thumb opposition and closed hook. Clearance must
    # not be won by straightening that thumb away from the grip.
    bounds=np.r_[[1.6,1.6,1.2],np.deg2rad([3,5,5]+[8,16,16]*4)]
    fit=least_squares(evaluate,np.zeros(18),bounds=(-bounds,bounds),max_nfev=65,diff_step=1e-4,ftol=1e-7)
    w,cc,ls=candidate(fit.x)
    result[variant]={'offset_hand_cm':fit.x[:3].tolist(),'finger_delta':{n:a.R.from_rotvec(axes[j]*fit.x[j+3]).as_quat().tolist() for j,n in enumerate(joints)},'stats':evaluate(fit.x,True),'cost':float(fit.cost),'contact_in_hand':cc.tolist()}
    print(variant,json.dumps(result[variant]['stats']),fit.x[:3],flush=True)
    ww={n:m.copy() for n,m in world.items()}
    for n in children:ww[n]=ww['hand_r']@w[n]
    staff=ww['hand_r']@cc@a.matrix(np.eye(3),[0,0,-32])
    st=staff[:3,3].tolist()+a.R.from_matrix(staff[:3,:3]).as_quat().tolist()+[1,1,1]
    if variant=='false':views.append(('contact',ww,st))
(a.OUT/'contact-fit.json').write_text(json.dumps(result,indent=2))
lines=['#pragma once','#include "CoreMinimal.h"','// Generated by Tools/PlayerBody/fit_staff_contact20261009.py. Native Jason only.',
       '// FPS grip remains the source; bounded deltas fit the equipped surface.',
       'namespace FPSBodyStaffContactFit {','inline const FVector Offset[4]={']
for fit in result.values():lines.append('    FVector('+','.join(f'{x:.9f}' for x in fit['offset_hand_cm'])+'),')
lines.extend(['};','inline const FQuat Fingers[4][15]={'])
for fit in result.values():
    lines.append('    {')
    for q in fit['finger_delta'].values():lines.append('        FQuat('+','.join(f'{x:.10f}' for x in q)+'),')
    lines.append('    },')
lines.extend(['};','}'])
(a.ROOT/'Source/FPSGAME/Characters/FPSBodyStaffContactFit.h').write_text('\n'.join(lines)+'\n')
a.write_views(views,{**a.geos,'ue_steel_gauntlets':steel})
