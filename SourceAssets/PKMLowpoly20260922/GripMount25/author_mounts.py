"""Fit the existing PKM grip geometry to actual factory interfaces.

Rear bodies are rigidly aligned by the grasp-zone centerline. Fore bodies and
all animation contacts remain fixed; only their mounting surfaces are fitted.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;R=O.parent;E=O/'Exports';E.mkdir(exist_ok=True)
sections=json.loads((O/'sections.json').read_text())
bpy.context.preferences.filepaths.save_version=0
report={};CX=-.0000381814

# Read the actual receiver/gas-housing mating surfaces in root space.
bpy.ops.wm.open_mainfile(filepath=str(O/'MountInspection.blend'),use_scripts=False)
verts=[];faces=[]
for name in ['Factory_PKM_Part_042','Factory_PKM_Part_068']:
    ob=bpy.data.objects[name];offset=len(verts)
    verts.extend(ob.matrix_world@v.co for v in ob.data.vertices)
    faces.extend([i+offset for i in p.vertices] for p in ob.data.polygons)
roof=BVHTree.FromPolygons(verts,faces)
def ceiling(x,y):
    hit=roof.ray_cast(Vector((x,y,-.12)),Vector((0,0,1)),.3)[0]
    return hit.z if hit else None
def coat(ob):
    while len(ob.data.uv_layers)<3:ob.data.uv_layers.new(name='PKM_CoatingUV' if len(ob.data.uv_layers)==2 else 'SourceUV')
    ob.data.update()
    for face in ob.data.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
        for loop in face.loop_indices:
            p=ob.data.vertices[ob.data.loops[loop].vertex_index].co
            ob.data.uv_layers[2].data[loop].uv=(p[axes[0]]/.05,p[axes[1]]/.05)
    ob.data.uv_layers.active_index=0
def bevel(ob,width):
    bpy.context.view_layer.objects.active=ob;ob.select_set(True)
    b=ob.modifiers.new('InterfaceEdge','BEVEL');b.width=width;b.segments=3
    bpy.ops.object.modifier_apply(modifier=b.name)
    n=ob.modifiers.new('InterfaceNormals','WEIGHTED_NORMAL');n.keep_sharp=True
    bpy.ops.object.modifier_apply(modifier=n.name)
def loft(name,rings,mat,width=.0005):
    vertices=[]
    for x0,x1,y0,y1,z in rings:vertices.extend([(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)])
    faces=[(3,2,1,0)]
    for j in range(len(rings)-1):
        a=j*4;b=a+4
        faces.extend([(a+i,a+(i+1)%4,b+(i+1)%4,b+i) for i in range(4)])
    last=4*(len(rings)-1);faces.append(tuple(last+i for i in range(4)))
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(ob);mesh.materials.append(mat)
    bevel(ob,width);coat(ob)
    for a,b in zip(mesh.uv_layers[0].data,mesh.uv_layers[2].data):a.uv=b.uv
    return ob
def bounds(ob):
    points=[ob.matrix_world@v.co for v in ob.data.vertices]
    return {'min':[min(v[i] for v in points) for i in range(3)],'max':[max(v[i] for v in points) for i in range(3)]}
def export(key,obs,info):
    for ob in bpy.context.scene.objects:ob.select_set(False)
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[0]
    name='SM_PKM_'+key
    bpy.ops.export_scene.fbx(filepath=str(E/(name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
    bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
    report[key]={'name':name,**info,'geometry':{o.name:bounds(o) for o in obs},'materials':{o.name:[m.name for m in o.data.materials] for o in obs}}
    (O/'authoring.json').write_text(json.dumps(report,indent=2))
    print('PKM25_MOUNT_EXPORTED',key,flush=True)

for key in ['phantom_reargrip','balanced_reargrip','stable_antislip_reargrip']:
    bpy.ops.wm.open_mainfile(filepath=str(R/'GripContact15'/f'SM_PKM_{key}.blend'),use_scripts=False)
    old=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name!='PKM_GripTang')
    # Work in the measured grasp band, excluding the decorative beavertail,
    # old adapter and bottom flare that skew whole-mesh bounds.
    zs=[-.015,-.03,-.05,-.07]
    def line(label):
        points=[Vector((*sections[label][str(z)]['center'],z)) for z in zs]
        center=sum(points,Vector())/len(points)
        slope=sum((p.z-center.z)*(p.y-center.y) for p in points)/sum((p.z-center.z)**2 for p in points)
        return center,Vector((0,slope,1)).normalized()
    source,axis=line(key);target,direction=line('factory')
    rotation=axis.rotation_difference(direction);xf=Matrix.Translation(target)@rotation.to_matrix().to_4x4()@Matrix.Translation(-source)
    # Preserve all polymer geometry/UV0 and imported corner normals, discard
    # only the malformed donor metal collar and its detached long pad.
    mesh=old.data;mesh.update();normals=[n.vector.copy() for n in mesh.corner_normals]
    kept=[p for p in mesh.polygons if p.material_index==0]
    used_ids=sorted({i for p in kept for i in p.vertices});remap={n:i for i,n in enumerate(used_ids)}
    new=bpy.data.meshes.new('PKM25_'+key+'_Body')
    new.from_pydata([xf@(old.matrix_world@mesh.vertices[i].co) for i in used_ids],[],[[remap[i] for i in p.vertices] for p in kept]);new.update()
    for m in mesh.materials:new.materials.append(m)
    for uv in mesh.uv_layers:
        layer=new.uv_layers.new(name=uv.name);i=0
        for face in kept:
            for loop in face.loop_indices:layer.data[i].uv=uv.data[loop].uv;i+=1
    corner=[]
    for face,src in zip(new.polygons,kept):
        face.material_index=0;face.use_smooth=src.use_smooth
        corner.extend(rotation@normals[l] for l in src.loop_indices)
    new.normals_split_custom_set(corner)
    body=bpy.data.objects.new(old.name+'_Fitted',new);bpy.context.scene.collection.objects.link(body)
    interface=bpy.data.materials.get('PKM14_Interface')
    for ob in list(bpy.context.scene.objects):
        if ob.type=='MESH' and ob!=body:bpy.data.objects.remove(ob,do_unlink=True)
    # A short symmetric adapter seats against the factory grip's receiver
    # footprint; the lower socket encloses the retained grip neck.
    # Each retained donor has a different cap elevation after its rigid fit.
    # Use a cross-section inside that cap, not a shared height above two of
    # the grips. These planes include a small overlap below the measured cap.
    socket_z={'phantom_reargrip':.012,'balanced_reargrip':.0012,
              'stable_antislip_reargrip':.0003}[key]
    neck=[]
    for edge in new.edges:
        a,b=[new.vertices[i].co for i in edge.vertices]
        if (a.z-socket_z)*(b.z-socket_z)<0:
            neck.append(a+(b-a)*((socket_z-a.z)/(b.z-a.z)))
    x0,x1=min(p.x for p in neck),max(p.x for p in neck)
    y0,y1=min(p.y for p in neck),max(p.y for p in neck)
    # Exclude a rear beavertail: it is part of the hand stop, not the socket.
    y0=max(-.011,y0);y1=min(.033,y1)
    collar=loft('PKM_GripTang',[(x0-.0004,x1+.0004,y0-.0006,y1+.0006,socket_z),
        (CX-.0145,CX+.0145,-.011,.033,.0224),
        (CX-.0145,CX+.0145,-.011,.033,.0249)],interface,.0008)
    # Retain a metal collar slot, so the existing finish bindings stay explicit.
    if len(new.materials)>1:collar.data.materials.append(new.materials[1])
    coat(body)
    export(key,[body,collar],{'kind':'rear','rigid_correction':list(map(list,xf)),
           'rake_correction_deg':math.degrees(rotation.angle),'grasp_center_before':list(source),'grasp_center_after':list(target),
           'seat_top_m':.0249,'socket_bottom_m':socket_z,'scale_changed':False})

for key in ['vertical','tactical_vertical','canted','prism','angled']:
    bpy.ops.wm.open_mainfile(filepath=str(R/'Accessories14'/f'SM_PKM_{key}.blend'),use_scripts=False)
    body=next(o for o in bpy.context.scene.objects if o.type=='MESH' and o.name!='PKM_UnderRailFoot')
    pad=bpy.data.objects['PKM_UnderRailFoot'];interface=pad.data.materials[0]
    bpy.data.objects.remove(pad,do_unlink=True)
    mesh=body.data;mesh.update();normals=[n.vector.copy() for n in mesh.corner_normals];changed=set()
    # Keep the grip/grasp region fixed. Bring canted's too-high rail cap to
    # the same mounting plane and trim only angled's buried upper rear edge.
    for v in mesh.vertices:
        old=v.co.copy()
        if key=='canted' and v.co.z>.019:
            v.co.z=.019+(v.co.z-.019)*(.02885269-.019)/(.03485269-.019)
        ceiling_z=ceiling(v.co.x,v.co.y)
        if ceiling_z is not None and v.co.z>ceiling_z-.00025 and v.co.z>.01:
            v.co.z=ceiling_z-.00025
        if (v.co-old).length>1e-7:changed.add(v.index)
    mesh.update()
    for face in mesh.polygons:
        if any(i in changed for i in face.vertices):
            for li in face.loop_indices:normals[li]=face.normal.copy()
    if changed:mesh.normals_split_custom_set(normals)
    ymin,ymax=(-.388437,-.333437) if key=='canted' else (-.403437,-.318437)
    # Angled's donor rail top is 1 mm lower than the other vertical families.
    top_of_clamp=.02785269 if key=='angled' else .02885269
    lower=top_of_clamp-.00035;upper=ceiling(CX,(ymin+ymax)*.5)+.0003
    pad=loft('PKM_UnderRailFoot',[(CX-.013,CX+.013,ymin,ymax,lower),
                                (CX-.013,CX+.013,ymin,ymax,upper)],interface,.0003)
    coat(body)
    export(key,[body,pad],{'kind':'fore','grasp_transform':'identity','modified_upper_vertices':len(changed),
        'pad_bottom_m':lower,'pad_top_m':upper,'seat_overlap_mm':.30,
        'clamp_overlap_mm':.35,'pad_length_mm':(ymax-ymin)*1000})
print('PKM25_MOUNTS_AUTHORED',flush=True)
