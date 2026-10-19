"""Requested offline waist/hip comparison; no game or rendering session is started."""
import json
from pathlib import Path
import numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BlueMageRobe20261018';OUT=R/'HipFit20261019';report={}
def load(p):return json.loads(p.read_text())
def proxy(d):return np.array(d['positions'])[np.unique(np.array(d['triangles'])[np.array(d['triangle_materials'])==9])]
def collision_distance(points,d,new):
    bones=d['bones'];result=np.full(len(points),1.e6);jason=d['profile'].startswith('Jason')
    for side in ('l','r'):
        hip=np.array(bones['thigh_'+side]['position']);knee=np.array(bones['calf_'+side]['position'])
        if not new:caps=[(hip,knee,12.8 if jason else 11.4,12.8 if jason else 11.4)]
        else:
            inward=-.9 if jason else 0.;caps=[]
            for depth in ((-3.8,2.6) if jason else (-2.,1.3)):
                a=hip+(knee-hip)*.12+[np.sign(hip[0])*inward,depth,0];b=hip+(knee-hip)*.95+[np.sign(hip[0])*inward,depth*.6,0];caps.append((a,b,7.1 if jason else 7.7,5.1 if jason else 5.4))
        for a,b,ra,rb in caps:
            t=np.linspace(0,1,129);centers=a+(b-a)*t[:,None];r=ra+(rb-ra)*t;dist=np.linalg.norm(points[:,None,:]-centers[None,:,:],axis=-1)-r[None,:];result=np.minimum(result,dist.min(1))
    return result-(.35 if new else .65)*d['cloth_dimensions']['scale']
for name in ('Body','Body_Owner','Jason','Jason_Owner'):
    old=load(OUT/'Before'/(name+'.json'));new=load(R/'Authored/Body'/(name+'.json'));a,b=np.array(old['positions']),np.array(new['positions']);faces=np.array(new['triangles']);mats=np.array(new['triangle_materials']);skirt=np.unique(faces[mats==4]);dims=new['cloth_dimensions'];waist=dims['waist_cm'];hip=new['bones']['thigh_l']['position'][2];hem=dims['hem_cm'];affected=np.unique(faces[np.isin(mats,[4,9])]);other=np.setdiff1d(np.arange(len(b)),affected)
    sections=[]
    for z in (waist,waist-5,waist-10,hip,hip-10,new['bones']['calf_l']['position'][2]):
        row={'z':round(z,2)}
        for label,p in [('before',a),('after',b)]:
            pp=p[skirt];pp=pp[np.abs(pp[:,2]-z)<1.3];row[label]=dict(halfwidth=round(float(np.max(np.abs(pp[:,0]))),2),depth=np.round([pp[:,1].min(),pp[:,1].max()],2).tolist())
        sections.append(row)
    q0,q1=proxy(old),proxy(new);inside0=collision_distance(q0,old,False);inside1=collision_distance(q1,new,True);upper=q1[:,2]>hip-15
    root=affected[np.abs(a[affected,2]-waist)<1.e-6];edge=affected[np.abs(a[affected,2]-hem)<1.e-6]
    result=dict(sections=sections,upper_thigh_collision_before=dict(vertices=int(np.sum(inside0[upper]<0)),max_penetration_cm=round(float(max(0,-inside0[upper].min())),3)),upper_thigh_collision_after=dict(vertices=int(np.sum(inside1[upper]<0)),max_penetration_cm=round(float(max(0,-inside1[upper].min())),3)),root_seam_shift_cm=float(np.linalg.norm(a[root]-b[root],axis=1).max()),hem_shift_cm=float(np.linalg.norm(a[edge]-b[edge],axis=1).max()),other_geometry_shift_cm=float(np.linalg.norm(a[other]-b[other],axis=1).max()),topology_unchanged=old['triangles']==new['triangles'],weights_unchanged=old['weights']==new['weights'],uv_unchanged=old['uv']==new['uv'],finite=bool(np.isfinite(b).all()),runtime_tested=False)
    report[name]=result
    print(name,json.dumps(result,ensure_ascii=False),flush=True)
(OUT/'geometry-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
