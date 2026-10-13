# Appended to the V2-derived baking script; keeps authored geometry and surface maps.
import bmesh
W=Path('C:/Users/allan/Documents/Codex/2026-10-04/task-2/woodworking_v4_import_20261008')
def split_copy(original,name,keep_blade):
    o=original.copy();o.data=original.data.copy();scene.collection.objects.link(o);o.name=name
    bm=bmesh.new();bm.from_mesh(o.data);flag=bm.faces.layers.int['WW_Blade']
    bmesh.ops.delete(bm,geom=[f for f in bm.faces if bool(f[flag])!=keep_blade],context='FACES')
    bm.to_mesh(o.data);bm.free();return o
blade=split_copy(props,'SM_WoodworkingSawBlade',True)
props_body=split_copy(props,'Opaque_Body',False)
select([blade]);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
pivot=Vector((.865,0,.888))
for v in blade.data.vertices:v.co-=pivot
blade.location=(0,0,0)
blade.data.calc_loop_triangles();assert len(blade.data.loop_triangles)==1280
select(glass);bpy.ops.object.join();hood=bpy.context.object;hood.data.materials.clear()
clear=bpy.data.materials.new('WW_ClearSawHood');clear.use_nodes=True
bsdf=next(n for n in clear.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bsdf.inputs['Base Color'].default_value=(.55,.73,.76,1);bsdf.inputs['Roughness'].default_value=.08;bsdf.inputs['Transmission Weight'].default_value=.92;bsdf.inputs['IOR'].default_value=1.45
hood.data.materials.append(clear)
for p in hood.data.polygons:p.material_index=0
select([table,props_body,hood]);bpy.ops.object.join();body=bpy.context.object;body.name='SM_WoodworkingBenchBody'
select([body]);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
preview=body.copy();preview.data=body.data.copy();scene.collection.objects.link(preview)
preview_blade=blade.copy();preview_blade.data=blade.data.copy();scene.collection.objects.link(preview_blade);preview_blade.location=pivot
select([preview,preview_blade]);bpy.ops.object.join();preview=bpy.context.object;preview.name='SM_WoodworkingBench'
for o in [body,preview,blade]:
    select([o]);mod=o.modifiers.new('ExportTriangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    o.data.calc_loop_triangles()
assert len(body.data.loop_triangles)==168432-1280
assert len(preview.data.loop_triangles)==168432
# Preserve V2 legs/shelves/L footprint; split the long table collision around the actual saw slot.
old=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/WoodworkingBenchV2/GameReady/game_manifest.json').read_text())
boxes=[]
for i,b in enumerate(old['collision_boxes_m']):
    if i==0:
        lo=b['min'];hi=b['max'];x0,x1,y0,y1=.8525,.8775,-.1875,.1875
        for a,z in [([lo[0],lo[1],lo[2]],[x0,hi[1],hi[2]]),([x1,lo[1],lo[2]],[hi[0],hi[1],hi[2]]),([x0,lo[1],lo[2]],[x1,y0,hi[2]]),([x0,y1,lo[2]],[x1,hi[1],hi[2]])]:boxes.append({'min':a,'max':z})
    else:boxes.append(b)
# New motor/chamber and upper machine fixed assembly; no collision on the rotating blade.
inspection=json.loads((W/'blend_inspection.json').read_text())
for group in ['UnderTableDrive']:
    items=[r for r in inspection['objects'] if r['props'].get('layout_group')==group]
    boxes.append({'min':[min(p['min'][i] for p in items) for i in range(3)],'max':[max(p['max'][i] for p in items) for i in range(3)]})
def export(objects,path):
    select(objects);bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',global_scale=1,apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',use_mesh_modifiers=True,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False,path_mode='STRIP')
def bounds(o):
    pts=[o.matrix_world@Vector(v) for v in o.bound_box]
    return {'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]}
mesh_records=[]
for mesh in [preview,body,blade]:
    cols=[]
    if mesh!=blade:
        for i,b in enumerate(boxes):
            lo,hi=b['min'],b['max'];bpy.ops.mesh.primitive_cube_add(size=1,location=[(a+b)/2 for a,b in zip(lo,hi)])
            o=bpy.context.object;o.name=f'UCX_{mesh.name}_{i:02}';o.dimensions=[max(.01,b-a) for a,b in zip(lo,hi)]
            bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.hide_render=True;cols.append(o)
    export([mesh]+cols,OUT/(mesh.name+'_LOD0.fbx'))
    triangles=[len(mesh.data.loop_triangles)]
    for level,ratio in [(1,.55),(2,.24)]:
        lod=mesh.copy();lod.data=mesh.data.copy();scene.collection.objects.link(lod);select([lod])
        if mesh!=blade:
            mod=lod.modifiers.new('DistanceOnlyReduction','DECIMATE');mod.ratio=ratio;mod.use_collapse_triangulate=True;mod.delimit={'MATERIAL','UV','NORMAL'};bpy.ops.object.modifier_apply(modifier=mod.name)
        lod.data.calc_loop_triangles();triangles.append(len(lod.data.loop_triangles));export([lod],OUT/f'{mesh.name}_LOD{level}.fbx');bpy.data.objects.remove(lod,do_unlink=True)
    for o in cols:bpy.data.objects.remove(o,do_unlink=True)
    mesh_records.append({'name':mesh.name,'lod_triangles':triangles,'bounds_m':bounds(mesh),'collision_boxes':len(cols),'materials':[m.name for m in mesh.data.materials]})
    mesh.hide_set(True)
for o in list(scene.objects):
    if o not in [preview,body,blade]:o.hide_set(True);o.hide_render=True
select([preview]);preview.hide_render=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'WoodworkingBench_GameReady.blend'))
manifest={'source_version':4,'source_objects':423,'source_triangles':168432,'meshes':mesh_records,'table_materials':records,'collision_boxes_m':boxes,'props_atlas':{k:im.filepath_raw for k,im in images.items()},'blade_pivot_source_m':list(pivot),'blade_axis_source':'X','glass':{'source_transmission':.92,'ue_opacity':.12,'roughness':.08,'ior':1.45},'lod0_geometry_reduced':False,'gameplay_tested':False,'notes':['Blender 5.2 source evaluated in 5.1.2; counts match source manifest.','Boolean cut null slot mapped to existing bench wood material.','Principled weight normalized to 1 for 5.1 compatibility.','Blade LOD keeps all 1280 triangles to preserve teeth and hub opening.']}
(OUT/'game_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('WOOD_V4_EXPORT_DONE',json.dumps(mesh_records),flush=True)
