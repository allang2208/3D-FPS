"""Rearrange the existing baked V4 assembly; retain UVs, material slots and blade pivot."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,kdtree

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/WoodworkingBenchV5Clean20261012'
GAME=OUT/'GameReady'
source=json.loads((ROOT/'SourceAssets/WoodworkingBenchV4/ProductionRecords/blend_inspection.json').read_text())
old=json.loads((ROOT/'SourceAssets/WoodworkingBenchV4/GameReady/game_manifest.json').read_text())
scene=bpy.context.scene
groups={}
for rec in source['objects']:
    group=rec.get('props',{}).get('layout_group','')
    if rec['name'].startswith(('Rip fence','Fence polished','Fence front','Fence lock')):group='StoredFence'
    if rec['name'].startswith('Push paddle'):group='StoredPaddle'
    groups.setdefault(group,[]).append(rec)
# Whole assemblies rest on the existing side bench or lower shelves, with clear gaps.
targets={
 'BowFormJig':((-1.115,-1.225,.2065),0,'side_lower_shelf'),
 'WoodLathe':((.55,-1.16,.2065),0,'long_lower_shelf_rear'),
 'CarvingVise':((.65,.48,.2065),0,'long_lower_shelf_front'),
 'StaffAssembly':((-1.09,-1.245,.938),0,'side_table_left'),
 'CarvingTools':((-.55,-.920,.938),0,'side_table_front'),
 'HandTools':((-.55,-1.235,.938),90,'side_table_rear'),
 'SharpeningStone':((.17,-1.050,.938),0,'side_table_right'),
 'StoredFence':((.54,-.505,.2065),0,'long_lower_shelf_middle'),
 'StoredPaddle':((.23,-1.250,.938),0,'side_table_rear_right')
}
deps=bpy.context.evaluated_depsgraph_get()
transforms={};report=[];lookup=[]
for group,(target,angle,support) in targets.items():
    records=groups[group];rotation=Matrix.Rotation(math.radians(angle),4,'Z')
    coords=[];evaluated=[]
    for rec in records:
        obj=bpy.data.objects.get(rec['name'])
        if not obj:raise RuntimeError('Missing source object '+rec['name'])
        ev=obj.evaluated_get(deps);mesh=ev.to_mesh()
        points=[obj.matrix_world@v.co for v in mesh.vertices];ev.to_mesh_clear()
        evaluated.extend(points);coords.extend(rotation@v for v in points)
    low=Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    transform=Matrix.Translation(Vector(target)-low)@rotation;transforms[group]=transform
    moved=[transform@v for v in evaluated]
    report.append(dict(group=group,support=support,objects=len(records),min=[min(v[i] for v in moved) for i in range(3)],max=[max(v[i] for v in moved) for i in range(3)],matrix=[list(r) for r in transform]))
    lookup.extend((v,group) for v in evaluated)

tree=kdtree.KDTree(len(lookup))
for i,(v,_) in enumerate(lookup):tree.insert(v,i)
tree.balance()
counts={}
def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:obj.hide_set(False);obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
def bounds(obj):
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    return dict(min=[min(v[i] for v in pts) for i in range(3)],max=[max(v[i] for v in pts) for i in range(3)])

outputs=[]
for name in ['SM_WoodworkingBench','SM_WoodworkingBenchBody']:
    obj=bpy.data.objects[name];mesh=obj.data
    props_indices={p.index for p in mesh.polygons if mesh.materials[p.material_index].name=='WW_PropsAtlas'}
    movable={idx for p in mesh.polygons if p.index in props_indices for idx in p.vertices}
    vertex_groups={};matrix_inv=obj.matrix_world.inverted()
    for idx in movable:
        point=obj.matrix_world@mesh.vertices[idx].co;_,nearest,distance=tree.find(point)
        if distance>0.000015:continue
        group=lookup[nearest][1];vertex_groups[idx]=group
    normals=[loop.vector.copy() for loop in mesh.corner_normals]
    for idx,group in vertex_groups.items():mesh.vertices[idx].co=matrix_inv@transforms[group]@obj.matrix_world@mesh.vertices[idx].co
    for loop in mesh.loops:
        group=vertex_groups.get(loop.vertex_index)
        if group:normals[loop.index]=(transforms[group].to_3x3()@normals[loop.index]).normalized()
    mesh.update();mesh.normals_split_custom_set(normals)
    counts[name]={g:sum(v==g for v in vertex_groups.values()) for g in targets}
    if any(n==0 for n in counts[name].values()):raise RuntimeError('Could not remap entire assembly '+str(counts[name]))
    outputs.append(obj)
# Move editable source objects too; old .blend stays untouched.
for group in targets:
    for rec in groups[group]:
        obj=bpy.data.objects[rec['name']];obj.matrix_world=transforms[group]@obj.matrix_world

# Update only the collision volumes corresponding to moved assemblies.
collision_groups={15:'BowFormJig',16:'WoodLathe',17:'CarvingVise',18:'CarvingTools',19:'StaffAssembly',20:'StaffAssembly',21:'StaffAssembly'}
boxes=[]
for i,b in enumerate(old['collision_boxes_m']):
    if i in collision_groups:
        t=transforms[collision_groups[i]]
        pts=[t@Vector((x,y,z)) for x in (b['min'][0],b['max'][0]) for y in (b['min'][1],b['max'][1]) for z in (b['min'][2],b['max'][2])]
        boxes.append(dict(min=[min(p[j] for p in pts) for j in range(3)],max=[max(p[j] for p in pts) for j in range(3)]))
    else:boxes.append(b)
for g in ['HandTools','SharpeningStone','StoredFence','StoredPaddle']:
    rec=next(r for r in report if r['group']==g);boxes.append(dict(min=rec['min'],max=rec['max']))

mesh_records=[]
for obj in outputs:
    cols=[]
    for i,b in enumerate(boxes):
        lo,hi=b['min'],b['max'];bpy.ops.mesh.primitive_cube_add(size=1,location=[(a+z)/2 for a,z in zip(lo,hi)])
        c=bpy.context.object;c.name=f'UCX_{obj.name}_{i:02}';c.dimensions=[max(.003,z-a) for a,z in zip(lo,hi)]
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);cols.append(c)
    triangles=[]
    for lod,ratio in [(0,1),(1,.55),(2,.24)]:
        mesh=obj
        if lod:
            mesh=obj.copy();mesh.data=obj.data.copy();scene.collection.objects.link(mesh);select([mesh])
            dec=mesh.modifiers.new('DistanceOnlyReduction','DECIMATE');dec.ratio=ratio;dec.use_collapse_triangulate=True;dec.delimit={'MATERIAL','UV','NORMAL'}
            bpy.ops.object.modifier_apply(modifier=dec.name)
        select([mesh]+(cols if lod==0 else []))
        bpy.ops.export_scene.fbx(filepath=str(GAME/f'{obj.name}_LOD{lod}.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
        mesh.data.calc_loop_triangles();triangles.append(len(mesh.data.loop_triangles))
        if lod:bpy.data.objects.remove(mesh,do_unlink=True)
    for c in cols:bpy.data.objects.remove(c,do_unlink=True)
    mesh_records.append(dict(name=obj.name,lod_triangles=triangles,bounds_m=bounds(obj),materials=[m.name for m in obj.data.materials],collision_boxes=len(boxes)))
    obj.hide_set(True)
select([outputs[0]])
bpy.ops.wm.save_as_mainfile(filepath=str(GAME/'WoodworkingBench_CleanLayout.blend'))
manifest=dict(revision='V5Clean20261012',source='SourceAssets/WoodworkingBenchV4/GameReady/WoodworkingBench_GameReady.blend',groups=report,remapped_vertices=counts,meshes=mesh_records,collision_boxes_m=boxes,blade_pivot_cm=[86.5,0,88.8],retained_materials='/Game/Building/WoodworkingBenchV4',retained_placement_bounds_m=old['meshes'][0]['bounds_m'],gameplay_tested=False)
(OUT/'layout_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('WOODWORKING_CLEAN_EXPORT_SAVED',str(GAME),counts,flush=True)
