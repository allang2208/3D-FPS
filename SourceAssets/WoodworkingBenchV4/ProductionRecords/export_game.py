import bpy,json,math,hashlib,shutil
from pathlib import Path
from mathutils import Vector
R=Path('D:/FPS3D/FPSGAME/SourceAssets/WoodworkingBenchV4');OUT=R/'GameReady';OUT.mkdir(parents=True,exist_ok=True);TEX=OUT/'Textures';TEX.mkdir(exist_ok=True)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.threads_mode='FIXED';scene.render.threads=6
scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=12
deps=bpy.context.evaluated_depsgraph_get()
source=[o for o in scene.objects if o.type in {'MESH','CURVE','SURFACE','FONT'}]
assert len(source)==423,len(source)
copied=[];tables=[];glass=[];table=None;material_copies={}
for original in source:
    ev=original.evaluated_get(deps);mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
    o=bpy.data.objects.new('Export_'+original.name,mesh);scene.collection.objects.link(o);o.matrix_world=original.matrix_world.copy()
    for i,m in enumerate(mesh.materials):
        if m is None:mesh.materials[i]=next(x for x in mesh.materials if x is not None)
    blade_flag=mesh.attributes.new('WW_Blade','INT','FACE')
    for value in blade_flag.data:value.value=int(original.name=='Driven circular blade')
    if original.name.startswith('Retained_Table'):
        tables.append(o)
        for i,m in enumerate(mesh.materials):
            if m is None:mesh.materials[i]=bpy.data.materials['WSBench_BenchWood']
    elif any(m and m.name=='Clear saw hood' for m in mesh.materials):glass.append(o)
    else:
        coords=[Vector(c) for c in original.bound_box];lo=Vector([min(c[i] for c in coords) for i in range(3)]);hi=Vector([max(c[i] for c in coords) for i in range(3)])
        attr=mesh.attributes.new('WW_Generated','FLOAT_VECTOR','POINT')
        for vert,value in zip(mesh.vertices,attr.data):value.vector=Vector([(vert.co[i]-lo[i])/max(1e-8,hi[i]-lo[i]) for i in range(3)])
        for i,m in enumerate(mesh.materials):
            if m.name not in material_copies:
                clone=m.copy();clone.name='Bake_'+m.name;nodes=clone.node_tree.nodes;links=clone.node_tree.links
                for bsdf in nodes:
                    if bsdf.type=='BSDF_PRINCIPLED' and 'Weight' in bsdf.inputs:bsdf.inputs['Weight'].default_value=1.0
                generated=nodes.new('ShaderNodeAttribute');generated.attribute_name='WW_Generated'
                for link in list(links):
                    if link.from_node.type=='TEX_COORD' and link.from_socket.name=='Generated':links.new(generated.outputs['Vector'],link.to_socket)
                for node in list(nodes):
                    if node.type=='TEX_NOISE' and not node.inputs['Vector'].is_linked:links.new(generated.outputs['Vector'],node.inputs['Vector'])
                material_copies[m.name]=clone
            mesh.materials[i]=material_copies[m.name]
        for uv in list(mesh.uv_layers):mesh.uv_layers.remove(uv)
        mesh.uv_layers.new(name='UVMap')
        copied.append(o)
    original.hide_render=True;original.hide_set(True)
