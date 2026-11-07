"""Fit the supplied textured stock into the two existing M24 receiver assemblies."""
from pathlib import Path
import json, math
import bpy,bmesh
import numpy as np
root=Path(__file__).resolve().parent
baseline=root.parent/'M24CarbonSpineGame20261104'
contract=json.loads((baseline/'geometry.json').read_text())['models']
bpy.ops.wm.read_factory_settings(use_empty=True)
with bpy.data.libraries.load(str(baseline/'M24_CarbonSpine_Fitted.blend')) as (avail,loaded):
    loaded.objects=[name for name in avail.objects if name.startswith('Donor receiver | ')]
receivers={o.name.split(' | ')[-1]:o for o in loaded.objects}
bpy.ops.import_scene.gltf(filepath=str(next((root/'Input').glob('*.glb'))))
template=next(o for o in bpy.context.scene.objects if o.type=='MESH')
template.data.materials[0].name='CS_Meshy'
mesh=template.data
# Preserve imported corner normals across the single neck cut, including split UV edges.
normals=np.empty((len(mesh.loops),3),np.float32)
mesh.corner_normals.foreach_get('vector',normals.ravel())
orig=mesh.attributes.new('FitSourceNormal','FLOAT_VECTOR','CORNER')
orig.data.foreach_set('vector',normals.ravel())
cut=-.941
bm=bmesh.new();bm.from_mesh(mesh)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                       plane_co=(cut,0,0),plane_no=(1,0,0),dist=1e-7,clear_inner=True)
bm.to_mesh(mesh);bm.free();mesh.update()
src=np.empty((len(mesh.vertices),3),np.float32)
mesh.vertices.foreach_get('co',src.ravel());src=src.astype(float)
bound=np.abs(src[:,0]-cut)<1e-6
source_rim=src[bound][:,1:]
source_mid=(source_rim.min(0)+source_rim.max(0))*.5
source_rim-=source_mid
def radial_table(rim):
    angles=np.mod(np.arctan2(rim[:,1],rim[:,0]),2*np.pi)
    order=np.argsort(angles)
    angles,idx=np.unique(angles[order].round(8),return_index=True)
    return angles,rim[order][idx]
def point_on_rim(rimtable,angles):
    samples,pts=rimtable
    j=np.searchsorted(samples,np.mod(angles,2*np.pi),side='right')%len(samples)
    p=pts[(j-1)%len(pts)];q=pts[j];edge=q-p
    vx,vy=np.cos(angles),np.sin(angles)
    cross=vx*edge[:,1]-vy*edge[:,0]
    d=np.divide(p[:,0]*edge[:,1]-p[:,1]*edge[:,0],cross,out=np.linalg.norm(p,axis=1),where=np.abs(cross)>1e-11)
    return np.column_stack((d*vx,d*vy))
