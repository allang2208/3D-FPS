"""Fit the ranger hem to the actual leather waist in native crouch poses.

Run in Blender background. Only native Jason torso/owner variants are changed.
"""
import copy,gc,json,math,sys
from pathlib import Path
import numpy as np
from mathutils import Matrix,Quaternion,Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/RangerCrouchFit20261021'
sys.path.insert(0,str(P/'Tools/BlueMageRobe'))
from geometry import normals,norm_weights,blend_weights
from geometry import boundary
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8')
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def waist_weights(p):
    # The waistband follows the pelvis/low spine. Corrective thigh bones belong
    # below the hip, otherwise separate clothes pull apart during deep flexion.
    x,y,z=p;spine=.35*float(smooth((z-92.)/8.2));leg=.78*float(smooth(y/9.))*(1-float(smooth((z-80.)/14.)))
    left=float(smooth((x+3.)/6.))
    return norm_weights({'pelvis':(1-spine)*(1-leg),'spine_01':spine*(1-leg),'thigh_l':leg*left,'thigh_r':leg*(1-left)})
def bary(p,tri):
    a,b=tri[1]-tri[0],tri[2]-tri[0];v=p-tri[0];aa,ab,bb=a@a,a@b,b@b;den=max(aa*bb-ab*ab,1e-12)
    y=(bb*(v@a)-ab*(v@b))/den;z=(aa*(v@b)-ab*(v@a))/den;r=np.maximum([1-y-z,y,z],0);return r/max(r.sum(),1e-12)
def canonical(d):
    if isinstance(d['bones'],list):
        d=copy.deepcopy(d);names={b['index']:b['name'] for b in d['bones']};d['bones']={b['name']:{k:v for k,v in b.items() if k!='name'} for b in d['bones']};d['weights']=[{names[i]:w for i,w in row} for row in d['weights']]
    return d
def matrix(b):
    m=np.eye(4);m[:3,:3]=np.array(b['axes']).T;m[:3,3]=b['position'];return m
def pose_matrix(t):
    x,y,z,w=t['q'];m=np.eye(4);m[:3,:3]=np.array(Quaternion((w,x,y,z)).to_matrix())@np.diag(t.get('s',[1,1,1]));m[:3,3]=t['p'];return m
def transforms(d,frame):return {n:pose_matrix(frame[n])@np.linalg.inv(matrix(b)) for n,b in d['bones'].items() if n in frame}
def skinned(p,ws,trans):
    out=np.zeros_like(p);names=set().union(*ws)
    for n in names:
        w=np.array([row.get(n,0) for row in ws]);ids=np.flatnonzero(w)
        m=trans[n];out[ids]+=(p[ids]@m[:3,:3].T+m[:3,3])*w[ids,None]
    return out
def exterior(d):
    p=np.array(d['positions']);f=np.array(d['triangles']);mid=p[f].mean(1);keep=np.zeros(len(f),bool);first=0
    # The continuous outer cloth sheet defines inside/outside. Open decorative
    # stitch tubes and ribbon end caps cannot supply a volume sign.
    for part in d['parts']:
        if part['name'] in ('Leather_WaistAndSeat','Leather_Leg_L','Leather_Leg_R'):keep[first:first+part['triangles']]=True
        first+=part['triangles']
    return f[keep]
def skin_mask(d):
    p=np.array(d['positions']);mass=np.array([sum(w for n,w in row.items() if any(a in n for a in ('arm','hand','wrist','thumb','index','middle','ring','pinky'))) for row in d['weights']])
    return (p[:,2]<107)&(abs(p[:,0])<24)&(mass<.08)
def surfaces(d,frames):
    fs=exterior(d);ids=np.unique(fs);mp=np.full(len(d['positions']),-1,int);mp[ids]=np.arange(len(ids));fs=mp[fs];p=np.array(d['positions'])[ids];ws=[d['weights'][i] for i in ids];out=[]
    out.append(('Reference',closed_volume(p,fs),None))
    for name,frame in frames:
        tr=transforms(d,frame);posed=skinned(p,ws,tr);out.append((name,closed_volume(posed,fs),frame))
    return out
