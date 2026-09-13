"""Blender: cut the source tree bases at their original 42 cm plane, without renders."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Matrix
ROOT=Path(__file__).parent/'OriginalStumps'
bpy.ops.wm.read_factory_settings(use_empty=True)
report={};deliveries=[]
for kind in 'ABCD':
    before=set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/('SourceTree_'+kind+'.fbx')),use_anim=False)
    imported=set(bpy.data.objects)-before
    meshes=[o for o in imported if o.type=='MESH']
    non_meshes=[o for o in imported if o.type!='MESH']
    bpy.ops.object.select_all(action='DESELECT')
    for o in meshes:
        matrix=o.matrix_world.copy();o.parent=None;o.data.transform(matrix);o.matrix_world=Matrix.Identity(4)
        o.modifiers.clear();o.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join()
    obj=bpy.context.object;obj.name='SM_OriginalStump_'+kind
    print('SOURCE_GEOMETRY',kind,len(obj.data.vertices),list(obj.dimensions),
        [(min(v.co[i] for v in obj.data.vertices),max(v.co[i] for v in obj.data.vertices)) for i in range(3)],flush=True)
    # The exported FBX is imported in metres. Preserve its origin and all bark UVs.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
        plane_co=(0,0,.42),plane_no=(0,0,1),clear_inner=False,clear_outer=True)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-5)
    rim=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-.42)<1e-5 for v in e.verts)]
    if not rim:raise RuntimeError('No actual trunk section at 42 cm: '+kind)
    cap_material=bpy.data.materials.get('TimberEndGrain') or bpy.data.materials.new('TimberEndGrain')
    cap_index=len(obj.data.materials);obj.data.materials.append(cap_material)
    faces=bmesh.ops.holes_fill(bm,edges=rim,sides=0)['faces']
    if not faces:
        points={v for e in rim for v in e.verts}
        print('CUT_TOPOLOGY',kind,len(bm.verts),len(bm.faces),len(rim),
            [(tuple(v.co),sum(v in e.verts for e in rim)) for v in points],flush=True)
        raise RuntimeError('Cannot close cut: '+kind)
    boundary={v for f in faces for v in f.verts}
    cx=(min(v.co.x for v in boundary)+max(v.co.x for v in boundary))*.5
    cy=(min(v.co.y for v in boundary)+max(v.co.y for v in boundary))*.5
    diameter=max(max(v.co.x for v in boundary)-min(v.co.x for v in boundary),max(v.co.y for v in boundary)-min(v.co.y for v in boundary))
    uv=bm.loops.layers.uv.verify()
    for f in faces:
        f.material_index=cap_index;f.smooth=False
        for loop in f.loops:loop[uv].uv=(.5+(loop.vert.co.x-cx)/diameter,.5+(loop.vert.co.y-cy)/diameter)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    cap_bm=bm.copy()
    bmesh.ops.delete(cap_bm,geom=[f for f in cap_bm.faces if f.material_index!=cap_index],context='FACES')
    for v in cap_bm.verts:v.co.z-=.42
    for f in cap_bm.faces:f.material_index=0
    cap_mesh=bpy.data.meshes.new('OriginalCut_'+kind);cap_bm.to_mesh(cap_mesh);cap_bm.free()
    cap_mesh.materials.append(cap_material)
    cap=bpy.data.objects.new('SM_OriginalCut_'+kind,cap_mesh);bpy.context.collection.objects.link(cap)
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    for old in non_meshes:
        if old.name in bpy.data.objects:bpy.data.objects.remove(old,do_unlink=True)
    for mesh in (obj,cap):
        bpy.ops.object.select_all(action='DESELECT');mesh.select_set(True);bpy.context.view_layer.objects.active=mesh
        bpy.ops.export_scene.fbx(filepath=str(ROOT/(mesh.name+'.fbx')),use_selection=True,object_types={'MESH'},
            apply_unit_scale=True,axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
        report[mesh.name]={'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),
            'dimensions_m':list(mesh.dimensions),'materials':[m.name if m else None for m in mesh.data.materials]}
        deliveries.append(mesh)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'OriginalTreeStumps.blend'))
(ROOT/'authoring.json').write_text(json.dumps(report,indent=2))
print('ORIGINAL_TREE_STUMPS_AUTHORED',json.dumps(report),flush=True)
