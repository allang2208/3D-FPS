"""Attribute-preserving cuts and boundary walks; never sort a rim by polar angle."""
import bpy,bmesh,numpy as np
ATTR='M24SavedNormal'
def unit(n):return n/np.maximum(np.linalg.norm(n,axis=-1,keepdims=True),1e-12)
def preserve(ob):
    me=ob.data
    if ATTR not in me.attributes:
        ns=np.empty((len(me.loops),3),np.float32);me.corner_normals.foreach_get('vector',ns.ravel())
        me.attributes.new(ATTR,'FLOAT_VECTOR','CORNER').data.foreach_set('vector',ns.ravel())
    me.uv_layers[0].name='UVMap';me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
def receiver_only(ob,material_index):
    preserve(ob);bm=bmesh.new();bm.from_mesh(ob.data)
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index!=material_index],context='FACES')
    bm.to_mesh(ob.data);bm.free()
    for p in ob.data.polygons:p.material_index=0
def cut_ring(ob,axis,value,keep_high=True):
    preserve(ob);bm=bmesh.new();bm.from_mesh(ob.data)
    p=[0,0,0];p[axis]=value;n=[0,0,0];n[axis]=1
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=p,plane_no=n,clear_inner=keep_high,clear_outer=not keep_high,dist=1e-8)
    bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if abs(v.co[axis]-value)<3e-7],dist=3e-7)
    es={e for e in bm.edges if e.is_boundary and all(abs(v.co[axis]-value)<3e-7 for v in e.verts)}
    bad=[v for v in {v for e in es for v in e.verts} if sum(e in es for e in v.link_edges)!=2]
    if bad:
        # The exported native rim has a measured 1.51 micrometre split.
        # Weld only these open endpoints, leaving all other source vertices intact.
        bmesh.ops.remove_doubles(bm,verts=bad,dist=3e-6)
        es={e for e in bm.edges if e.is_boundary and all(abs(v.co[axis]-value)<3e-7 for v in e.verts)}
        bad=[v for v in {v for e in es for v in e.verts} if sum(e in es for e in v.link_edges)!=2]
    if bad:raise RuntimeError('Cut endpoint data '+ob.name+' '+str([(v.co[:],sum(e in es for e in v.link_edges)) for v in bad[:16]]))
    pool={v for e in es for v in e.verts};groups=[];other=[i for i in range(3) if i!=axis]
    while pool:
        start=next(iter(pool));ordered=[start];previous=None;current=start
        while True:
            neighbors=[e.other_vert(current) for e in current.link_edges if e in es]
            if len(neighbors)!=2:raise RuntimeError('Non-cycle cut boundary '+ob.name+' '+str(len(neighbors)))
            nxt=next(v for v in neighbors if v!=previous)
            if nxt==start:break
            if nxt in ordered:raise RuntimeError('Cut edge walk intersects itself '+ob.name)
            ordered.append(nxt);previous,current=current,nxt
        pool.difference_update(ordered)
        q=np.array([v.co[:] for v in ordered])[:,other]
        area=float(np.sum(q[:,0]*np.roll(q[:,1],-1)-q[:,1]*np.roll(q[:,0],-1)))
        if area<0:ordered.reverse();area=-area
        groups.append((area,ordered))
    outer=max(groups,key=lambda g:g[0])[1]
    layer=bm.loops.layers.float_vector[ATTR]
    for _,g in groups:
        if g is outer:continue
        gg=set(g);caps=bmesh.ops.holes_fill(bm,edges=[e for e in es if all(v in gg for v in e.verts)],sides=0)['faces']
        for f in caps:
            f.normal_update()
            if (f.normal[axis]>0)==keep_high:f.normal_flip()
            for l in f.loops:
                l[layer]=f.normal
                for uv in bm.loops.layers.uv.values():l[uv].uv=(l.vert.co[other[0]]*4+.5,l.vert.co[other[1]]*4+.5)
    # Shared top-centre anchor avoids rotating a rectangular rim toward a circle's corner.
    q=np.array([v.co[:] for v in outer])[:,other];cx=float((q[:,0].min()+q[:,0].max())/2)
    crossings=[]
    for i,(a,b) in enumerate(zip(q,np.roll(q,-1,axis=0))):
        if abs(b[0]-a[0])<1e-12:continue
        t=(cx-a[0])/(b[0]-a[0])
        if 0<=t<=1:crossings.append((a[1]+t*(b[1]-a[1]),i,t))
    _,i,t=max(crossings)
    if t<1e-6:anchor=i
    elif t>1-1e-6:anchor=(i+1)%len(outer)
    else:
        a,b=outer[i],outer[(i+1)%len(outer)];edge=next(e for e in a.link_edges if e in es and e.other_vert(a)==b)
        values={f:{l.vert:l[layer].copy() for l in f.loops if l.vert in (a,b)} for f in edge.link_faces}
        _,v=bmesh.utils.edge_split(edge,a,t)
        for l in v.link_loops:
            row=values.get(l.face)
            if row and a in row and b in row:l[layer]=row[a].lerp(row[b],t)
        outer.insert(i+1,v);anchor=i+1
    outer=outer[anchor:]+outer[:anchor]
    p=np.array([v.co[:] for v in outer]);lengths=np.linalg.norm(np.roll(p,-1,axis=0)-p,axis=1)
    phase=np.r_[0,np.cumsum(lengths[:-1])]/sum(lengths)
    edge_normals=[]
    for a,b in zip(outer,outer[1:]+outer[:1]):
        edge=next(e for e in a.link_edges if e.is_boundary and e.other_vert(a)==b)
        f=edge.link_faces[0];ns={l.vert:np.array(l[layer][:]) for l in f.loops if l.vert in (a,b)}
        edge_normals.append([ns[a],ns[b]])
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    return {'phase':phase,'point':p,'edge_normals':unit(np.array(edge_normals)),'inner_rims_capped':len(groups)-1}
def sample(r,phase):
    phase=np.asarray(phase)%1;j=np.searchsorted(r['phase'],phase,side='right')%len(r['phase']);i=(j-1)%len(r['phase'])
    t=((phase-r['phase'][i])%1)/np.maximum((r['phase'][j]-r['phase'][i])%1,1e-12)
    p=r['point'][i]+t[:,None]*(r['point'][j]-r['point'][i])
    n=unit(r['edge_normals'][i,0]+t[:,None]*(r['edge_normals'][i,1]-r['edge_normals'][i,0]))
    return p,n