def closed_volume(p,fs):
    # Close only the analysis volume's waist/lower boundaries. No caps are added
    # to the actual garment. A parity test distinguishes real inside points from
    # the negative halfspace of a nearby concave/corrective fold.
    _,first,inverse=np.unique(np.round(p,5),axis=0,return_index=True,return_inverse=True);p=p[first];fs=inverse[fs];adj={}
    for a,b in boundary(fs):adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
    left=set(adj);vertices=p.tolist();faces=fs.tolist()
    while left:
        start=next(iter(left));ring=[start];previous=None;cur=start
        while True:
            nxt=next((n for n in adj[cur] if n!=previous),None)
            if nxt is None or nxt==start or nxt in ring:break
            ring.append(nxt);previous,cur=cur,nxt
        left.difference_update(ring)
        if len(ring)>2:
            center=len(vertices);vertices.append(p[ring].mean(0).tolist())
            faces.extend([[center,a,b] for a,b in zip(ring,ring[1:]+ring[:1])])
    return BVHTree.FromPolygons([Vector(v) for v in vertices],faces,all_triangles=True)
def inside(tree,q):
    votes=0
    for raw in ((.372831,.619173,.691277),(-.71631,.28371,.51927),(.24917,-.84131,.47689)):
        direction=Vector(raw).normalized();origin=Vector(q);count=0
        for _ in range(32):
            hit,_,_,_=tree.ray_cast(origin,direction,250)
            if hit is None:break
            count+=1;origin=hit+direction*.003
        votes+=count%2
    return votes>=2
def gaps(d,surfaces,selected=None):
    p=np.array(d['positions']);mask=skin_mask(d)&(p[:,2]<100.2)
    # Outer cloth faces are authoritative; skin and lining do not count as visible penetration.
    f=np.array(d['triangles']);slots=np.array(d['triangle_materials']);outer=np.unique(f[np.isin(slots,[0,1,3,4])]);mask &= np.isin(np.arange(len(p)),outer)
    ids=np.flatnonzero(mask) if selected is None else selected;pp=p[ids];ww=[d['weights'][i] for i in ids];report=[]
    for name,tree,frame in surfaces:
        posed=pp if frame is None else skinned(pp,ww,transforms(d,frame));ds=[]
        for q in posed:
            hit,n,_,_=tree.find_nearest(Vector(q));distance=float(np.linalg.norm(q-np.array(hit)));ds.append(-distance if inside(tree,q) else distance)
        a=np.array(ds);worst=np.argsort(a)[:6]
        report.append(dict(pose=name,samples=len(a),penetrating=int(sum(a<-.025)),min_signed_clearance_cm=float(a.min()),p05_cm=float(np.quantile(a,.05)),median_cm=float(np.median(a)),worst_vertices=[dict(vertex=int(ids[j]),rest=pp[j].tolist(),posed=posed[j].tolist(),gap=float(a[j]),weights=ww[j]) for j in worst]))
    return report
def source_match(source,live):
    ps=np.array(source['positions']);kd=KDTree(len(ps))
    for i,p in enumerate(ps):kd.insert(Vector(p),i)
    kd.balance();poserror=0.;weighterror=0.
    for vi,w in live['waist_weights'].items():
        co,idx,dist=kd.find(Vector(live['positions'][int(vi)]));poserror=max(poserror,dist);other=source['weights'][idx];weighterror=max(weighterror,max(abs(w.get(n,0)-other.get(n,0)) for n in set(w)|set(other)))
    return dict(max_position_error_cm=poserror,max_weight_error=weighterror,live_triangles=len(live['triangles']),source_triangles=len(source['triangles']))

