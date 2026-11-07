"""Directly join the two existing surfaces; no connector object or connector faces."""
from pathlib import Path
import bpy,bmesh,numpy as np,json
from math import tau
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24StockJunctionR2_20261105/M24_Meshy_JunctionR2.blend'),use_scripts=False)
SEAT=-.0295
CUT=-.085
BACK=-.110
SHIFT=SEAT-CUT
ATTR='FlushCornerNormal'

def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)

def preserve(ob):
    me=ob.data
    n=np.empty((len(me.loops),3),np.float32);me.corner_normals.foreach_get('vector',n.ravel())
    layer=me.attributes.new(ATTR,'FLOAT_VECTOR','CORNER');layer.data.foreach_set('vector',n.ravel())
    bm=bmesh.new();bm.from_mesh(me)
    return bm

def boundary(bm,y):
    verts=[v for v in bm.verts if abs(v.co.y-y)<2e-7]
    # Merge just the sliced rim. UV and normal discontinuities remain per corner.
    bmesh.ops.remove_doubles(bm,verts=verts,dist=3e-6)
    edges=[e for e in bm.edges if all(abs(v.co.y-y)<2e-7 for v in e.verts) and e.is_boundary]
    nodes=set(v for e in edges for v in e.verts)
    if len(edges)<12:raise RuntimeError('Missing open mating rim')
    degree={v:0 for v in nodes}
    for e in edges:
        for v in e.verts:degree[v]+=1
    if any(n!=2 for n in degree.values()):raise RuntimeError('Mating rim is branched '+str([(tuple(v.co),n) for v,n in degree.items() if n!=2][:30]))
    return edges,nodes

def table(points,center=None):
    p=np.unique(np.round(np.asarray(points),9),axis=0)
    if center is None:center=(p.min(0)+p.max(0))*.5
    theta=np.arctan2(p[:,1]-center[1],p[:,0]-center[0])%tau
    ids=np.argsort(theta)
    a,ix=np.unique(theta[ids].round(9),return_index=True)
    return a,p[ids][ix],center

def sample(tab,angle):
    a,p,c=tab;angle=np.asarray(angle)%tau
    j=np.searchsorted(a,angle,side='right')%len(a);i=(j-1)%len(a)
    d=np.stack((np.cos(angle),np.sin(angle)),axis=-1)
    edge=p[j]-p[i];q=p[i]-c
    cross=lambda x,y:x[...,0]*y[...,1]-x[...,1]*y[...,0]
    denom=cross(d,edge)
    w=np.clip(cross(q,d)/np.where(abs(denom)>1e-14,denom,1.),0,1)
    return p[i]+w[...,None]*edge

SLICE_CACHE={}
def slice_table(ob,y):
    me=ob.data
    key=ob.as_pointer()
    if key not in SLICE_CACHE:
        points=np.empty((len(me.vertices),3),np.float64);me.vertices.foreach_get('co',points.ravel())
        me.calc_loop_triangles();tri=np.empty((len(me.loop_triangles),3),np.int32)
        me.loop_triangles.foreach_get('vertices',tri.ravel());SLICE_CACHE[key]=points[tri]
    tris=SLICE_CACHE[key]
    tris=tris[(tris[:,:,1].min(1)<y)&(tris[:,:,1].max(1)>=y)]
    segments=[]
    for tri in tris:
        hit=[]
        for p,q in zip(tri,np.roll(tri,-1,axis=0)):
            if (p[1]<y<=q[1]) or (q[1]<y<=p[1]):hit.append((p+(q-p)*((y-p[1])/(q[1]-p[1])))[[0,2]])
        if len(hit)==2:segments.append(hit)
    seg=np.array(segments);c=(seg.min((0,1))+seg.max((0,1)))*.5
    angle=np.linspace(0,tau,2048,endpoint=False);d=np.stack((np.cos(angle),np.sin(angle)),axis=-1)[:,None,:]
    a=seg[None,:,0]-c;e=seg[None,:,1]-seg[None,:,0]
    cross=lambda a,b:a[...,0]*b[...,1]-a[...,1]*b[...,0]
    denom=cross(d,e);safe=np.where(abs(denom)>1e-14,denom,1e10)
    w=cross(a,d)/safe;r=cross(a,e)/safe
    r=np.max(np.where((w>=-1e-7)&(w<=1.0000001)&(r>0),r,0),axis=1)
    if np.min(r)<1e-6:raise RuntimeError('Open radial section '+ob.name)
    return angle,c+r[:,None]*d[:,0,:],c

