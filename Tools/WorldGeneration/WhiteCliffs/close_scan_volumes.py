"""Preserve the licensed scan face/UVs and give quarry fins a textured closed back."""
import bpy, json
from pathlib import Path
from mathutils import Vector

ROOT=Path('D:/FPS3D')
OUT=ROOT/'FPSGAME/SourceAssets/HillsLandscapeRepair20261117/SolidScansR9'
OUT.mkdir(parents=True,exist_ok=True)
records=[]
for folder,name in [('Quarry_Cliff-5c019f10','CliffA'),('Quarry_Cliff-9caa4be4','CliffB')]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source=next((ROOT/'VaultCache/FabLibrary'/folder/'Extracted').glob('*.fbx'))
    bpy.ops.import_scene.fbx(filepath=str(source))
    old=next(o for o in bpy.context.scene.objects if o.type=='MESH')
    data=old.data;uv=data.uv_layers.active
    points=[old.matrix_world@v.co for v in data.vertices]
    normals=old.matrix_world.to_3x3().inverted().transposed()
    plane=max(p.y for p in points)+.08
    count=len(points)
    points += [Vector((p.x,2*plane-p.y,p.z)) for p in points[:]]
    faces=[];uvs=[];ns=[];edge_uses={};directed={}
    for poly in data.polygons:
        ids=list(poly.vertices)
        coords=[tuple(uv.data[i].uv) for i in poly.loop_indices]
        fn=[(normals@data.corner_normals[i].vector).normalized() for i in poly.loop_indices]
        faces.append(ids);uvs.append(coords);ns.append(fn)
        faces.append([i+count for i in reversed(ids)])
        uvs.append(list(reversed(coords)))
        ns.append([Vector((n.x,-n.y,n.z)) for n in reversed(fn)])
        for a,b in zip(ids,ids[1:]+ids[:1]):
            key=tuple(sorted((a,b)));edge_uses[key]=edge_uses.get(key,0)+1;directed[key]=(a,b)
    # Continuous UV distance around each open boundary avoids restarting the
    # texture on hundreds of narrow edge strips.
    remaining={key for key,n in edge_uses.items() if n==1};distance={}
    while remaining:
        key=min(remaining);arc=0.
        while key in remaining:
            remaining.remove(key);a,b=directed[key];length=(points[b]-points[a]).length
            distance[key]=(arc,arc+length);arc+=length
            following=next((k for k in remaining if directed[k][0]==b),None)
            if following is None:break
            key=following
    side_start=len(faces)
    # Close every original open edge. Each side gets non-degenerate metric UVs.
    for key,uses in edge_uses.items():
        if uses!=1:continue
        a,b=directed[key];ua,ub=distance[key]
        depth_a=(points[a+count]-points[a]).length
        depth_b=(points[b+count]-points[b]).length
        for ids,coords in [([b,a,a+count],[(ub,0),(ua,0),(ua,depth_a)]),
                           ([b,a+count,b+count],[(ub,0),(ua,depth_a),(ub,depth_b)])]:
            n=(points[ids[1]]-points[ids[0]]).cross(points[ids[2]]-points[ids[0]]).normalized()
            faces.append(ids);uvs.append(coords);ns.append([n]*3)
    side_normals={}
    for ids in faces[side_start:]:
        n=(points[ids[1]]-points[ids[0]]).cross(points[ids[2]]-points[ids[0]])
        for i in ids:side_normals[i]=side_normals.get(i,Vector())+n
    for index in range(side_start,len(faces)):
        ns[index]=[side_normals[i].normalized() for i in faces[index]]
    mesh=bpy.data.meshes.new('Closed_'+name);mesh.from_pydata(points,[],faces);mesh.update()
    layer=mesh.uv_layers.new(name='ScanUV')
    loop_normals=[]
    for poly,coords,fn in zip(mesh.polygons,uvs,ns):
        poly.use_smooth=True
        for i,coord,n in zip(poly.loop_indices,coords,fn):layer.data[i].uv=coord;loop_normals.append(n)
    mesh.normals_split_custom_set(loop_normals)
    obj=bpy.data.objects.new('SM_White'+name+'_SolidR9',mesh);bpy.context.collection.objects.link(obj)
    for mat in data.materials:mesh.materials.append(mat)
    cut_slot=len(mesh.materials);mesh.materials.append(bpy.data.materials.new('LimestoneCut'))
    for poly in list(mesh.polygons)[side_start:]:poly.material_index=cut_slot
    bpy.data.objects.remove(old,do_unlink=True)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    edges={}
    for poly in mesh.polygons:
        for edge in poly.edge_keys:edges[edge]=edges.get(edge,0)+1
    bad=sum(n!=2 for n in edges.values())
    if bad:raise RuntimeError(f'{name}: {bad} non-manifold edges after closure')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(name+'.blend')))
    fbx=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',
        axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    records.append({'name':obj.name,'source':str(source),'fbx':str(fbx),'vertices':len(points),
        'triangles':sum(len(f)-2 for f in faces),'non_manifold_edges':bad,
        'source_boundary_edges':sum(n==1 for n in edge_uses.values()),
        'size_cm':[(max(p[i] for p in points)-min(p[i] for p in points))*100 for i in range(3)],
        'front_uv_and_normals_preserved':True,'back':'mirrored scanned surface with closed boundary strips'})
(OUT/'manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