def fit_hem(source,pants):
    d=copy.deepcopy(source);p=np.array(d['positions']);old=p.copy();mask=skin_mask(d);ids=np.flatnonzero(mask)
    source_faces=np.array(source['triangles']);source_slots=np.array(source['triangle_materials'])
    outer=source_faces[np.isin(source_slots,[0,1])]
    garment=BVHTree.FromPolygons([Vector(v) for v in old],outer.tolist(),all_triangles=True)
    pp=np.array(pants['positions']);ff=exterior(pants);tree=BVHTree.FromPolygons([Vector(v) for v in pp],ff.tolist(),all_triangles=True)
    ns=normals(pp,ff);weights=d['weights'];changed=0;transfer_tri=[];transfer_bc=[]
    for i in ids:
        anchor,_,_,_=garment.find_nearest(Vector(old[i]));anchor=np.array(anchor);q=anchor.copy();q[2]+=2.0*(1-float(smooth((q[2]-81.2)/13.5)))
        z=min(q[2],99.6);origin=np.array([0.,.8,z]);radial=np.r_[q[:2]-origin[:2],0.];radius=np.linalg.norm(radial);radial/=max(radius,1e-9)
        hit,n,fi,_=tree.ray_cast(Vector(origin+radial*50),Vector(-radial),50)
        if hit is None:raise RuntimeError('Waist fitting ray missed '+str(q))
        hit=np.array(hit);target_radius=(hit-origin)@radial+1.2
        fade=1-float(smooth((q[2]-99.2)/7.6));offset=max(0,target_radius-radius)*fade
        q+=radial*offset;p[i]=old[i]+q-anchor
        tri=ff[fi];bc=bary(hit,pp[tri]);borrowed=norm_weights({n:sum(pants['weights'][j].get(n,0)*a for j,a in zip(tri,bc)) for n in set().union(*(pants['weights'][j] for j in tri))})
        transfer_tri.append(tri);transfer_bc.append(bc)
        blend=1-float(smooth((q[2]-98.)/7.));weights[i]=blend_weights(weights[i],borrowed,blend)
        changed+=offset>1e-6
    # Keep the author's non-waist normals byte-for-byte. Within the edited region,
    # weld only the normal calculation, never UVs or actual mesh vertices.
    fs=np.array(d['triangles']);cross=-np.cross(p[fs[:,1]]-p[fs[:,0]],p[fs[:,2]]-p[fs[:,0]]);vn=np.zeros_like(p)
    for k in range(3):np.add.at(vn,fs[:,k],cross)
    _,inv=np.unique(np.round(p,5),axis=0,return_inverse=True);weld=np.zeros((inv.max()+1,3));np.add.at(weld,inv,vn);vn=weld[inv];vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
    for fi in np.flatnonzero(np.any(mask[fs],axis=1)):d['normals'][fi]=vn[fs[fi]].tolist()
    d['positions']=p.tolist();d['contract']+='; RangerCrouchFit20261021: waist radial envelope +1.2cm; smooth mobility hem raised up to4.5cm; paired lining/details; shared pelvis/low-spine waist weights blended to original torso from100.2 to106.8cm'
    d['crouch_waist_fit']=dict(clearance_cm=1.2,hem_lift_max_cm=4.5,hem_lift_fade_z_cm=[81.2,94.7],weight_blend_z_cm=[100.2,106.8],shape_blend_z_cm=[99.2,106.8],changed_position_vertices=int(changed),rebound_vertices=len(ids),max_rest_displacement_cm=float(np.linalg.norm(p-old,axis=1).max()),pants_reference='TrouserFit20261018/Jason_LeatherPants')
    np.savez(R/(d['profile']+'_transfer.npz'),ids=ids,triangles=np.array(transfer_tri),barycentric=np.array(transfer_bc))
    return d

def underlayer(source,profile):
    d=canonical(source);keep=[];parts=[];first=0;removed=[]
    for part in d['parts']:
        name=part['name'];hidden=name in ('LeatherWaistband','LeatherBelt','LeatherFly','FlySeam') or name.startswith(('WaistSeam_','BeltLoop_','WaistBuckle','InsetPocket_'))
        if hidden:removed.append(name)
        else:keep.extend(range(first,first+part['triangles']));parts.append(part)
        first+=part['triangles']
    f=np.array(d['triangles'])[keep];used=np.unique(f);mp=np.full(len(d['positions']),-1,int);mp[used]=np.arange(len(used))
    for key in ('positions','weights','colors'):
        if key in d:d[key]=[d[key][i] for i in used]
    for key in ('normals','uv','triangle_materials'):d[key]=[d[key][i] for i in keep]
    d['triangles']=mp[f].tolist();d['parts']=parts;d['profile']=profile;d['binding_source']=d['source']
    changed=0
    d['contract']+='; RangerCrouchFit20261021: shirt-specific underlayer omits fully covered waistband/belt/loops/buckle; complete waist/seat shell retained; pelvis/low-spine waist band with smooth thigh transition from 70 to80cm; existing cuff fit retained'
    d['hidden_under_ranger_top']=removed
    d['waist_binding']=dict(rebound_vertices=changed,thigh_transition_z_cm=[70,80],pelvis_band_z_cm=[80,92],spine_blend_z_cm=[92,100.2])
    return d

