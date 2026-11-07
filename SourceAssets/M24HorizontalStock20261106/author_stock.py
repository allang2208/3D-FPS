"""Horizontal revision of the accepted joint; trim the receiver 18 mm farther forward."""
from pathlib import Path
import bpy,bmesh,numpy as np,json,math
from mathutils import Matrix
O=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
ATTR='PreservedCornerNormal';CUT=-.941;FRONT=0.;SCALE=.3185991175/1.90327501
ANGLE=0.;C,S=math.cos(ANGLE),math.sin(ANGLE)
ROT=np.array([[0,1,0],[-C,0,-S],[-S,0,C]])
SOURCE_CENTER=np.array([CUT,.00039667,.17187572]);SEAT=np.array([.000055,-.025,.0917])
def unit(v):return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)
def preserve(ob):
    me=ob.data;n=np.empty((len(me.loops),3),np.float32);me.corner_normals.foreach_get('vector',n.ravel())
    a=me.attributes.new(ATTR,'FLOAT_VECTOR','CORNER');a.data.foreach_set('vector',n.ravel())
    me.uv_layers[0].name='UVMap';me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
def cut(ob,axis,value,keep_high):
    preserve(ob);bm=bmesh.new();bm.from_mesh(ob.data)
    p=[0,0,0];p[axis]=value;n=[0,0,0];n[axis]=1
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=p,plane_no=n,dist=1e-8,clear_inner=keep_high,clear_outer=not keep_high)
    boundary=[v for v in bm.verts if abs(v.co[axis]-value)<2e-7]
    bmesh.ops.remove_doubles(bm,verts=boundary,dist=2e-7)
    edges={e for e in bm.edges if e.is_boundary and all(abs(v.co[axis]-value)<2e-7 for v in e.verts)}
    pool={v for e in edges for v in e.verts};groups=[]
    while pool:
        todo=[next(iter(pool))];group=[]
        while todo:
            v=todo.pop()
            if v not in pool:continue
            pool.remove(v);group.append(v);todo.extend(e.other_vert(v) for e in v.link_edges if e in edges)
        groups.append(group)
    other=[j for j in range(3) if j!=axis]
    outer=max(groups,key=lambda g:np.prod(np.ptp(np.array([v.co[:] for v in g])[:,other],axis=0)))
    for g in groups:
        if g is outer:continue
        es=[e for e in edges if e.verts[0] in g and e.verts[1] in g]
        caps=bmesh.ops.holes_fill(bm,edges=es,sides=0)['faces']
        for face in caps:
            face.normal_update()
            for loop in face.loops:
                loop[bm.loops.layers.float_vector[ATTR]]=face.normal
                for uv in bm.loops.layers.uv.values():loop[uv].uv=(loop.vert.co[other[0]]*3+.5,loop.vert.co[other[1]]*3+.5)
    pos=np.array([v.co[:] for v in outer]);ns=unit(np.array([np.mean([l[bm.loops.layers.float_vector[ATTR]][:] for l in v.link_loops],axis=0) for v in outer]))
    q=pos[:,other];center=(q.min(0)+q.max(0))*.5;angle=np.arctan2(q[:,1]-center[1],q[:,0]-center[0])%(2*np.pi);order=np.argsort(angle)
    bm.to_mesh(ob.data);bm.free();ob.data.update()
    return angle[order],pos[order],ns[order],center
def sample(r,a):
    ang,p,n,_=r;j=np.searchsorted(ang,a,side='right')%len(ang);i=(j-1)%len(ang)
    w=((a-ang[i])%(2*np.pi))/np.maximum((ang[j]-ang[i])%(2*np.pi),1e-12)
    return p[i]+w[:,None]*(p[j]-p[i]),unit(n[i]+w[:,None]*(n[j]-n[i]))