assert len(tables)==2 and len(glass)==3
# Keep exactly the UV channel used by the source table image textures as game UV0.
for table in tables:
    uv=next((u for u in table.data.uv_layers if u.active_render),table.data.uv_layers.active)
    uv_values=[tuple(v.uv) for v in uv.data]
    for layer in list(table.data.uv_layers):table.data.uv_layers.remove(layer)
    uv=table.data.uv_layers.new(name='UVMap')
    for value,co in zip(uv.data,uv_values):value.uv=co

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
select(tables);bpy.ops.object.join();table=bpy.context.object
select(copied);bpy.ops.object.join();props=bpy.context.object;props.name='Woodworking_V2_Props'
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.001,area_weight=.2);bpy.ops.object.mode_set(mode='OBJECT')
print('WOOD_EXPORT atlas UV complete',flush=True)
mats=list(props.data.materials);original_surfaces={}
for m in mats:
    output=next(n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL')
    original_surfaces[m.name]=(output,output.inputs['Surface'].links[0].from_socket)
def bake(kind,size):
    image=bpy.data.images.new('T_WW_Props_'+kind,width=size,height=size,alpha=False)
    image.colorspace_settings.name='sRGB' if kind in {'BaseColor','Emissive'} else 'Non-Color'
    for m in mats:
        nodes=m.node_tree.nodes;links=m.node_tree.links
        for node in nodes:node.select=False
        target=nodes.new('ShaderNodeTexImage');target.image=image;target.select=True;nodes.active=target
        output,surface=original_surfaces[m.name]
        for link in list(output.inputs['Surface'].links):links.remove(link)
        principled=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
        if kind=='Normal':links.new(surface,output.inputs['Surface']);continue
        emission=nodes.new('ShaderNodeEmission');links.new(emission.outputs[0],output.inputs['Surface'])
        if kind=='BaseColor':
            socket=principled.inputs['Base Color']
            if socket.is_linked:links.new(socket.links[0].from_socket,emission.inputs['Color'])
            else:emission.inputs['Color'].default_value=socket.default_value
        elif kind=='ORM':
            combine=nodes.new('ShaderNodeCombineColor');combine.inputs['Red'].default_value=1
            for name,dest in [('Roughness','Green'),('Metallic','Blue')]:
                socket=principled.inputs[name]
                if socket.is_linked:links.new(socket.links[0].from_socket,combine.inputs[dest])
                else:combine.inputs[dest].default_value=socket.default_value
            links.new(combine.outputs[0],emission.inputs['Color'])
        elif kind=='Emissive':
            emission.inputs['Color'].default_value=principled.inputs['Emission Color'].default_value
            emission.inputs['Strength'].default_value=principled.inputs['Emission Strength'].default_value
    select([props]);bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT',normal_space='TANGENT')
    image.filepath_raw=str(TEX/(image.name+'.png'));image.file_format='PNG';image.save()
    print('WOOD_EXPORT baked '+kind,flush=True)
    return image
images={kind:bake(kind,size) for kind,size in [('BaseColor',4096),('ORM',2048),('Normal',4096),('Emissive',2048)]}
# Save the game representation with baked props and unchanged table texture appearance.
mat=bpy.data.materials.new('WW_PropsAtlas');mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
for kind,im in images.items():
    n=nodes.new('ShaderNodeTexImage');n.image=im
    if kind=='BaseColor':links.new(n.outputs['Color'],p.inputs['Base Color'])
    elif kind=='Normal':
        normal=nodes.new('ShaderNodeNormalMap');links.new(n.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
    elif kind=='ORM':
        sep=nodes.new('ShaderNodeSeparateColor');links.new(n.outputs['Color'],sep.inputs[0]);links.new(sep.outputs['Green'],p.inputs['Roughness']);links.new(sep.outputs['Blue'],p.inputs['Metallic'])
    else:links.new(n.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=1
props.data.materials.clear();props.data.materials.append(mat)
for poly in props.data.polygons:poly.material_index=0
# Table graph conversion record: supported source nodes are retained as textures + exact scalar/color operations.
records=[]
for m in dict.fromkeys(table.data.materials):
    p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    def input_record(socket):
        if not socket.is_linked:
            v=socket.default_value;return {'constant':list(v) if hasattr(v,'__iter__') else v}
        node=socket.links[0].from_node
        if node.type=='TEX_IMAGE':
            f=Path(bpy.path.abspath(node.image.filepath));dst=TEX/f.name
            if not dst.exists():shutil.copyfile(f,dst)
            return {'texture':dst.name,'colorspace':node.image.colorspace_settings.name}
        if node.type=='MIX_RGB':return {'mix':node.blend_type,'factor':input_record(node.inputs[0]),'a':input_record(node.inputs[1]),'b':input_record(node.inputs[2]),'clamp':node.use_clamp}
        if node.type=='MATH':return {'math':node.operation,'a':input_record(node.inputs[0]),'b':input_record(node.inputs[1]),'c':input_record(node.inputs[2]),'clamp':node.use_clamp}
        if node.type=='NORMAL_MAP':return {'normal_map':input_record(node.inputs['Color']),'strength':node.inputs['Strength'].default_value}
        raise RuntimeError('Unsupported original table node '+node.type)
    records.append({'name':m.name,'base_color':input_record(p.inputs['Base Color']),'roughness':input_record(p.inputs['Roughness']),'metallic':input_record(p.inputs['Metallic']),'normal':input_record(p.inputs['Normal'])})
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
