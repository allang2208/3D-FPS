"""Reconstruct continuous wrists beneath the original M09 hand surfaces.

The original crossed-arm partition made disconnected sealed hand/forearm shells.
Create anatomical connecting volume, fuse only the small-arm objects, transfer
their existing UVs and weights, and retain the unchanged rig and other organs.
"""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'ArmContinuityV16'
for d in ('Authoring','Exports','Records'):(OUT/d).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'CrownClawV15/Authoring/M09_Rigged_ClawV15.blend'))
rig=bpy.data.objects['M09_Rig_V03'];report={'parts':[],'animation':'CrownClawV15 newly authored rake','game_tested':False}

def activate(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def tube(points,radii):
    points=[Vector(p) for p in points];v=[];f=[];sides=32
    for i,(p,radius) in enumerate(zip(points,radii)):
        direction=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        x=direction.cross(Vector((0,1,0))).normalized();y=direction.cross(x).normalized()
        for k in range(sides):
            a=k*2*math.pi/sides;v.append(p+radius*(math.cos(a)*x+math.sin(a)*y))
    for i in range(len(points)-1):
        for k in range(sides):
            a=i*sides+k;b=i*sides+(k+1)%sides;f.append((a,b,b+sides,a+sides))
    f.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+k for k in range(sides))])
    return v,f

def transfer(ob,source):
    activate(ob)
    if not ob.data.uv_layers:ob.data.uv_layers.new(name='UVMap')
    for g in source.vertex_groups:
        if not ob.vertex_groups.get(g.name):ob.vertex_groups.new(name=g.name)
    mod=ob.modifiers.new('Preserve source skin coordinates','DATA_TRANSFER');mod.object=source
    mod.use_loop_data=True;mod.data_types_loops={'UV'};mod.loop_mapping='POLYINTERP_NEAREST'
    mod.use_vert_data=True;mod.data_types_verts={'VGROUP_WEIGHTS'};mod.vert_mapping='POLYINTERP_NEAREST'
    bpy.ops.object.modifier_apply(modifier=mod.name)