def export(objects,name):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    ob=objects[0];ob.name=name;me=ob.data
    n=np.empty((len(me.loops),3),np.float32);me.attributes[ATTR].data.foreach_get('vector',n.ravel());me.normals_split_custom_set(unit(n).tolist());me.attributes.remove(me.attributes[ATTR])
    me.uv_layers.active_index=0;me.uv_layers[0].active_render=True
    bpy.ops.export_scene.fbx(filepath=str(O/'Exports'/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',use_tspace=True,add_leaf_bones=False,bake_anim=False,use_triangles=True,mesh_smooth_type='FACE',path_mode='STRIP')
    return ob
with bpy.data.libraries.load(str(O.parent/'M24CarbonSpineGame20261104/M24_CarbonSpine_Fitted.blend')) as (av,ld):
    ld.objects=[n for n in av.objects if n.startswith('Donor receiver | ')]
receivers={o.name.split(' | ')[-1]:o for o in ld.objects}
bpy.ops.import_scene.gltf(filepath=str(O.parent/'M24Meshy1105135808Replacement/Input/Meshy_AI_Carbon_Stock_1105135808_texture.glb'))
template=next(o for o in bpy.context.scene.objects if o.type=='MESH');template.data.materials[0].name='CS_Meshy'
source_ring=cut(template,0,CUT,True)
metal_faces=[p.index for p in template.data.polygons if sum(template.data.vertices[v].co.x for v in p.vertices)/len(p.vertices)<-.8448]
me=template.data;p=np.empty((len(me.vertices),3),np.float32);me.vertices.foreach_get('co',p.ravel());p=(p-SOURCE_CENTER)@ROT.T*SCALE+SEAT;me.vertices.foreach_set('co',p.astype(np.float32).ravel())
n=np.empty((len(me.loops),3),np.float32);me.attributes[ATTR].data.foreach_get('vector',n.ravel());me.attributes[ATTR].data.foreach_set('vector',(n@ROT.T).astype(np.float32).ravel());me.update()
# Rotate raw circular perimeter into the receiver XZ angular convention.
a,sp,sn,sc=source_ring;target=((sp-SOURCE_CENTER)@ROT.T*SCALE+SEAT);target_n=sn@ROT.T
br=(a,target,target_n,SEAT[[0,2]])
records={}
for kind in ('Native','Advanced'):
    col=bpy.data.collections.new(kind);bpy.context.scene.collection.children.link(col)
    rec=receivers[kind];col.objects.link(rec);rec.data.materials[0].name='CS_Receiver'
    rr=cut(rec,1,FRONT,True)
    body=template.copy();body.data=template.data.copy();col.objects.link(body)
    body.data.materials.append(rec.data.materials[0])
    for pi in metal_faces:body.data.polygons[pi].material_index=1
    # The new surface ends at the unmodified circular nose, never at the cheek shell.
    angles=np.unique(np.round(np.r_[rr[0],br[0],np.arange(160)*2*np.pi/160],5));pa,na=sample(rr,angles);pb,nb=sample(br,angles)
    length=FRONT-SEAT[1];delta=pb-pa
    d0=np.column_stack((np.zeros(len(angles)),np.full(len(angles),-length),np.zeros(len(angles))))
    d1=np.tile(np.array([0,-C,-S])*length,(len(angles),1))
    verts=[];normals=[];faces=[];rings=25;count=len(angles)
    for j in range(rings):
        t=j/(rings-1);t2=t*t;t3=t2*t
        pp=(2*t3-3*t2+1)*pa+(t3-2*t2+t)*d0+(-2*t3+3*t2)*pb+(t3-t2)*d1
        tangent=(6*t2-6*t)*pa+(3*t2-4*t+1)*d0+(-6*t2+6*t)*pb+(3*t2-2*t)*d1
        across=(np.roll(pp,-1,axis=0)-np.roll(pp,1,axis=0));ns=unit(np.cross(tangent,across))
        radial=pp[:,[0,2]]-np.mean(pp[:,[0,2]],axis=0)
        if np.mean(np.sum(ns[:,[0,2]]*radial,axis=1))<0:ns=-ns
        if j==0:ns=na
        if j==rings-1:ns=nb
        verts.extend(pp.tolist());normals.extend(ns.tolist())
    for j in range(rings-1):
        for i in range(count):
            a0=j*count+i;a1=j*count+(i+1)%count;faces.append((a0,a1,a1+count,a0+count))
    mesh=bpy.data.meshes.new(kind+' receiving tail');mesh.from_pydata(verts,[],faces);mesh.materials.append(rec.data.materials[0]);mesh.update()
    neck=bpy.data.objects.new(kind+' receiving tail',mesh);col.objects.link(neck);uv=mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        poly.use_smooth=True
        phases=[angles[mesh.loops[li].vertex_index%count]/(2*np.pi) for li in poly.loop_indices]
        wrapped=max(phases)-min(phases)>.5
        for li in poly.loop_indices:
            vi=mesh.loops[li].vertex_index;phase=angles[vi%count]/(2*np.pi)
            uv.data[li].uv=(phase+(1 if wrapped and phase<.5 else 0),vi//count/(rings-1))
    # Coherent outward winding independent of ring construction orientation.
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    an=mesh.attributes.new(ATTR,'FLOAT_VECTOR','CORNER');ns=np.array([normals[l.vertex_index] for l in mesh.loops],np.float32);an.data.foreach_set('vector',ns.ravel())
    ob=export([rec,body,neck],'SM_M24_CarbonSpine_'+kind)
    records[kind]={'accepted_basis':'M24NaturalStockRail20261106; user accepted the joint on 2026-11-06','original_source':'Meshy_AI_Carbon_Stock_1105135808_texture.glb','uniform_scale':SCALE,'rigid_pitch_down_deg':0,'stock_axis_source':[0,-1,0],'nose_center_m':SEAT.tolist(),'receiver_cut_y_m':FRONT,'additional_receiver_trim_mm':18,'stock_translation_forward_mm':18,'source_tip_trim_mm':(.95188099+CUT)*SCALE*1000,'receiver_tail_rebuilt_mm':length*1000,'stock_body_deformation':False,'source_UV_and_normal_preserved':True,'metal_nose_finish':'same material as receiver'}
    if kind=='Advanced':ob.hide_render=True;ob.hide_set(True)
bpy.data.objects.remove(template,do_unlink=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_HorizontalStock.blend'),compress=True)
(O/'stock_construction.json').write_text(json.dumps(records,indent=2))
print('HORIZONTAL_STOCK_AUTHORED',records)
