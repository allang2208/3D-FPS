"""Rebuild only the connecting neck using the two actual stock/receiver cut loops."""
from pathlib import Path
from math import tau,cos,sin
import bpy,bmesh,numpy as np,json
O=Path(__file__).resolve().parent
prior=O.parent/'M24Meshy1105135808Replacement'
bpy.ops.wm.open_mainfile(filepath=str(prior/'M24_Meshy_Fitted.blend'),use_scripts=False)
CENTER=np.array([.000055,.082]);front=-.0295;back=-.0649
def unit(n):return n/np.maximum(np.linalg.norm(n,axis=-1,keepdims=True),1e-10)
def cut_boundary(ob,y,keep_front):
    mesh=ob.data
    n=np.empty((len(mesh.loops),3),np.float32);mesh.corner_normals.foreach_get('vector',n.ravel())
    at=mesh.attributes.new('JunctionNormals','FLOAT_VECTOR','CORNER');at.data.foreach_set('vector',n.ravel())
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,y,0),plane_no=(0,1,0),dist=1e-8,clear_inner=keep_front,clear_outer=not keep_front)
    bm.to_mesh(mesh);bm.free();mesh.update()
    saved=np.empty((len(mesh.loops),3),np.float32);mesh.attributes['JunctionNormals'].data.foreach_get('vector',saved.ravel())
    mesh.normals_split_custom_set(unit(saved).tolist());mesh.attributes.remove(mesh.attributes['JunctionNormals'])
    # UV splits may create duplicate mesh indices at one geometric boundary point.
    corner={}
    for p in mesh.polygons:
        ids=list(p.vertices);ls=p.loop_indices
        for a in range(len(ids)):
            b=(a+1)%len(ids);v=mesh.vertices[ids[a]].co;w=mesh.vertices[ids[b]].co
            if max(abs(v.y-y),abs(w.y-y))>1e-6:continue
            for k in (a,b):
                co=mesh.vertices[ids[k]].co;pos=np.array([co.x,co.z])
                key=tuple(np.round(pos,8))
                if key not in corner:corner[key]=[pos,[]]
                corner[key][1].append(saved[ls[k]])
    if len(corner)<12:raise ValueError('Missing cut on '+ob.name)
    pos=np.array([v[0] for v in corner.values()]);nor=unit(np.array([np.mean(v[1],axis=0) for v in corner.values()]))
    d=pos-CENTER;theta=np.arctan2(d[:,1],d[:,0])%tau;order=np.argsort(theta)
    return theta[order],pos[order],nor[order]
def sample(ring,theta):
    a,p,n=ring
    j=np.searchsorted(a,theta%tau,side='right')%len(a);i=(j-1)%len(a)
    direction=np.stack((np.cos(theta),np.sin(theta)),axis=-1)
    dp=p[j]-p[i];origin=p[i]-CENTER
    def cross(x,y):return x[:,0]*y[:,1]-x[:,1]*y[:,0]
    denom=cross(direction,dp);weight=np.clip(cross(origin,direction)/np.where(np.abs(denom)>1e-14,denom,1.),0,1)
    return p[i]+dp*weight[:,None],unit(n[i]+(n[j]-n[i])*weight[:,None])
def loft(start,end,mat,collection):
    angles=np.arange(128)*tau/128
    q=np.stack((np.cos(angles),np.sin(angles)),axis=-1)
    pa,na=sample(start,angles);pb,nb=sample(end,angles)
    ra=np.linalg.norm(pa-CENTER,axis=1);rb=np.linalg.norm(pb-CENTER,axis=1)
    def slope(N):return np.clip(-N[:,1]/np.maximum(.25,np.sum(N[:,[0,2]]*q,axis=1)),-.95,.95)
    sa,sb=slope(na),slope(nb);length=back-front
    verts=[];rings=[];phases=[];locks={}
    def row(angles,xz,y,ns=None):
        rings.append(np.arange(len(angles))+len(verts));phases.append(angles)
        if ns is not None:
            for id,n in zip(rings[-1],ns):locks[id]=n
        verts.extend((p[0],y,p[1]) for p in xz)
    row(start[0],start[1],front,start[2])
    for k in range(1,18):
        t=k/18;tt=t*t;ttt=tt*t
        r=(2*ttt-3*tt+1)*ra+(ttt-2*tt+t)*length*sa+(-2*ttt+3*tt)*rb+(ttt-tt)*length*sb
        row(angles,CENTER+r[:,None]*q,front+length*t)
    row(end[0],end[1],back,end[2])
    faces=[]
    # Zipper dissimilar loop counts without introducing the other rim's near-duplicate angles.
    for a,b,ta,tb in zip(rings,rings[1:],phases,phases[1:]):
        ia=ib=0
        while ia<len(a) or ib<len(b):
            a0=a[ia%len(a)];b0=b[ib%len(b)]
            aa=(ta[(ia+1)%len(a)]+(tau if ia+1>=len(a) else 0)) if ia<len(a) else 1e9
            bb=(tb[(ib+1)%len(b)]+(tau if ib+1>=len(b) else 0)) if ib<len(b) else 1e9
            if aa<=bb:
                faces.append((a0,a[(ia+1)%len(a)],b0));ia+=1
            else:
                faces.append((a0,b[(ib+1)%len(b)],b0));ib+=1
    me=bpy.data.meshes.new('M24 | continuous neck');me.from_pydata(verts,[],faces);me.update()
    sleeve=bpy.data.objects.new('M24 | blended receiver shoulder',me);collection.objects.link(sleeve)
    me.materials.append(mat);uv=me.uv_layers.new(name='UVMap')
    for p in me.polygons:
        p.use_smooth=True
        ps=np.array([verts[j] for j in p.vertices]);d=ps[:,[0,2]]-CENTER
        angle=np.arctan2(d[:,1],d[:,0]);angle=np.unwrap(angle)
        for li,theta,v in zip(p.loop_indices,angle,ps):
            uv.data[li].uv=(theta/tau*3,(v[1]-front)*24.)
    me.update()
    ns=np.array([locks.get(loop.vertex_index,me.vertices[loop.vertex_index].normal[:]) for loop in me.loops])
    me.normals_split_custom_set(unit(ns).tolist());return sleeve
r={}
for kind in ('Native','Advanced'):
    col=bpy.data.collections[kind+' | fitted to M24']
    rec=next(o for o in col.objects if o.name.startswith('Donor receiver'))
    body=next(o for o in col.objects if 'Meshy carbon stock' in o.name)
    old=next(o for o in col.objects if o.name.endswith('neck seam'))
    bpy.data.objects.remove(old,do_unlink=True)
    ra=cut_boundary(rec,front,True);rb=cut_boundary(body,back,False)
    neck=loft(ra,rb,rec.data.materials[0],col)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in (rec,body,neck):ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=rec
    name='SM_M24_CarbonSpine_'+kind
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',use_tspace=True,add_leaf_bones=False,bake_anim=False,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    r[kind]={'receiver_loop':len(ra[0]),'shell_loop':len(rb[0]),'transition_mm':(front-back)*1000,'transverse_steps':128,'longitudinal_steps':18,'material':'CS_Receiver'}
for ob in bpy.data.collections['Advanced | fitted to M24'].objects:ob.hide_set(True);ob.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_Meshy_JunctionR2.blend'),compress=True)
(O/'carbon-construction.json').write_text(json.dumps(r,indent=2))
print(r)
