"""Rebuild the local carbon shoulder with regular surface strips and one shared UV0."""
from pathlib import Path
from math import tau
import bpy,bmesh,numpy as np,json
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24StockJunctionR2_20261105/M24_Meshy_JunctionR2.blend'),use_scripts=False)
SEAT=-.020;SOURCE_FRONT=-.085;BACK=-.110;SHIFT=.0555;END=BACK+SHIFT
ATTR='ShoulderNormal';STEPS=40;RES=192

def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def preserve(ob):
    me=ob.data;n=np.empty((len(me.loops),3),np.float32);me.corner_normals.foreach_get('vector',n.ravel())
    if ATTR in me.attributes:me.attributes.remove(me.attributes[ATTR])
    layer=me.attributes.new(ATTR,'FLOAT_VECTOR','CORNER');layer.data.foreach_set('vector',n.ravel())
    # Blender joins UV layers by name. All primary coordinates must become UV0.
    me.uv_layers[0].name='UVMap';me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
    bm=bmesh.new();bm.from_mesh(me);return bm
def cut(ob,y,front):
    bm=preserve(ob)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,y,0),plane_no=(0,1,0),dist=1e-8,clear_inner=front,clear_outer=not front)
    bmesh.ops.remove_doubles(bm,verts=[v for v in bm.verts if abs(v.co.y-y)<2e-7],dist=3e-6)
    edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-y)<2e-7 for v in e.verts)]
    pool=set(v for e in edges for v in e.verts);groups=[];es=set(edges)
    while pool:
        todo=[next(iter(pool))];group=[]
        while todo:
            v=todo.pop()
            if v not in pool:continue
            pool.remove(v);group.append(v);todo.extend(e.other_vert(v) for e in v.link_edges if e in es)
        groups.append(group)
    outer=max(groups,key=lambda g:np.prod(np.ptp(np.array([v.co[:] for v in g])[:,[0,2]],axis=0)))
    # The source has an inner cavity. Close its own rim behind the outer join.
    for group in groups:
        if group is outer:continue
        first=group[0];ordered=[first];prev=None;cur=first
        while True:
            nxt=next(e.other_vert(cur) for e in cur.link_edges if e in es and e.other_vert(cur)!=prev)
            if nxt==first:break
            ordered.append(nxt);prev,cur=cur,nxt
        for v in ordered:v.co.y-=.0015
        face=bm.faces.new(ordered);face.material_index=0;face.normal_update()
        if face.normal.y>0:face.normal_flip()
        for l in face.loops:
            l[bm.loops.layers.float_vector[ATTR]]=(0,-1,0)
            for uv in bm.loops.layers.uv.values():l[uv].uv=(l.vert.co.x*20+.5,l.vert.co.z*20)
    # Follow the real edge graph. Polar sorting folds the concave cheek contour.
    first=outer[0];ordered=[first];prev=None;cur=first
    while True:
        nxt=next(e.other_vert(cur) for e in cur.link_edges if e in es and e.other_vert(cur)!=prev)
        if nxt==first:break
        ordered.append(nxt);prev,cur=cur,nxt
    pos=np.array([v.co[:] for v in ordered]);xz=pos[:,[0,2]]
    signed=np.sum(xz[:,0]*np.roll(xz[:,1],-1)-xz[:,1]*np.roll(xz[:,0],-1))
    if signed<0:ordered.reverse();pos=np.array([v.co[:] for v in ordered]);xz=pos[:,[0,2]]
    center=(xz.min(0)+xz.max(0))*.5
    lengths=np.linalg.norm(np.roll(xz,-1,axis=0)-xz,axis=1);distance=np.r_[0,np.cumsum(lengths[:-1])];perimeter=lengths.sum()
    crossings=[]
    for i,(p,q) in enumerate(zip(xz,np.roll(xz,-1,axis=0))):
        if abs(q[1]-p[1])<1e-12:continue
        w=(center[1]-p[1])/(q[1]-p[1])
        if 0<=w<=1:crossings.append((p[0]+w*(q[0]-p[0]),distance[i]+w*lengths[i]))
    anchor=max(crossings)[1]
    normals=[]
    for v in ordered:normals.append(np.mean([l[bm.loops.layers.float_vector[ATTR]][:] for l in v.link_loops],axis=0))
    a=((distance-anchor)%perimeter)/perimeter*tau;order=np.argsort(a)
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    return {'angle':a[order],'point':pos[order][:,[0,2]],'normal':unit(np.array(normals)[order]),'center':center}
def sample(r,a):
    a=np.asarray(a)%tau;idx=np.searchsorted(r['angle'],a,side='right')%len(r['angle']);prev=(idx-1)%len(r['angle'])
    span=(r['angle'][idx]-r['angle'][prev])%tau
    w=((a-r['angle'][prev])%tau)/np.maximum(span,1e-12)
    return r['point'][prev]+w[...,None]*(r['point'][idx]-r['point'][prev])