for side in ('L','R'):
    ob=bpy.data.objects['M09_SmallArm_'+side]
    source=ob.copy();source.data=ob.data.copy();source.name=ob.name+'_V15_Source'
    bpy.context.scene.collection.objects.link(source);source.modifiers.clear();source.parent=None
    source.matrix_world=ob.matrix_world.copy()
    source.hide_render=True
    # Make a temporary world-coordinate reconstruction mesh at the bind pose.
    p=np.empty((len(ob.data.vertices),3));ob.data.vertices.foreach_get('co',p.ravel())
    m=np.array(ob.matrix_world);p=p@m[:3,:3].T+m[:3,3]
    s,e,w,h=[rig.matrix_world@rig.data.bones[n].head_local for n in
        (f'small_upperarm_{side}',f'small_forearm_{side}',f'small_hand_{side}',f'smallfinger_{side}_03_01')]
    fore=(w-e).normalized();hand=(h-w).normalized();axis=(fore+hand).normalized()
    rel=p-np.array(w);along=rel@np.array(axis);radial=rel-along[:,None]*np.array(axis)
    radial_length=np.linalg.norm(radial,axis=1)
    # Replace the jagged interpenetration seam with a tapered wrist surface.
    blend=np.clip((.071-np.abs(along))/.031,0,1);blend=blend*blend*(3-2*blend)
    radius=.029+np.clip(-along,0,.055)*.18
    clean=np.array(w)+along[:,None]*np.array(axis)+radial/np.maximum(radial_length[:,None],1e-9)*radius[:,None]
    p=p*(1-blend[:,None])+clean*blend[:,None]
    faces=[tuple(poly.vertices) for poly in ob.data.polygons]
    # The source proximal arm contains separately capped crossing surfaces.
    # Keep the original palm/digits and replace that faulty sleeve completely.
    hand_mesh=bpy.data.meshes.new('M09_PreservedDistalHand');hand_mesh.from_pydata(p.tolist(),[],faces);hand_mesh.update()
    bm=bmesh.new();bm.from_mesh(hand_mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=.000001,
        plane_co=w-axis*.025,plane_no=axis,clear_inner=True,clear_outer=False)
    border=[edge for edge in bm.edges if edge.is_boundary]
    if border:bmesh.ops.holes_fill(bm,edges=border,sides=0)
    bm.verts.index_update();p=np.array([v.co[:] for v in bm.verts]);faces=[tuple(v.index for v in face.verts) for face in bm.faces]
    bm.free();bpy.data.meshes.remove(hand_mesh)
    # Continuous core joins the hand and forearm and reaches into the original
    # shoulder socket. This becomes one welded surface after local remeshing.
    upper=e-s
    arm_points=[s-upper.normalized()*.025,s,s+upper*.35,s+upper*.75,e,
                e+(w-e)*.10,e+(w-e)*.35,e+(w-e)*.65,w-fore*.02,w,w+hand*.055]
    for points,radii in ((arm_points,[.043,.048,.050,.046,.042,.045,.043,.034,.028,.027,.035]),):
        v,f=tube(points,radii);offset=len(p);p=np.vstack((p,np.array(v)));faces.extend(tuple(offset+j for j in face) for face in f)
    me=bpy.data.meshes.new(ob.name+'_ContinuousVolume');me.from_pydata(p.tolist(),[],faces);me.update()
    work=bpy.data.objects.new(ob.name+'_Work',me);bpy.context.scene.collection.objects.link(work)
    for mat in ob.data.materials:me.materials.append(mat)
    activate(work);me.remesh_voxel_size=.0018;me.remesh_voxel_adaptivity=0.;me.use_remesh_preserve_volume=True
    print('M09_ARM_VOLUME_BEGIN',side,flush=True)
    bpy.ops.object.voxel_remesh()
    print('M09_ARM_VOLUME_COMPLETE',side,len(work.data.vertices),flush=True)
    # Relax voxel steps without shrinking the original digits.
    bm=bmesh.new();bm.from_mesh(work.data)
    near=[]
    for v in bm.verts:
        d=v.co-w
        if abs(d.dot(axis))<.08:near.append(v)
    for _ in range(5):bmesh.ops.smooth_vert(bm,verts=near,factor=.30,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(work.data);bm.free()
    print('M09_ARM_ATTRIBUTES_BEGIN',side,flush=True)
    transfer(work,source)
    print('M09_ARM_ATTRIBUTES_COMPLETE',side,flush=True)
    # The reconstructed proximal arm uses one continuous anatomical field;
    # retain source finger weights only on the preserved distal hand.
    coordinates=np.empty((len(work.data.vertices),3));work.data.vertices.foreach_get('co',coordinates.ravel())
    groups=[g.name for g in work.vertex_groups];weights=np.zeros((len(coordinates),len(groups)))
    for vertex in work.data.vertices:
        for g in vertex.groups:weights[vertex.index,g.group]=g.weight
    def smooth(x):
        x=np.clip(x,0,1);return x*x*(3-2*x)
    u=np.array(upper.normalized());f=np.array(fore);palm=np.array(hand)
    hinge=(u+f)/np.linalg.norm(u+f);wrist_hinge=(f+palm)/np.linalg.norm(f+palm)
    a=smooth(((coordinates-np.array(e))@hinge+.065)/.130)
    b=smooth(((coordinates-np.array(w))@wrist_hinge+.04)/.08)
    root_weight=1-smooth(((coordinates-np.array(s))@u+.012)/.062)
    core=[i for i,name in enumerate(groups) if not name.startswith('smallfinger_')]
    mass=weights[:,core].sum(1);weights[:,core]=0
    for name,value in [(f'small_upperarm_{side}',(1-root_weight)*(1-a)),
                       (f'small_forearm_{side}',(1-root_weight)*a*(1-b)),
                       (f'small_hand_{side}',(1-root_weight)*a*b),('spine_03',root_weight)]:
        if name not in groups:
            work.vertex_groups.new(name=name);groups.append(name);weights=np.pad(weights,((0,0),(0,1)))
        weights[:,groups.index(name)]=mass*value
    quantized=np.rint(weights*1024).astype(np.int32)
    quantized[np.arange(len(weights)),weights.argmax(1)]+=1024-quantized.sum(1)
    all_vertices=list(range(len(weights)))
    for col,g in enumerate(work.vertex_groups):
        g.remove(all_vertices)
        for value in np.unique(quantized[:,col]):
            if value>0:g.add(np.flatnonzero(quantized[:,col]==value).tolist(),float(value)/1024,'REPLACE')
    # Move the reconstruction back into the original object's transform. Other
    # parts, bone hierarchy, materials and their runtime references stay intact.
    inv=ob.matrix_world.inverted()
    coordinates=np.empty((len(work.data.vertices),3));work.data.vertices.foreach_get('co',coordinates.ravel())
    mi=np.array(inv);coordinates=coordinates@mi[:3,:3].T+mi[:3,3]
    work.data.vertices.foreach_set('co',coordinates.ravel())
    work.data.polygons.foreach_set('use_smooth',np.ones(len(work.data.polygons),bool))
    work.data.polygons.foreach_set('material_index',np.zeros(len(work.data.polygons),np.int32))
    for g in list(ob.vertex_groups):ob.vertex_groups.remove(g)
    ob.data=work.data
    # Blender 5.1 stores the group definitions on the shared mesh. Assigning
    # the data already carries them; appending while iterating would duplicate
    # that same collection indefinitely and clearing it would erase the skin.
    report['parts'].append({'name':ob.name,'vertices':len(ob.data.vertices),'faces':len(ob.data.polygons),
        'voxel_mm':1.8,'UV':'nearest source surface interpolation','reconstructed':'wrist and shoulder junction'})
    bpy.data.objects.remove(work,do_unlink=True);bpy.data.objects.remove(source,do_unlink=True)
    print('M09_CONTINUOUS_ARM',side,len(ob.data.vertices),flush=True)

rig.animation_data_clear()
for pb in rig.pose.bones:pb.location=(0,0,0);pb.rotation_mode='QUATERNION';pb.rotation_quaternion=(1,0,0,0);pb.scale=(1,1,1)
bpy.context.scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_ContinuousArms_V16.blend'),compress=True)
(OUT/'Records/reconstruction.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('M09_ARM_CONTINUITY_V16_AUTHORED',flush=True)