source_table=radial_table(source_rim)
smeta={}
for kind,record in contract.items():
    receiver=receivers[kind]
    col=bpy.data.collections.new(kind+' | fitted to M24');bpy.context.scene.collection.children.link(col)
    col.objects.link(receiver);receiver.data.materials[0].name='CS_Receiver'
    ring=np.asarray(record['ring']);seat=record['seam_y_m'];rear=record['shoulder_y_m']
    bounds=ring[:,[0,2]];center=(bounds.min(0)+bounds.max(0))*.5
    dest_table=radial_table(bounds-center)
    scale=(seat-rear)/(.95139402+.95188099)
    def transform(v):
        xx=v[:,0];q=v[:,1:]-source_mid
        theta=np.arctan2(q[:,1],q[:,0])
        srcp=point_on_rim(source_table,theta);dstp=point_on_rim(dest_table,theta)
        t=np.clip((-.840-xx)/(-.840-cut),0,1);t=t*t*(3.-2.*t)
        transverse=center+q*scale
        radius=np.linalg.norm(q,axis=1)/np.maximum(1e-8,np.linalg.norm(srcp,axis=1))
        transverse+=t[:,None]*(dstp-srcp*scale)*radius[:,None]
        return np.column_stack((transverse[:,0],seat-(xx+.95188099)*scale,transverse[:,1]))
    ob=template.copy();ob.data=mesh.copy();ob.name=kind+' | Meshy carbon stock';col.objects.link(ob)
    me=ob.data; points=transform(src);me.vertices.foreach_set('co',points.astype(np.float32).ravel());me.update()
    # Inverse transpose of the local deformation carries the supplied tangent frame around the neck.
    ids=np.empty(len(me.loops),np.int32);me.loops.foreach_get('vertex_index',ids)
    ns=np.empty((len(ids),3),np.float32);me.attributes['FitSourceNormal'].data.foreach_get('vector',ns.ravel())
    rotated=ns[:,[1,0,2]].copy();rotated[:,1]*=-1
    local=src[:,0]<-.8399; inds=np.flatnonzero(local)
    delta=.000015
    jac=np.stack([(transform(src[inds]+d)-transform(src[inds]-d))/(2*delta) for d in np.eye(3)*delta],axis=2)
    rows=np.flatnonzero(local[ids])
    mapped=np.einsum('nji,nj->ni',np.linalg.pinv(jac)[np.searchsorted(inds,ids[rows])],ns[rows])
    rotated[rows]=mapped/np.maximum(np.linalg.norm(mapped,axis=1)[:,None],1e-12)
    me.normals_split_custom_set(rotated.tolist()); me.attributes.remove(me.attributes['FitSourceNormal'])
    # Stitch across the last 1.8 mm; the two actual perimeters have different vertex counts.
    # UVs follow individual source cut edges, preserving UV islands on the metal end.
    edge_uv=[];uv=me.uv_layers.active.data
    for face in me.polygons:
        vs=list(face.vertices)
        if sum(bool(bound[i]) for i in vs)<2:continue
        ls=list(face.loop_indices)
        for a,b in zip(range(len(vs)),list(range(1,len(vs)))+[0]):
            i,j=vs[a],vs[b]
            if not(bound[i] and bound[j]):continue
            p,q=points[[i,j]][:,[0,2]]-center
            aa,bb=np.mod(np.arctan2([p[1],q[1]],[p[0],q[0]]),2*np.pi)
            if abs((bb-aa+np.pi)%(2*np.pi)-np.pi)<1e-7:continue
            edge_uv.append((aa,bb,np.array(uv[ls[a]].uv),np.array(uv[ls[b]].uv)))
    tip=radial_table(points[bound][:,[0,2]]-center)
    ang=np.unique(np.r_[tip[0],dest_table[0]].round(7))
    ring0=point_on_rim(dest_table,ang)+center;ring1=point_on_rim(tip,ang)+center
    collar_y=points[bound,1].mean()
    verts=[(x,y,z) for r,y in ((ring0,seat),(ring1,collar_y)) for x,z in r]
    count=len(ang);faces=[];uv_faces=[]
    for i in range(count):
        j=(i+1)%count;a=ang[i];b=ang[j] if j else ang[j]+2*np.pi;mid=(a+b)*.5
        def ratio(x,y,p):return ((p-x+np.pi)%(2*np.pi)-np.pi)/((y-x+np.pi)%(2*np.pi)-np.pi)
        closest=min(edge_uv,key=lambda e:abs(ratio(e[0],e[1],mid)-.5))
        aa,bb,ua,ub=closest
        left=ua+(ub-ua)*np.clip(ratio(aa,bb,a),0,1);right=ua+(ub-ua)*np.clip(ratio(aa,bb,b),0,1)
        tangent=right-left;perp=np.array([-tangent[1],tangent[0]])/max(np.linalg.norm(tangent),1e-9)*.00016
        faces.append((i,j,j+count,i+count));uv_faces.append((left+perp,right+perp,right,left))
    band=bpy.data.meshes.new(kind+' seat bridge');band.from_pydata(verts,[],faces);band.update()
    bridge=bpy.data.objects.new(kind+' | neck seam',band);col.objects.link(bridge)
    band.materials.append(me.materials[0]);layer=band.uv_layers.new(name='UVMap')
    for face,coords in zip(band.polygons,uv_faces):
        face.use_smooth=True
        for ix,co in zip(face.loop_indices,coords):layer.data[ix].uv=co
    # Order around the XZ plane gives a +radial side when pointing down the longitudinal axis.
    for o in (ob,bridge,receiver):
        o.hide_render=False;o.hide_set(False)
    bpy.ops.object.select_all(action='DESELECT')
    for o in (ob,bridge,receiver):o.select_set(True)
    bpy.context.view_layer.objects.active=receiver
    filename='SM_M24_CarbonSpine_'+kind+'.fbx'
    bpy.ops.export_scene.fbx(filepath=str(root/'Exports'/filename),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,use_tspace=True,
        use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    smeta[kind]={'file':filename,'seat_y':seat,'shoulder_y':rear,'receiver_mat':record['material'],'receiver_points':len(ring)}
bpy.data.objects.remove(template,do_unlink=True)
for o in bpy.data.collections['Advanced | fitted to M24'].objects:o.hide_set(True);o.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(root/'M24_Meshy_Fitted.blend'),compress=True)
(root/'fit.json').write_text(json.dumps(smeta,indent=2))
