"""Fit a smooth manufactured crown around native scalp-hair envelopes.

The lower edge keeps its authored height. The chin hardware stays on the native
head. No Groom vertices, binding, materials, physics or hairstyle choices change.
"""
import csv,json,hashlib
from pathlib import Path
import numpy as np
from scipy.optimize import minimize
from scipy.spatial import cKDTree

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModernTacticalSet20261113/HelmetHairFitR1';BASE=R.parent/'HelmetDetailR1'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
manifest=list(csv.DictReader((R/'Inputs/groom-points.csv').read_text(encoding='utf-8-sig').splitlines()))
out={'profiles':{},'hair_modified':False,'runtime_tested':False}
def mapped(p,a,b):
    return (p-np.array(a['position']))@np.linalg.inv(np.array(a['axes']))@np.array(b['axes'])+b['position']

for rig in ['Jason','Kaitlin']:
    head=read(R/'Inputs'/f'{rig}_Head.json');body=read(R/'Inputs'/f'{rig}_Body.json')
    hb=head['bones']['head'];bb=body['bones']['head']
    dimension=read(BASE/f'authored-{rig}-game.json')['dimensions'];center=np.array(dimension['center']);top=dimension['top']
    previous=read(BASE/f'authored-{rig}-game.json')
    if previous['native_head']!=head['sha256']:
        raise RuntimeError('Native head changed since detailed crown author: '+rig)
    old=np.array([dimension['rx'],dimension['ry'],dimension['ry'],11.7])
    original_center=center.copy()
    hp=mapped(np.array(head['positions']),hb,bb)
    upper=hp[hp[:,2]>top-8]
    center[1]=float(np.mean(np.percentile(upper[:,1],[2,98])))
    chunks=[];sources=[]
    if rig=='Jason':
        # Native Groom transfers from the source MetaHuman face to Jason. Use
        # matching source/target surface neighborhoods to estimate rest transfer.
        # Keep an extra 0.65 cm clearance for this offline approximation.
        source=read(R/'Inputs/Jason_HairSourceHead.json')
        sp=np.array(source['positions']);tp=np.array(head['positions'])
        if len(sp)!=len(tp):raise RuntimeError('Native source/target vertex correspondence unavailable')
        delta=tp-sp
        # The target re-triangulates many of the same native quads. Vertex
        # order remains native: the indexed surfaces differ only by a small
        # local morph plus translation. Bound that morph before using it.
        correspondence_residual=float(np.linalg.norm(delta-np.median(delta,axis=0),axis=1).max())
        if correspondence_residual>.5:raise RuntimeError('Native source/target surface correspondence changed')
        tree=cKDTree(sp)
    for row in manifest:
        if row['rig']!=rig:continue
        f=R/'Inputs'/row['file'];p=np.fromfile(f,dtype='<f4').reshape(-1,3).astype(float)
        if len(p)!=int(row['points']):raise RuntimeError('Incomplete native point capture')
        if rig=='Jason':
            dist,idx=tree.query(p,k=4,workers=4);w=1/np.maximum(dist,.025)**2;w/=w.sum(axis=1,keepdims=True)
            p+=np.einsum('ij,ijk->ik',w,delta[idx])
        p=mapped(p,hb,bb);chunks.append(p)
        sources.append(dict(file=row['file'],sha256=hashlib.sha256(f.read_bytes()).hexdigest(),kind=row['kind'],lod=int(row['lod']),points=len(p)))
    hair_count=sum(len(c) for c in chunks)
    p=np.concatenate(chunks+[hp])
    # The original hairline/rim intersection defines the portion under the cap;
    # hair below this boundary remains outside and never sizes the crown.
    theta=np.arctan2((p[:,0]-center[0])/old[0],(p[:,1]-center[1])/old[1])
    rim=top-11.6+2.15*abs(np.sin(theta))**6-3.6*np.maximum(0,-np.cos(theta))**2
    under=p[:,2]>=rim-.35
    protected=p[under];q=protected-center
    # Dense source data is voxelized only for the optimizer. The final envelope
    # is expanded against every captured point, including native far LODs.
    sample=np.unique(np.round(q/.10).astype(np.int32),axis=0)*.10
    clearance=.95+(.65 if rig=='Jason' else .30)
    power=3.2
    crown_radius=float(q[:,2].max()+clearance+.40)
    def rho(x,points):
        radii=np.column_stack([np.full(len(points),x[0]),np.where(points[:,1]>=0,x[1],x[2]),np.full(len(points),x[3])])-clearance
        scaled=points/radii
        return (np.linalg.norm(scaled[:,:2],axis=1)**power+abs(scaled[:,2])**power)**(1/power)
    objective=lambda x: x[0]*(x[1]+x[2])*x[3]
    fitted=old+2;fitted[3]=crown_radius
    for iteration in range(8):
        result=minimize(objective,fitted,method='SLSQP',bounds=[(v,v+8) for v in old[:3]]+[(crown_radius,crown_radius)],constraints={'type':'ineq','fun':lambda x:1-rho(x,sample)},options={'maxiter':150,'ftol':1e-7})
        if not result.success and np.max(rho(result.x,sample))>1.0001:raise RuntimeError('Envelope fit failed for '+rig+': '+result.message)
        fitted=result.x
        # Upper-bound the cell quantization, maintaining a smooth four-radius shape.
        excess=max(1,float(rho(fitted,q).max()));fitted=clearance+(fitted-clearance)*excess+.06
        allq=p-center
        newtheta=np.arctan2(allq[:,0]/fitted[0],allq[:,1]/np.where(allq[:,1]>=0,fitted[1],fitted[2]))
        newrim=top-11.6+2.15*abs(np.sin(newtheta))**6-3.6*np.maximum(0,-np.cos(newtheta))**2
        added=(p[:,2]>=newrim-.35)&~under
        if not np.any(added):break
        under|=added;q=allq[under];sample=np.unique(np.round(q/.10).astype(np.int32),axis=0)*.10
    else:raise RuntimeError('Crown/rim envelope did not converge')
    oldq=p[under]-original_center
    oldrho=np.sqrt((oldq[:,0]/old[0])**2+(oldq[:,1]/old[1])**2+(oldq[:,2]/old[3])**2)
    newrho=rho(fitted,q)
    np.savez_compressed(R/f'{rig}-hair-envelope.npz',positions=p,under_cap=under)
    out['profiles'][rig]=dict(rx=float(fitted[0]),front_radius=float(fitted[1]),rear_radius=float(fitted[2]),rz=float(fitted[3]),clearance_cm=clearance,vertical_power=power,
        center=center.tolist(),original_center=original_center.tolist(),original_radii=old.tolist(),source_hair_points=hair_count,head_points=len(hp),source_points=len(p),cap_points=len(q),original_outside_outer_shell=int(np.count_nonzero(oldrho>1)),fitted_outside_clearance_envelope=int(np.count_nonzero(newrho>1)),max_fitted_ratio=float(newrho.max()),sources=sources,
        binding_basis='native source to target nearest-surface rest-transfer approximation; 0.65 cm additional allowance' if rig=='Jason' else 'native head Groom space, exact head bone frame',
        style='curly_fade' if rig=='Jason' else 'long_straight',bald='same head attachment; native head and chin anchors retained',runtime_tested=False)
    if rig=='Jason':out['profiles'][rig]['source_target_indexed_morph_residual_cm']=correspondence_residual
    print(rig,json.dumps({k:out['profiles'][rig][k] for k in ['rx','front_radius','rear_radius','rz','original_outside_outer_shell','fitted_outside_clearance_envelope']}),flush=True)
(R/'fit.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