def refine_rim(bm,y,center,angles):
    edges,_=boundary(bm,y)
    for edge in edges:
        va,vb=edge.verts
        pa=np.array([va.co.x,va.co.z]);pb=np.array([vb.co.x,vb.co.z])
        aa=np.arctan2(*(pa-center)[::-1])%tau
        ab=np.arctan2(*(pb-center)[::-1])%tau
        span=(ab-aa+np.pi)%tau-np.pi
        if abs(span)<1e-10:continue
        phase=(angles-aa+np.pi)%tau-np.pi
        wanted=angles[(phase/span>1e-6)&(phase/span<1-1e-6)]
        if not len(wanted):continue
        d=np.stack((np.cos(wanted),np.sin(wanted)),axis=-1)
        cross=lambda a,b:a[...,0]*b[...,1]-a[...,1]*b[...,0]
        denom=cross(d,pb-pa)
        ratios=cross(pa-center,d)/denom
        left=va;prev=0.
        for f in sorted(ratios[(ratios>1e-6)&(ratios<1-1e-6)]):
            _,nv=bmesh.utils.edge_split(edge,left,float((f-prev)/(1-prev)))
            edge=next(e for e in nv.link_edges if vb in e.verts)
            left=nv;prev=f

def flush_kind(kind):
    col=bpy.data.collections[kind+' | fitted to M24']
    rec=next(o for o in col.objects if o.name.startswith('Donor receiver'))
    body=next(o for o in col.objects if 'Meshy carbon stock' in o.name)
    for ob in list(col.objects):
        if ob not in (rec,body):bpy.data.objects.remove(ob,do_unlink=True)
    recbm=preserve(rec);bodybm=preserve(body)
    bmesh.ops.bisect_plane(bodybm,geom=list(bodybm.verts)+list(bodybm.edges)+list(bodybm.faces),
        plane_co=(0,CUT,0),plane_no=(0,1,0),dist=1e-8,clear_outer=True)
    _,rv=boundary(recbm,SEAT);_,bv=boundary(bodybm,CUT)
    edges,_=boundary(bodybm,CUT);seen=set();components=[]
    for v in bv:
        if v in seen:continue
        todo=[v];part=[]
        while todo:
            p=todo.pop()
            if p in seen:continue
            seen.add(p);part.append(p)
            todo.extend(e.other_vert(p) for e in p.link_edges if e in edges)
        components.append(part)
    outer=max(components,key=lambda c:np.prod(np.ptp(np.array([v.co[:] for v in c])[:,[0,2]],axis=0)))
    inner_caps=0
    for comp in components:
        if comp is outer:continue
        # Close the recessed inner cavity separately; do not stretch it onto the outer seam.
        pool=set(comp);first=comp[0];ordered=[first];prev=None;cur=first
        while True:
            nxt=next(e.other_vert(cur) for e in cur.link_edges if e in edges and e.other_vert(cur)!=prev)
            if nxt==first:break
            ordered.append(nxt);prev,cur=cur,nxt
        for v in ordered:v.co.y-=.0015
        face=bodybm.faces.new(ordered);face.material_index=0;face.smooth=False
        face.normal_update()
        if face.normal.y>0:face.normal_flip()
        layer=bodybm.loops.layers.float_vector[ATTR]
        for loop in face.loops:
            loop[layer]=(0,-1,0)
            for uv in bodybm.loops.layers.uv.values():loop[uv].uv=(loop.vert.co.x*20+.5,loop.vert.co.z*20)
        inner_caps+=1
    rt=table([(v.co.x,v.co.z) for v in rv]);st=table([(v.co.x,v.co.z) for v in outer])
    angles=np.sort(np.unique(np.round(np.r_[rt[0],st[0]],7)))
    angles=angles[np.r_[True,np.diff(angles)>2e-6]]
    refine_rim(recbm,SEAT,rt[2],angles);refine_rim(bodybm,CUT,st[2],angles)
    recbm.to_mesh(rec.data);recbm.free();rec.data.update()
    bodybm.to_mesh(body.data);bodybm.free();body.data.update()
    # Use actual source sections to reshape only the first 25 mm of carbon shell.
    # Hermite slopes are limited per coordinate: the top cannot dip into a new neck.
    grid=np.linspace(0,tau,2048,endpoint=False)
    rows=np.linspace(CUT,BACK,65)
    sections=[st if i==0 else slice_table(body,float(y)) for i,y in enumerate(rows)]
    centers=np.array([s[2] for s in sections])
    rings=np.array([sample(s,grid) for s in sections])
    start=sample(rt,grid);end=rings[-1]
    rec_next=sample(slice_table(rec,SEAT+.001),grid)
    stock_next=sample(slice_table(body,BACK-.001),grid)
    length=CUT-BACK
    delta=end-start
    da=(start-rec_next)/.001*length
    db=(stock_next-end)/.001*length
    for tangent in (da,db):
        tangent[:]=np.sign(delta)*np.minimum(np.where(tangent*delta>0,abs(tangent),0),3*abs(delta))
    alpha=np.divide(da,delta,out=np.zeros_like(da),where=abs(delta)>1e-10)
    beta=np.divide(db,delta,out=np.zeros_like(db),where=abs(delta)>1e-10)
    factor=np.maximum(1,np.sqrt(alpha*alpha+beta*beta)/3)
    da/=factor;db/=factor
    def angular(arr,a):
        f=(a%tau)/tau*len(grid);i=np.floor(f).astype(int)%len(grid);w=(f-i)[...,None]
        return arr[i]*(1-w)+arr[(i+1)%len(grid)]*w
    def transform(points):
        out=points.copy();out[:,1]+=SHIFT
        mask=points[:,1]>BACK
        if not mask.any():return out
        p=points[mask];t=np.clip((CUT-p[:,1])/length,0,1)
        f=t*(len(rows)-1);i=np.minimum(np.floor(f).astype(int),len(rows)-2);w=(f-i)[:,None]
        c=centers[i]*(1-w)+centers[i+1]*w
        a=np.arctan2(p[:,2]-c[:,1],p[:,0]-c[:,0])%tau
        j=np.floor(a/tau*len(grid)).astype(int)%len(grid);wa=(a/tau*len(grid)-j)[:,None]
        rs=rings[i,j]*(1-wa)+rings[i,(j+1)%len(grid)]*wa
        re=rings[i+1,j]*(1-wa)+rings[i+1,(j+1)%len(grid)]*wa
        src=rs*(1-w)+re*w
        t=t[:,None];t2=t*t;t3=t2*t
        dst=(2*t3-3*t2+1)*angular(start,a)+(t3-2*t2+t)*angular(da,a)+(-2*t3+3*t2)*angular(end,a)+(t3-t2)*angular(db,a)
        out[np.flatnonzero(mask)[:,None],np.array([0,2])]=p[:,[0,2]]+dst-src
        return out
    me=body.data
    points=np.empty((len(me.vertices),3),np.float64);me.vertices.foreach_get('co',points.ravel())
    old=np.empty((len(me.loops),3),np.float32);me.attributes[ATTR].data.foreach_get('vector',old.ravel())
    ids=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',ids)
    new=transform(points)
    local=points[:,1]>BACK
    indices=np.flatnonzero(local)
    eps=1e-6
    jac=np.stack([(transform(points[indices]+d)-transform(points[indices]-d))/(2*eps) for d in np.eye(3)*eps],axis=2)
    normals=old.copy();li=np.flatnonzero(local[ids])
    normals[li]=unit(np.einsum('nji,nj->ni',np.linalg.pinv(jac)[np.searchsorted(indices,ids[li])],old[li]))
    # Snap both existing polygon rims to the identical receiver polyline.
    # Their UVs remain separate corner data, but geometry becomes one welded edge.
    source_rim=np.flatnonzero(abs(points[:,1]-CUT)<2e-7)
    a=np.arctan2(points[source_rim,2]-st[2][1],points[source_rim,0]-st[2][0])%tau
    new[source_rim[:,None],[0,2]]=sample(rt,a);new[source_rim,1]=SEAT
    me.vertices.foreach_set('co',new.astype(np.float32).ravel())
    me.attributes[ATTR].data.foreach_set('vector',unit(normals).astype(np.float32).ravel());me.update()
    # Interpolate the receiver's authored corner normals onto the common seam.
    rm=rec.data;rn=np.empty((len(rm.loops),3),np.float32);rm.attributes[ATTR].data.foreach_get('vector',rn.ravel())
    sums={}
    for p in rm.polygons:
        for li in p.loop_indices:
            v=rm.vertices[rm.loops[li].vertex_index]
            if abs(v.co.y-SEAT)<2e-7:sums.setdefault(v.index,[]).append(rn[li])
    nv=list(sums);npnt=np.array([[rm.vertices[i].co.x,rm.vertices[i].co.z] for i in nv])
    na=np.arctan2(npnt[:,1]-rt[2][1],npnt[:,0]-rt[2][0])%tau
    order=np.argsort(na);na=na[order];nn=unit(np.array([np.mean(sums[i],axis=0) for i in nv]))[order]
    def seam_normal(a):
        return unit(np.column_stack([np.interp(a,na,nn[:,j],period=tau) for j in range(3)]))
    for ob in (rec,body):
        m=ob.data;co=np.empty((len(m.vertices),3),np.float64);m.vertices.foreach_get('co',co.ravel())
        ix=np.empty(len(m.loops),np.int32);m.loops.foreach_get('vertex_index',ix)
        ns=np.empty((len(m.loops),3),np.float32);m.attributes[ATTR].data.foreach_get('vector',ns.ravel())
        mask=abs(co[ix,1]-SEAT)<2e-7
        pos=co[ix[mask]]
        ns[mask]=seam_normal(np.arctan2(pos[:,2]-rt[2][1],pos[:,0]-rt[2][0])%tau)
        m.attributes[ATTR].data.foreach_set('vector',unit(ns).astype(np.float32).ravel())
        ob.hide_set(False);ob.hide_render=False
    bpy.ops.object.select_all(action='DESELECT')
    rec.select_set(True);body.select_set(True);bpy.context.view_layer.objects.active=rec
    bpy.ops.object.join()
    rec.name='SM_M24_CarbonSpine_'+kind
    bm=bmesh.new();bm.from_mesh(rec.data)
    seamverts=[v for v in bm.verts if abs(v.co.y-SEAT)<2e-7]
    before=len(seamverts)
    bmesh.ops.remove_doubles(bm,verts=seamverts,dist=2e-7)
    seam_edges=[e for e in bm.edges if all(abs(v.co.y-SEAT)<2e-7 for v in e.verts)]
    open_seam=[e for e in seam_edges if len(e.link_faces)!=2]
    if open_seam:raise RuntimeError('Direct seam needs topology repair: '+str((kind,len(seam_edges),len(open_seam),[(tuple(e.verts[0].co),tuple(e.verts[1].co),len(e.link_faces)) for e in open_seam[:8]])))
    bm.to_mesh(rec.data);bm.free();rec.data.update()
    ns=np.empty((len(rec.data.loops),3),np.float32);rec.data.attributes[ATTR].data.foreach_get('vector',ns.ravel())
    rec.data.normals_split_custom_set(unit(ns).tolist());rec.data.attributes.remove(rec.data.attributes[ATTR])
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(rec.name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',use_tspace=True,add_leaf_bones=False,bake_anim=False,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    return {'stock_forward_mm':SHIFT*1000,'shared_seam_y_mm':SEAT*1000,'carbon_local_fit_length_mm':length*1000,
        'old_connector_removed':True,'added_connector_faces':0,'recessed_inner_caps':inner_caps,'seam_vertices_before_weld':before,
        'seam_vertices_after_weld':sum(abs(v.co.y-SEAT)<2e-7 for v in rec.data.vertices),
        'source_shoulder_y_mm':-361.5991175,'new_shoulder_y_mm':-361.5991175+SHIFT*1000,
        'source_mesh':'Meshy_AI_Carbon_Stock_1105135808_texture.glb'}

records={kind:flush_kind(kind) for kind in ('Native','Advanced')}
for ob in bpy.data.collections['Advanced | fitted to M24'].objects:ob.hide_set(True);ob.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Carbon_DirectFlush.blend'),compress=True)
(O/'construction.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print('M24_DIRECT_FLUSH_AUTHORED',records)
