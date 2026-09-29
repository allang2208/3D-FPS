"""Retain approved render geometry; fit cart hulls and leave IV geometry collision-free."""
import bpy,bmesh,json
from pathlib import Path
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]
OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
records=[]
for key,folder,source_name,mesh_name,scale in [
    ('MedicalCart','MedicalCart20260929','SM_Hospital_MedicalCart','SM_Ward_MedicalCart',.82),
    ('IVDripCrutch','IVDripCrutch20260929','SM_Hospital_IVDrip_Crutch','SM_Ward_IVDripCrutch',1.)]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC'
    source=PROJECT/'SourceAssets'/folder
    imported=json.loads((source/'install_receipt.json').read_text(encoding='utf-8'))
    bpy.ops.import_scene.fbx(filepath=str(source/'Exports'/(source_name+'.fbx')))
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH']
    colliders=[]
    def hull(points):
        lo=[min(p[k] for p in points) for k in range(3)]
        hi=[max(p[k] for p in points) for k in range(3)]
        if len(points)<4 or min(hi[k]-lo[k] for k in range(3))<.001:return
        bm=bmesh.new()
        for p in set(tuple(v) for v in points):bm.verts.new(p)
        result=bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
        unused=[e for e in result['geom_interior']+result['geom_unused'] if isinstance(e,bmesh.types.BMVert) and e.is_valid]
        if unused:bmesh.ops.delete(bm,geom=list(set(unused)),context='VERTS')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        mesh=bpy.data.meshes.new('FittedCollision');bm.to_mesh(mesh);bm.free()
        obj=bpy.data.objects.new(f'UCX_{mesh_name}_{len(colliders):02d}',mesh)
        bpy.context.collection.objects.link(obj);colliders.append(obj)
    if key=='MedicalCart':
        for obj in objects:
            points=[obj.matrix_world@v.co for v in obj.data.vertices]
            slots={m.name for m in obj.data.materials if m}
            if slots.intersection({'Cart_A','Cart_C'}):
                # Solid drawer cabinet and shallow top tray each retain a broad support.
                hull(points);continue
            keys=[tuple(round(v,5) for v in p) for p in points]
            graph={p:set() for p in keys}
            for edge in obj.data.edges:
                a,b=(keys[i] for i in edge.vertices);graph[a].add(b);graph[b].add(a)
            seen=set()
            for start in graph:
                if start in seen:continue
                pending=[start];seen.add(start);part=[]
                while pending:
                    p=pending.pop();part.append(p)
                    for other in graph[p]:
                        if other not in seen:seen.add(other);pending.append(other)
                hull(part)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join()
    mesh_obj=bpy.context.object;mesh_obj.name=mesh_name
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    for obj in [mesh_obj]+colliders:
        for vertex in obj.data.vertices:vertex.co*=scale
    for obj in colliders:obj.select_set(True)
    bpy.context.view_layer.objects.active=mesh_obj
    fbx=OUT/(mesh_name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(mesh_name+'.blend')))
    records.append(dict(key=key,name=mesh_name,fbx=str(fbx),source_mesh=imported['mesh'],materials=imported['materials'],
        license_file=str(source/'license.txt'),credit=(source/'license.txt').read_text(encoding='utf-8'),
        scale=scale,collision_hulls=len(colliders),blocking=key=='MedicalCart'))
    print('WARD_PROP_AUTHORED',mesh_name,'scale',scale,'hulls',len(colliders),flush=True)
(ROOT/'manifest.json').write_text(json.dumps(dict(objects=records,rendered=False,tested=False),indent=2),encoding='utf-8')