def relax_crouch_envelope(d,surfaces):
    """Bake a smooth rest-space clearance field across the sampled native poses.

    One angular/height field moves cloth, lining and stitches together. There is
    no runtime collision solver and no independent point-by-point bulging.
    """
    p=np.array(d['positions']);original=p.copy();mask=skin_mask(d);ids=np.flatnonzero(mask);pp=p[ids];ws=[d['weights'][i] for i in ids]
    faces=np.array(d['triangles']);slots=np.array(d['triangle_materials']);outer=np.unique(faces[np.isin(slots,[0,1,3,4])]);constraints=np.flatnonzero((pp[:,2]<100.15)&np.isin(ids,outer))
    radial=pp-np.c_[np.zeros(len(pp)),np.full(len(pp),.8),pp[:,2]];radial/=np.maximum(np.linalg.norm(radial,axis=1,keepdims=True),1e-12)
    theta=np.mod(np.arctan2(radial[:,0],radial[:,1]),math.tau);gx=theta/math.tau*96;gy=np.clip((pp[:,2]-80)/28*79,0,78.999)
    ix=np.floor(gx).astype(int);iy=np.floor(gy).astype(int);tx=gx-ix;ty=gy-iy;total=np.zeros(len(ids));steps=[]
    prepared=[(name,tree,None if frame is None else transforms(d,frame)) for name,tree,frame in surfaces]
    for iteration in range(3):
        needed=np.zeros(len(ids));bad=0;backfacing=0
        for name,tree,trans in prepared:
            if trans is None:posed=pp;direction=radial
            else:
                posed=skinned(pp,ws,trans);direction=np.zeros_like(radial)
                for n in set().union(*ws):
                    w=np.array([r.get(n,0) for r in ws]);used=np.flatnonzero(w);direction[used]+=(radial[used]@trans[n][:3,:3].T)*w[used,None]
            for j in constraints:
                q=posed[j]
                hit,n,_,_=tree.find_nearest(Vector(q));outward=-np.array(n);gap=float((q-np.array(hit))@outward)
                if gap>=.20:continue
                slope=float(direction[j]@outward)
                if gap<-.025:bad+=1
                if slope>.12:needed[j]=max(needed[j],min(.55,(.24-gap)/slope))
                elif gap<-.025:backfacing+=1
        if not np.any(needed>.005):break
        field=np.zeros((80,96));np.maximum.at(field,(iy,ix),needed)
        # Envelope dilation fills the narrow angular gap between thread and
        # cloth vertices. A smooth field preserves the original fine details.
        padded=field.copy()
        for dy in (-2,-1,0,1,2):
            for dx in (-1,0,1):padded=np.maximum(padded,np.roll(np.pad(field,((2,2),(0,0)),mode='edge')[2+dy:82+dy],dx,axis=1))
        field=padded
        for _ in range(3):
            field=.5*field+.25*(np.roll(field,1,1)+np.roll(field,-1,1))
            field=.5*field+.25*(np.r_[field[:1],field[:-1]]+np.r_[field[1:],field[-1:]])
        push=(field[iy,ix]*(1-tx)*(1-ty)+field[iy,(ix+1)%96]*tx*(1-ty)+field[iy+1,ix]*(1-tx)*ty+field[iy+1,(ix+1)%96]*tx*ty)
        push*=1-smooth((pp[:,2]-101)/6);pp+=radial*push[:,None];total+=push
        steps.append(dict(iteration=iteration+1,penetrating_before=bad,nonradial_contacts=backfacing,max_step_cm=float(push.max())))
        print('CROUCH_CLEARANCE_SCULPT',d['profile'],steps[-1],flush=True)
    p[ids]=pp;d['positions']=p.tolist();fs=np.array(d['triangles']);cross=-np.cross(p[fs[:,1]]-p[fs[:,0]],p[fs[:,2]]-p[fs[:,0]]);vn=np.zeros_like(p)
    for k in range(3):np.add.at(vn,fs[:,k],cross)
    _,inv=np.unique(np.round(p,5),axis=0,return_inverse=True);weld=np.zeros((inv.max()+1,3));np.add.at(weld,inv,vn);vn=weld[inv];vn/=np.maximum(np.linalg.norm(vn,axis=1,keepdims=True),1e-12)
    for fi in np.flatnonzero(np.any(mask[fs],axis=1)):d['normals'][fi]=vn[fs[fi]].tolist()
    d['crouch_waist_fit']['pose_envelope_sculpt']=dict(samples=len(surfaces),max_additional_clearance_cm=float(total.max()),steps=steps)
    return d

