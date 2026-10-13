"""Remove the complete overhead guard, preserving V5 placements and surface attributes."""
import bpy,json
from pathlib import Path
from mathutils import kdtree

ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/WoodworkingBenchV6Controls20261013';GAME=OUT/'GameReady'
old=json.loads((ROOT/'SourceAssets/WoodworkingBenchV5Clean20261012/layout_manifest.json').read_text())
source=json.loads((ROOT/'SourceAssets/WoodworkingBenchV4/ProductionRecords/blend_inspection.json').read_text())
guard=[r['name'] for r in source['objects'] if r['name'].startswith(('Blade guard','Guard '))]
deps=bpy.context.evaluated_depsgraph_get()
def points(names):
    result=[]
    for name in names:
        o=bpy.data.objects[name];e=o.evaluated_get(deps);m=e.to_mesh()
        result.extend(o.matrix_world@v.co for v in m.vertices);e.to_mesh_clear()
    tree=kdtree.KDTree(len(result))
    for i,v in enumerate(result):tree.insert(v,i)
    tree.balance();return tree
remove=points(guard);blade=points(['Driven circular blade'])
paint=bpy.data.materials.new('WW_SawEdgePaint');paint.diffuse_color=(.7,.02,.015,1)
records=[]
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def extent(obj):
    xyz=[obj.matrix_world@v.co for v in obj.data.vertices]
    return dict(min=[min(v[i] for v in xyz) for i in range(3)],max=[max(v[i] for v in xyz) for i in range(3)])
for name in ['SM_WoodworkingBench','SM_WoodworkingBenchBody','SM_WoodworkingSawBlade']:
    obj=bpy.data.objects[name];mesh=obj.data;is_blade=name.endswith('SawBlade')
    deleted=set();painted=set()
    if not is_blade:
        matched={v.index for v in mesh.vertices if remove.find(obj.matrix_world@v.co)[2]<.000015}
        blade_vertices={v.index for v in mesh.vertices if blade.find(obj.matrix_world@v.co)[2]<.000015}
        deleted={p.index for p in mesh.polygons if all(i in matched for i in p.vertices)}
        painted={p.index for p in mesh.polygons if all(i in blade_vertices for i in p.vertices)}
        if not deleted:raise RuntimeError('No guard removed from '+name)
    else:painted={p.index for p in mesh.polygons}
    faces=[p for p in mesh.polygons if p.index not in deleted]
    verts=sorted({i for p in faces for i in p.vertices});index={v:i for i,v in enumerate(verts)}
    loops=[i for p in faces for i in p.loop_indices]
    normals=[mesh.corner_normals[i].vector.copy() for i in loops]
    output=bpy.data.meshes.new(name+'_NoGuard')
    output.from_pydata([mesh.vertices[i].co.copy() for i in verts],[],[[index[i] for i in p.vertices] for p in faces])
    for mat in mesh.materials:output.materials.append(mat)
    edge_slot=len(output.materials);output.materials.append(paint)
    for p,prior in zip(output.polygons,faces):
        p.material_index=edge_slot if prior.index in painted else prior.material_index;p.use_smooth=prior.use_smooth
    for uv in mesh.uv_layers:
        layer=output.uv_layers.new(name=uv.name)
        for new_i,old_i in enumerate(loops):layer.data[new_i].uv=uv.data[old_i].uv
    for attr in mesh.color_attributes:
        layer=output.color_attributes.new(name=attr.name,type=attr.data_type,domain=attr.domain)
        for new_i,old_i in enumerate(verts if attr.domain=='POINT' else loops):layer.data[new_i].color=attr.data[old_i].color
    output.update();output.normals_split_custom_set(normals);obj.data=output
    cols=[]
    # The removed overhead parts had no separate simple-collision boxes in V5.
    if not is_blade:
        for i,b in enumerate(old['collision_boxes_m']):
            lo,hi=b['min'],b['max'];bpy.ops.mesh.primitive_cube_add(size=1,location=[(a+z)/2 for a,z in zip(lo,hi)])
            c=bpy.context.object;c.name=f'UCX_{name}_{i:02}';c.dimensions=[max(.003,z-a) for a,z in zip(lo,hi)]
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);cols.append(c)
    counts=[]
    for lod,ratio in [(0,1),(1,.55),(2,.24 if not is_blade else .34)]:
        part=obj
        if lod:
            part=obj.copy();part.data=obj.data.copy();bpy.context.scene.collection.objects.link(part);select([part])
            dec=part.modifiers.new('RetainedDistanceLOD','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True;dec.delimit={'MATERIAL','UV','NORMAL'}
            bpy.ops.object.modifier_apply(modifier=dec.name)
        select([part]+(cols if lod==0 else []))
        bpy.ops.export_scene.fbx(filepath=str(GAME/f'{name}_LOD{lod}.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
        part.data.calc_loop_triangles();counts.append(len(part.data.loop_triangles))
        if lod:bpy.data.objects.remove(part,do_unlink=True)
    for c in cols:bpy.data.objects.remove(c,do_unlink=True)
    records.append(dict(name=name,removed_guard_faces=len(deleted),painted_blade_faces=len(painted),lod_triangles=counts,bounds_m=extent(obj),collision_boxes=len(cols),material_slots=[m.name for m in output.materials]))
    obj.hide_set(True)
for name in guard:bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
select([bpy.data.objects['SM_WoodworkingBench']])
bpy.ops.wm.save_as_mainfile(filepath=str(GAME/'WoodworkingBench_NoGuard_RedEdge.blend'))
manifest=dict(revision='V6Controls20261013',source='SourceAssets/WoodworkingBenchV5Clean20261012/GameReady/WoodworkingBench_CleanLayout.blend',removed_guard_objects=guard,meshes=records,collision_boxes_m=old['collision_boxes_m'],retained_placement_bounds_m=old['retained_placement_bounds_m'],blade_pivot_cm=[86.5,0,88.8],retained_layout=old['groups'],gameplay_tested=False)
(OUT/'layout_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('WOODWORKING_V6_EXPORT_SAVED',records,flush=True)
