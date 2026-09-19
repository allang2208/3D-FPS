import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(P/'seed_91713/textured_master_00001_.glb'))
high=next(o for o in bpy.context.scene.objects if o.type=='MESH')
high.data.transform(high.matrix_world);high.parent=None;high.matrix_world=Matrix.Identity(4)
high.data.transform(Matrix.Rotation(-math.pi/2,4,'Z'))
high.name='StableGrip_Master'
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low)
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
low.data.calc_loop_triangles();dec=low.modifiers.new('Game reduction','DECIMATE');dec.ratio=min(1,30000/len(low.data.loop_triangles));dec.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=dec.name)
mat=low.data.materials[0];mat.name='M_StableAntiSlipRearGrip'
bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
base=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and any(l.to_socket==bs.inputs['Base Color'] for l in n.outputs['Color'].links))
packed=next(n.image for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image!=base)
for name,img in [('BaseColor',base),('MetalRough',packed)]:
    img.filepath_raw=str(P/('T_StableAntiSlipRearGrip_'+name+'.png'));img.file_format='PNG';img.save()
canonical=low.data.copy();high.hide_set(True);high.hide_render=True
def bounds(points):return Vector([min(v[i] for v in points) for i in range(3)]),Vector([max(v[i] for v in points) for i in range(3)])
sl,sh=bounds([v.co for v in canonical.vertices]);source_head=[v.co for v in canonical.vertices if v.co.z>sh.z-(sh.z-sl.z)*.10]
head_center=sum(source_head,Vector())/len(source_head)
report={}
for family in ['M4','AKM','QBZ191']:
    path=P.parent/'PhantomRearGripSeamFit20260913'/(family+'_Assembly_Editable.blend')
    with bpy.data.libraries.load(str(path),link=False) as (src,dst):dst.objects=['FactoryMountReference']
    factory=dst.objects[0];bpy.context.collection.objects.link(factory)
    points=[factory.matrix_world@v.co for v in factory.data.vertices];tl,th=bounds(points)
    # Fit the solid top head to the factory mating region, not an ornamental extremity.
    floor=th.z-(th.z-tl.z)*.18
    target_head=[v for v in points if v.z>=floor];target_center=sum(target_head,Vector())/len(target_head)
    scale=(th.z-tl.z)/(sh.z-sl.z)
    transform=Matrix.Translation(target_center)@Matrix.Diagonal(((th.x-tl.x)/(sh.x-sl.x),scale,scale,1))@Matrix.Translation(-head_center)
    low.data=canonical.copy();low.data.transform(transform);low.name='SM_StableAntiSlipRearGrip'
    # Preserve the actual receiver-facing factory surface as a short interface collar.
    collar=factory.copy();collar.data=factory.data.copy();bpy.context.collection.objects.link(collar);collar.hide_set(False)
    collar.data.transform(collar.matrix_world);collar.matrix_world=Matrix.Identity(4)
    bm=bmesh.new();bm.from_mesh(collar.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,floor),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
    bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
    bmesh.ops.triangulate(bm,faces=list(bm.faces));bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    uv=bm.loops.layers.uv.verify()
    for f in bm.faces:
        axes=[i for i in range(3) if i!=max(range(3),key=lambda j:abs(f.normal[j]))]
        for loop in f.loops:loop[uv].uv=(loop.vert.co[axes[0]]*10,loop.vert.co[axes[1]]*10)
    bm.to_mesh(collar.data);bm.free()
    collar.data.materials.clear();cm=bpy.data.materials.new('M_StableGrip_Collar_'+family);cm.diffuse_color=(.018,.018,.018,1);collar.data.materials.append(cm)
    bpy.ops.object.select_all(action='DESELECT');low.select_set(True);collar.select_set(True);bpy.context.view_layer.objects.active=low;bpy.ops.object.join()
    out=P/family;out.mkdir(exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(out/'SM_StableAntiSlipRearGrip.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'StableAntiSlipRearGrip_Editable.blend'))
    report[family]={'transform':[list(row) for row in transform],'factory_mount_center':list(target_center),'collar_floor':floor,'triangles':len(low.data.polygons)}
    bpy.data.objects.remove(factory,do_unlink=True)
(P/'authoring.json').write_text(json.dumps(report,indent=2))