def main():
    inputs=read(R/'inputs.json');shirt=read(inputs['sources']['Jason']['file']);pants=canonical(read(P/'SourceAssets/TrouserFit20261018/Jason_LeatherPants.json'))
    frames=[(k+'@'+str(i),s['bones']) for k,v in inputs['clips'].items() for i,s in enumerate(v['samples'])]
    match=dict(shirt=source_match(shirt,read(R/'Jason_live_mesh.json')),pants=source_match(pants,read(R/'Pants_live_mesh.json')))
    # Numeric comparison of saved/active geometry is necessary: UE metadata tags
    # may be absent after a reload, and are not sufficient version evidence.
    write(R/'source_match.json',match);print('ACTIVE_SOURCE_MATCH',json.dumps(match),flush=True)
    p=np.array(shirt['positions']);m=skin_mask(shirt)&(p[:,2]<97);ids=np.flatnonzero(m)
    weight_summary={}
    for label,d in [('shirt',shirt),('pants',pants)]:
        pp=np.array(d['positions']);ii=np.flatnonzero((pp[:,2]>=81)&(pp[:,2]<97)&(abs(pp[:,0])<23));sums={}
        for i in ii:
            for n,w in d['weights'][i].items():sums[n]=sums.get(n,0)+w/len(ii)
        weight_summary[label]=dict(sorted(sums.items(),key=lambda r:-r[1])[:16])
    write(R/'diagnosis.json',dict(active_sources=match,weight_summary=weight_summary,geometry_check='surface_check.json uses actual triangle intersections; capped-volume experiments are not acceptance evidence'))
    if max(match[k]['max_position_error_cm'] for k in match)>.001 or max(match[k]['max_weight_error'] for k in match)>.001:raise RuntimeError('Loaded geometry differs from author source; do not overwrite')
    rows=[];underlayers={}
    for profile,stem in [('LeatherPants','Jason_LeatherPants'),('LeatherPants_ShortBootsFit','Jason_LeatherPants_ShortBootsFit'),('LeatherPants_HighBootsFit','Jason_LeatherPants_HighBootsFit')]:
        original=read(P/'SourceAssets/TrouserFit20261018'/(stem+'.json'));d=underlayer(original,profile);out=R/'Authored/ue_leather_pants'/(profile+'.json');write(out,d);underlayers[profile]=d
        rows.append(dict(item='ue_leather_pants',profile=profile,file=str(out),hidden_parts=d['hidden_under_ranger_top'],vertices=len(d['positions']),triangles=len(d['triangles'])))
    pants=underlayers['LeatherPants']
    for profile in ('Jason','Owner_Jason'):
        source=shirt if profile=='Jason' else read(inputs['sources'][profile]['file']);d=fit_hem(source,pants)
        out=R/'Authored/ue_field_sweater'/(profile+'.json');write(out,d)
        rows.append(dict(item='ue_field_sweater',profile=profile,file=str(out),fit=d['crouch_waist_fit']))
        print('FITTED_HEM',json.dumps(rows[-1]),flush=True);del d;gc.collect()
    write(R/'authored.json',dict(completed=True,records=rows,scope='Jason world and owner torso plus three shirt-specific leather underlayers',crouch_samples=36,reference_sample=True,gameplay_tested=False))

if __name__=='__main__':main()
