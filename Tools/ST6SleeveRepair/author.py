"""Rebuild ST6 sleeves directly on each saved native arm, with a paired lining.

Keep original arm topology/binding through elbow twists. Wrist and shoulder
boundaries are explicit annuli; no global hole fill and no donor-pose warp.
"""
import json,copy,math,hashlib
from pathlib import Path
import bpy,bmesh,numpy as np
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ST6SleeveRepair20261018';OUT=R/'Authored';OUT.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def unit(v):return v/max(float(np.linalg.norm(v)),1e-10)
def smooth(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def normals(p,f):
    n=np.zeros_like(p);cross=-np.cross(p[f[:,1]]-p[f[:,0]],p[f[:,2]]-p[f[:,0]])
    for k in range(3):np.add.at(n,f[:,k],cross)
    return n/np.maximum(np.linalg.norm(n,axis=1)[:,None],1e-12)
def build(row):
    s=read(Path(row['file']));bones=s['bones'];names=sorted(bones);p0=np.array(s['positions']);side_of=[max(('l','r'),key=lambda side:sum(w for n,w in ws.items() if n.endswith('_'+side))) for ws in s['weights']]
    d=dict(profile=row['profile'],binding_source=s['source'],bones=bones,skeleton=s['skeleton'],positions=[],triangles=[],uv=[],normals=[],weights=[],triangle_materials=[],parts=[],contract='ST6NativeSleeves20261018: actual native arm topology and paired skin weights; explicit cuff/shoulder rims; closed cuff turned facing; no donor pose warp; protected 3 LOD topology')
    evidence=dict(profile=row['profile'],native=s['source'],source_sha256=s['asset_sha256'],arms={})
    for side in ('l','r'):
        faces=[f for f in s['triangles'] if all(side_of[i]==side for i in f)]
        if not faces:continue
        a=np.array(bones['upperarm_'+side]['position']);e=np.array(bones['lowerarm_'+side]['position']);w=np.array(bones['hand_'+side]['position']);upper=unit(e-a);lower=unit(w-e);upper_len=np.linalg.norm(e-a)
        # Native hands are included only to obtain a continuous wrist transition;
        # the wrist plane removes the entire palm and every finger.
        bm=bmesh.new();deform=bm.verts.layers.deform.verify();ids=sorted({i for f in faces for i in f});verts={i:bm.verts.new(p0[i]) for i in ids}
        for i,v in verts.items():
            for n,value in s['weights'][i].items():v[deform][names.index(n)]=value
        for f in faces:bm.faces.new([verts[i] for i in f])
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0001)
        for co,no in [(a+upper,upper),(w-lower*1.0,-lower)]:bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=Vector(co),plane_no=Vector(no),clear_inner=True,clear_outer=False)
        # A true band boundary avoids a sawtooth material edge across arm faces.
        bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.00001,plane_co=Vector(w-lower*3.8),plane_no=Vector(lower),clear_inner=False,clear_outer=False)
        bmesh.ops.triangulate(bm,faces=list(bm.faces));bm.verts.ensure_lookup_table();bm.verts.index_update()
        p=np.array([list(v.co) for v in bm.verts]);f=np.array([[v.index for v in face.verts] for face in bm.faces]);ws=[]
        for v in bm.verts:
            pairs=sorted(((names[i],float(x)) for i,x in v[deform].items() if x>1e-8),key=lambda x:-x[1])[:8];den=sum(x for _,x in pairs);ws.append({n:x/den for n,x in pairs})
        boundary=[(ed.link_loops[0].vert.index,ed.link_loops[0].link_loop_next.vert.index) for ed in bm.edges if ed.is_boundary];bm.free()
        n=normals(p,f);dist=-(p-w)@lower;seed=unit(np.cross(upper,lower))
        if np.linalg.norm(seed)<.5:
            seed=np.array([0.,1.,0.]);seed=unit(seed-upper*(seed@upper))
        longitudinal=(p-e)@lower;blend=smooth((longitudinal+4)/8);axis=(1-blend[:,None])*upper+blend[:,None]*lower;axis/=np.linalg.norm(axis,axis=1)[:,None]
        cross=np.cross(axis,seed);q=p-e;theta=np.arctan2(np.einsum('ij,ij->i',q,cross),q@seed);along=upper_len+np.einsum('ij,ij->i',q,axis)
        cuff=1-smooth((dist-3.0)/2.8);elbow=np.exp(-(longitudinal/5.)**2)
        folds=(.07*np.sin(dist*1.65+np.sin(theta*2)*.8)+.045*np.sin(dist*.81-theta*3))*(1-cuff)*(.3+.7*elbow)
        clearance=.34+.25*(1-cuff)+folds;thickness=.12
        outer=p+n*clearance[:,None];inner=p+n*(clearance-thickness)[:,None]
        start=len(d['positions']);count=len(p);d['positions'].extend(outer.tolist()+inner.tolist());d['weights'].extend(ws+copy.deepcopy(ws));start_tri=len(d['triangles'])
        # 25 cm physical UV field, with continuous elbow basis and unwrapped seam.
        uv=np.column_stack((theta/(2*math.pi),along/25))
        for face in f:
            coords=uv[face].copy()
            if np.ptp(coords[:,0])>.5:coords[coords[:,0]<0,0]+=1
            coords[:,0]*=1.5
            is_cuff=dist[face].mean()<3.8
            if is_cuff:coords[:,1]=dist[face]/25
            for local,tex,mat in [(face,coords,1 if is_cuff else 0),(face[::-1]+count,coords[::-1],2)]:
                d['triangles'].append((local+start).tolist());d['uv'].append(tex.tolist());d['triangle_materials'].append(mat)
        rim_count=0
        for i,j in boundary:
            # One quad between corresponding surfaces; never a disk across the opening.
            ids=[j+start,i+start,i+start+count,j+start+count];length=np.linalg.norm(p[i]-p[j]);tex=[[0,0],[length/25,0],[length/25,thickness/25],[0,thickness/25]]
            for tri in [(0,1,2),(0,2,3)]:d['triangles'].append([ids[k] for k in tri]);d['uv'].append([tex[k] for k in tri]);d['triangle_materials'].append(1);rim_count+=1
        d['parts'].append(dict(name='NativeSleeve_'+side,first_vertex=start,vertices=count*2,first_triangle=start_tri,triangles=len(d['triangles'])-start_tri))
        # Curved double topstitch follows the outer cloth at the cuff, represented
        # in the material field; the cuff's thickness and return are geometry.
        evidence['arms'][side]=dict(surface_vertices=count,surface_triangles=len(f),boundary_edges=len(boundary),cuff_end_from_wrist_cm=1.,outer_clearance_cm=[float(clearance.min()),float(clearance.max())],thickness_cm=thickness,paired_weights=True,rim_triangles=rim_count)
    p=np.array(d['positions']);f=np.array(d['triangles']);d['normals']=normals(p,f)[f].tolist()
    edges=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),axis=1);_,counts=np.unique(edges,axis=0,return_counts=True)
    evidence['construction']=dict(finite=bool(np.isfinite(p).all() and np.isfinite(d['normals']).all()),open_edges=int(np.count_nonzero(counts==1)),nonmanifold_edges=int(np.count_nonzero(counts>2)),duplicate_triangles=int(len(f)-len(np.unique(np.sort(f,axis=1),axis=0))),max_edge_cm=float(np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1).max()))
    if not evidence['construction']['finite'] or evidence['construction']['nonmanifold_edges'] or evidence['construction']['duplicate_triangles']:raise RuntimeError('Invalid sleeve construction: '+row['profile'])
    file=OUT/(row['profile']+'.json');file.write_text(json.dumps(d,separators=(',',':')),encoding='utf-8');evidence.update(vertices=len(p),triangles=len(f),author_sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    print('ST6_NATIVE_SLEEVE_AUTHORED',row['profile'],len(p),len(f),flush=True);return evidence
if __name__=='__main__':
    report={row['profile']:build(row) for row in read(R/'before.json')['inventory']};(R/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
