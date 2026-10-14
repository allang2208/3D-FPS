"""Author small, feature-protected surface corrections; no render or test pass."""
import json
from pathlib import Path
import numpy as np
from scipy.spatial import cKDTree

O=Path(__file__).parent; (O/'Plans').mkdir(exist_ok=True)
C=json.loads((O/'Input/current.json').read_text())
def unit(a):return a/np.maximum(np.linalg.norm(a,axis=-1,keepdims=True),1e-20)
def body_slot(name):
    s=name.lower()
    return not any(x in s for x in ('interface','collar','neck')) and not (s.endswith('_1') and s.startswith(('a762_','pkm14_')))

report={'version':'RearGripSurface01-20261007','tested':False,'meshes':{}}
for key,row in C['meshes'].items():
    with (O/'Input'/(key+'.bin')).open('rb') as f:
        h=json.loads(f.readline()); nv,nt=h['vertices'],h['triangles']
        V=np.fromfile(f,'<f4',nv*3).reshape(-1,3).astype(float)
        tri=np.fromfile(f,'<i4',nt*3).reshape(-1,3)
        mat=np.fromfile(f,'<i4',nt)
        original=np.fromfile(f,'<f4',nt*9).reshape(-1,3,3).astype(float)
    # UV seams split vertices in some legacy exports. Join equal positions only
    # in the calculation graph; write the same correction to each source copy.
    source_positions=V.copy();source_nv=nv
    _,unique,source_to_calc=np.unique(np.round(V,5),axis=0,return_index=True,return_inverse=True)
    V=V[unique];nv=len(V);tri=source_to_calc[tri]
    selected=np.flatnonzero(np.isin(mat,[i for i,s in enumerate(h['slots']) if body_slot(s)]))
    T=tri[selected]; ntarget=len(T)
    if not ntarget:raise RuntimeError('No grip-body triangles '+key)
    def face_data(pos):
        p=pos[T]; cr=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
        return unit(cr),np.linalg.norm(cr,axis=1)*.5,p.mean(1)
    n0,area,cent=face_data(V)
    # Native UE winding can oppose the imported shading normal.
    orientation=np.einsum('ij,ij->i',n0,original[selected].mean(1))
    n0*=np.where(orientation<0,-1.,1.)[:,None]
    # Installation seams, open hole rims, hard creases, and all other slots stay fixed.
    edges=np.sort(np.stack((T[:,[0,1]],T[:,[1,2]],T[:,[2,0]]),1).reshape(-1,2),axis=1)
    ek=edges[:,0].astype(np.int64)*nv+edges[:,1]; order=np.argsort(ek,kind='stable'); sk=ek[order]
    _,inv,cnt=np.unique(ek,return_inverse=True,return_counts=True)
    frozen=np.zeros(nv,bool);frozen[edges[cnt[inv]!=2].ravel()]=True
    frozen[np.intersect1d(np.unique(T),np.unique(tri[~np.isin(np.arange(nt),selected)]))]=True
    pairs=np.flatnonzero(sk[1:]==sk[:-1]); fi=order//3
    crease=np.einsum('ij,ij->i',n0[fi[pairs]],n0[fi[pairs+1]])<np.cos(np.radians(42))
    frozen[edges[order[pairs[crease]]].ravel()]=True
    # Bounded neighbours avoid smoothing across the thin open frame or across slots.
    distance,near=cKDTree(cent).query(cent,k=min(32,ntarget),distance_upper_bound=.18,workers=2)
    valid=near<ntarget;near=np.minimum(near,ntarget-1)
    same=mat[selected[near]]==mat[selected,None]
    ws=np.exp(-distance**2/(2*.085**2))*area[near]*valid*same
    alignment=np.einsum('ijk,ik->ij',n0[near],n0)
    ws*=alignment>np.cos(np.radians(40))
    mean=unit((n0[near]*ws[:,:,None]).sum(1))
    spread=(np.degrees(np.arccos(np.clip(np.einsum('ijk,ik->ij',n0[near],mean),-1,1)))*ws).sum(1)/np.maximum(ws.sum(1),1e-20)
    strength=np.clip((24.-spread)/8.,0,1)
    border=cKDTree(V[frozen]).query(cent)[0] if frozen.any() else np.ones(ntarget)
    strength*=np.clip(border/.12,0,1)
    strength*=.65 if row['kind']=='phantom' else .8
    n=n0.copy()
    for _ in range(5):
        diff=np.sum((n[near]-n[:,None,:])**2,axis=2)
        w=ws*np.exp(-diff/(2*.28**2))
        n=unit((n[near]*w[:,:,None]).sum(1))
    n=unit(n0+strength[:,None]*(n-n0))
    vr=T.ravel();fr=np.repeat(np.arange(ntarget),3)
    count=np.bincount(vr,minlength=nv);vs=np.bincount(vr,strength[fr],minlength=nv)/np.maximum(count,1)
    vs[frozen]=0;pos=V.copy();cap=.008 if row['kind']=='phantom' else .012
    for _ in range(6):
        center=pos[T].mean(1)
        projection=np.einsum('ij,ij->i',n[fr],center[fr]-pos[vr])
        delta=np.zeros_like(pos)
        for axis in range(3):delta[:,axis]=np.bincount(vr,n[fr,axis]*projection,minlength=nv)/np.maximum(count,1)
        pos+=delta*vs[:,None]*.6
        offset=pos-V;length=np.linalg.norm(offset,axis=1)
        pos=V+offset*np.minimum(1,cap/np.maximum(length,1e-20))[:,None]
    # Smooth shading only within the same original normal hemisphere. Hard corners
    # retain their imported split normal; topology, every UV, colors and slots persist.
    sums=np.zeros_like(V)
    for axis in range(3):sums[:,axis]=np.bincount(vr,n[fr,axis]*area[fr],minlength=nv)
    target=unit(sums)[T];orig=unit(original[selected])
    dot=np.einsum('ijk,ijk->ij',target,orig)
    s=vs[T]*np.clip((dot-np.cos(np.radians(35)))/(1-np.cos(np.radians(35))),0,1)
    corner=unit(orig*(1-s[:,:,None])+target*s[:,:,None])
    output_positions=source_positions+(pos-V)[source_to_calc]
    moved=np.flatnonzero(np.linalg.norm(output_positions-source_positions,axis=1)>1e-7)
    changed=np.flatnonzero(np.max(np.linalg.norm(corner-orig,axis=2),axis=1)>1e-6)
    head={'key':key,'source_sha256':row['sha256'],'vertices':source_nv,'triangles':nt,'moved':len(moved),'normal_triangles':len(changed)}
    with (O/'Plans'/(key+'.bin')).open('wb') as f:
        f.write((json.dumps(head)+'\n').encode())
        for arr in (moved.astype('<i4'),output_positions[moved].astype('<f4'),selected[changed].astype('<i4'),corner[changed].astype('<f4')):arr.tofile(f)
    report['meshes'][key]={**head,'frozen_vertices':int(frozen.sum()),'max_displacement_mm':float(np.linalg.norm(pos-V,axis=1).max()*10),
                          'radius_mm':1.8,'max_allowed_displacement_mm':cap*10,'topology_changed':False,'selected_slots':[s for s in h['slots'] if body_slot(s)]}
    (O/'production.json').write_text(json.dumps(report,indent=2))
    print('REARGRIP_AUTHORED',key,'moved',len(moved),'normals',len(changed),flush=True)