def normal(r,a):return unit(np.column_stack([np.interp(a%tau,r['angle'],r['normal'][:,k],period=tau) for k in range(3)]))

def author(kind):
    col=bpy.data.collections[kind+' | fitted to M24']
    rec=next(o for o in col.objects if o.name.startswith('Donor receiver'))
    body=next(o for o in col.objects if 'Meshy carbon stock' in o.name)
    for ob in list(col.objects):
        if ob not in (rec,body):bpy.data.objects.remove(ob,do_unlink=True)
    donor=body.copy();donor.data=body.data.copy();donor.name=kind+' UV source';col.objects.link(donor);donor.hide_set(False)
    donor.data.uv_layers[0].name='UVMap'
    # Additional section rings are taken from untouched source surfaces.
    def section(ob,y,front=False):
        tmp=ob.copy();tmp.data=ob.data.copy();col.objects.link(tmp)
        result=cut(tmp,y,front);mesh=tmp.data;bpy.data.objects.remove(tmp,do_unlink=True);bpy.data.meshes.remove(mesh);return result
    recnext=section(rec,SEAT+.002,True)
    backnext=section(donor,BACK-.003,False)
    uvfront=section(donor,SOURCE_FRONT,False)
    rt=cut(rec,SEAT,True);bt=cut(body,BACK,False)
    grid=np.arange(RES)*tau/RES
    start=sample(rt,grid);end=sample(bt,grid);length=SEAT-END
    delta=end-start;d0=(start-sample(recnext,grid))/.002*length;d1=(sample(backnext,grid)-end)/.003*length
    # Monotone component tangents remove bulges and keep the cheek line flat.
    for d in (d0,d1):d[:]=np.sign(delta)*np.minimum(np.where(d*delta>0,abs(d),0),3*abs(delta))
    aa=np.divide(d0,delta,out=np.zeros_like(delta),where=abs(delta)>1e-10);bb=np.divide(d1,delta,out=np.zeros_like(delta),where=abs(delta)>1e-10)
    fac=np.maximum(1,np.sqrt(aa*aa+bb*bb)/3);d0/=fac;d1/=fac
    def interp(v,a):return np.column_stack([np.interp(a%tau,grid,v[:,i],period=tau) for i in range(2)])
    def surface(a,t):
        t=np.asarray(t);t=np.broadcast_to(t,np.shape(a))[:,None];t2=t*t;t3=t2*t
        xz=(2*t3-3*t2+1)*interp(start,a)+(t3-2*t2+t)*interp(d0,a)+(-2*t3+3*t2)*interp(end,a)+(t3-t2)*interp(d1,a)
        return np.column_stack((xz[:,0],SEAT-length*t[:,0],xz[:,1]))
    def surf_normal(a,t):
        eps=1e-5
        n=unit(np.cross(surface(a+eps,t)-surface(a-eps,t),surface(a,t+eps)-surface(a,t-eps)))
        if t<.15:n=unit(n*(t/.15)+normal(rt,a)*(1-t/.15))
        if t>.85:n=unit(n*((1-t)/.15)+normal(bt,a)*(1-(1-t)/.15))
        return n
    points=[];mapped=[];ns=[];rings=[];phases=[]
    def row(a,t):
        rings.append(np.arange(len(a))+len(points));phases.append(a)
        pos=surface(a,t)
        if t==0:pos[:,[0,2]]=rt['point']
        if t==1:pos[:,[0,2]]=bt['point']
        points.extend(pos);ns.extend(normal(rt,a) if t==0 else normal(bt,a) if t==1 else surf_normal(a,t))
        # Transfer existing atlas UVs on the original surface before reshaping.
        y=SOURCE_FRONT+(BACK-SOURCE_FRONT)*t
        source=uvfront if t==0 else bt if t==1 else section(donor,y,False)
        xz=sample(source,a)
        mapped.extend(np.column_stack((xz[:,0],np.full(len(a),y),xz[:,1])))
    row(rt['angle'],0.)
    for i in range(1,STEPS):row(grid,i/STEPS)
    row(bt['angle'],1.)
    faces=[]
    for ra,rb,pa,pb in zip(rings,rings[1:],phases,phases[1:]):
        ia=ib=0
        while ia<len(ra) or ib<len(rb):
            a0=ra[ia%len(ra)];b0=rb[ib%len(rb)]
            va=pa[(ia+1)%len(ra)]+(tau if ia+1>=len(ra) else 0) if ia<len(ra) else 1e10
            vb=pb[(ib+1)%len(rb)]+(tau if ib+1>=len(rb) else 0) if ib<len(rb) else 1e10
            if abs(va-vb)<1e-9:
                faces.append((a0,ra[(ia+1)%len(ra)],rb[(ib+1)%len(rb)],b0));ia+=1;ib+=1
            elif va<vb:faces.append((a0,ra[(ia+1)%len(ra)],b0));ia+=1
            else:faces.append((a0,rb[(ib+1)%len(rb)],b0));ib+=1
    me=bpy.data.meshes.new(kind+' smooth carbon shoulder');me.from_pydata(mapped,[],faces);me.materials.append(body.data.materials[0]);me.uv_layers.new(name='UVMap');me.update()
    shoulder=bpy.data.objects.new(kind+' smooth carbon shoulder',me);col.objects.link(shoulder)
    for o in bpy.context.view_layer.objects:o.select_set(False)
    shoulder.select_set(True);bpy.context.view_layer.objects.active=shoulder
    mod=shoulder.modifiers.new('Source carbon atlas','DATA_TRANSFER');mod.object=donor;mod.use_loop_data=True;mod.data_types_loops={'UV'};mod.loop_mapping='POLYINTERP_NEAREST';mod.layers_uv_select_src='UVMap';mod.layers_uv_select_dst='NAME'
    bpy.ops.object.modifier_apply(modifier=mod.name)
    me=shoulder.data;me.vertices.foreach_set('co',np.asarray(points,dtype=np.float32).ravel())
    for p in me.polygons:p.use_smooth=True
    me.update();indices=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',indices)
    layer=me.attributes.new(ATTR,'FLOAT_VECTOR','CORNER');layer.data.foreach_set('vector',np.asarray(ns,dtype=np.float32)[indices].ravel())
    # Match the boundary's UV island on each side of the atlas seam.
    bm=bmesh.new();bm.from_mesh(body.data)
    body_uv=bm.loops.layers.uv['UVMap'];boundary_edges=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-BACK)<2e-7 for v in e.verts)]
    anchors=[]
    for edge in boundary_edges:
        if len(edge.link_faces)!=1:continue
        face=edge.link_faces[0];uv={l.vert:l[body_uv].uv.copy() for l in face.loops}
        a,b=edge.verts;anchors.append((np.array(a.co)[[0,2]],np.array(b.co)[[0,2]],np.array(uv[a]),np.array(uv[b])))
    points_arr=np.asarray(points);uv=me.uv_layers[0].data
    for p in me.polygons:
        boundary_loops=[li for li in p.loop_indices if abs(points_arr[me.loops[li].vertex_index,1]-END)<2e-7]
        if len(boundary_loops)!=2:continue
        pos=np.array([points_arr[me.loops[li].vertex_index,[0,2]] for li in boundary_loops]);mid=pos.mean(0)
        a,b,ua,ub=min(anchors,key=lambda v:np.linalg.norm((v[0]+v[1])*.5-mid))
        for li,pt in zip(boundary_loops,pos):
            w=np.clip(np.dot(pt-a,b-a)/max(np.dot(b-a,b-a),1e-20),0,1);uv[li].uv=ua+w*(ub-ua)
    bm.free()
    for v in body.data.vertices:v.co.y+=SHIFT
    body.data.update()
    bpy.data.objects.remove(donor,do_unlink=True)
    for o in bpy.context.view_layer.objects:o.select_set(False)
    for o in (rec,body,shoulder):o.hide_set(False);o.hide_render=False;o.select_set(True)
    bpy.context.view_layer.objects.active=rec;bpy.ops.object.join()
    rec.name='SM_M24_CarbonSpine_'+kind
    bm=bmesh.new();bm.from_mesh(rec.data)
    for y in (SEAT,END):
        vv=[v for v in bm.verts if abs(v.co.y-y)<2e-7];bmesh.ops.remove_doubles(bm,verts=vv,dist=2e-7)
        bad=[e for e in bm.edges if all(abs(v.co.y-y)<2e-7 for v in e.verts) and len(e.link_faces)!=2]
        if bad:raise RuntimeError('Unsewn shoulder rim '+kind+' '+str((y,len(bad))))
    bm.to_mesh(rec.data);bm.free();me=rec.data;me.update()
    ns=np.empty((len(me.loops),3),np.float32);me.attributes[ATTR].data.foreach_get('vector',ns.ravel());me.normals_split_custom_set(unit(ns).tolist());me.attributes.remove(me.attributes[ATTR])
    me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
    if me.uv_layers[0].name!='UVMap':raise RuntimeError('UV0 is not the shared atlas channel')
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(rec.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',use_tspace=True,add_leaf_bones=False,bake_anim=False,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    return {'seam_y_mm':SEAT*1000,'shell_join_y_mm':END*1000,'local_retopology_mm':length*1000,'stock_shift_mm':SHIFT*1000,'rings':STEPS+1,'cross_section_samples':RES,'UV0':'UVMap','material':'CS_Meshy','source_body_unwarped':True}

records={k:author(k) for k in ('Native','Advanced')}
for o in bpy.data.collections['Advanced | fitted to M24'].objects:o.hide_set(True);o.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Carbon_SmoothUV.blend'),compress=True)
(O/'construction.json').write_text(json.dumps(records,indent=2))
print('M24_SMOOTH_UV_AUTHORED',records)