def restore(ob):
    me=ob.data;ns=np.empty((len(me.loops),3),np.float32);me.attributes[ATTR].data.foreach_get('vector',ns.ravel())
    me.normals_split_custom_set(unit(ns).tolist());me.attributes.remove(me.attributes[ATTR])
def zipper(a,b,pa,pb):
    faces=[];i=j=0
    while i<len(a) or j<len(b):
        na=pa[(i+1)%len(a)]+(1 if i+1>=len(a) else 0) if i<len(a) else 1e9
        nb=pb[(j+1)%len(b)]+(1 if j+1>=len(b) else 0) if j<len(b) else 1e9
        aa=a[i%len(a)];bb=b[j%len(b)]
        if abs(na-nb)<1e-10:faces.append((aa,a[(i+1)%len(a)],b[(j+1)%len(b)],bb));i+=1;j+=1
        elif na<nb:faces.append((aa,a[(i+1)%len(a)],bb));i+=1
        else:faces.append((aa,b[(j+1)%len(b)],bb));j+=1
    return faces

def transition(front,back,name,material,rows=25):
    """Sew real rims, with tangents projected onto the adjoining source surfaces."""
    length=float(front['point'][:,1].mean()-back['point'][:,1].mean())
    regular=np.arange(192)/192
    def derivative(n):
        n=unit(n);q=np.sum(n[:,[0,2]]**2,axis=1)
        # The mating surfaces are longitudinal; retain their transverse slope.
        d=n*(length*n[:,1]/np.maximum(q,.12))[:,None];d[:,1]=-length
        return d
    def shape(t,s):
        pa,na=sample(front,s);pb,nb=sample(back,s);da=derivative(na);db=derivative(nb)
        t2=t*t;t3=t2*t
        pos=(2*t3-3*t2+1)*pa+(-2*t3+3*t2)*pb+(t3-2*t2+t)*da+(t3-t2)*db
        along=(6*t2-6*t)*pa+(-6*t2+6*t)*pb+(3*t2-4*t+1)*da+(3*t2-2*t)*db
        return pos,along
    verts=[];vnorm=[];rings=[];phases=[];params=[]
    for j in range(rows):
        t=j/(rows-1);s=front['phase'] if j==0 else back['phase'] if j==rows-1 else regular
        pos,along=shape(t,s);across=shape(t,s+1e-5)[0]-shape(t,s-1e-5)[0]
        n=unit(np.cross(across,along))
        if j==0:n=sample(front,s)[1]
        if j==rows-1:n=sample(back,s)[1]
        rings.append(list(range(len(verts),len(verts)+len(pos))));phases.append(s)
        verts.extend(pos.tolist());vnorm.extend(n.tolist());params.extend((float(p),t) for p in s)
    faces=[]
    for a,b,pa,pb in zip(rings,rings[1:],phases,phases[1:]):faces.extend(zipper(a,b,pa,pb))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.materials.append(material);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);uv=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.use_smooth=True;values=[params[mesh.loops[li].vertex_index][0] for li in poly.loop_indices];wrap=max(values)-min(values)>.5
        for li in poly.loop_indices:
            s,t=params[mesh.loops[li].vertex_index];uv.data[li].uv=(s+(1 if wrap and s<.5 else 0),t)
    mesh.attributes.new(ATTR,'FLOAT_VECTOR','CORNER').data.foreach_set('vector',np.asarray([vnorm[l.vertex_index] for l in mesh.loops],np.float32).ravel())
    return ob
