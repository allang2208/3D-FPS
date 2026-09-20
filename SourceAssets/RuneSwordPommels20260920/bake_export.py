"""Bake production PBR atlases and export FBX/GLB without any preview rendering."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent;OUT=P/'Export';TEX=P/'Textures'
OUT.mkdir(exist_ok=True);TEX.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'RuneSword_Pommels_Editable.blend'))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=4
scene.render.bake.margin=12;scene.render.bake.use_clear=True;scene.render.bake.use_selected_to_active=False
scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False
scene.render.bake.use_pass_color=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.image_settings.color_depth='8'
rows=json.loads((P/'authoring_manifest.json').read_text())
NAMES={'meteor':'SM_RunePommel_Meteor','jade_core':'SM_RunePommel_JadeStar','swift':'SM_RunePommel_Swiftstar'}
recipe=[];output=[]

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False;obj.select_set(True);bpy.context.view_layer.objects.active=obj

def make_target(row):
    coll=bpy.data.collections.new('Export_'+row['id']);scene.collection.children.link(coll)
    copies=[]
    for name in row['components']:
        src=bpy.data.objects[name];obj=src.copy();obj.data=src.data.copy();coll.objects.link(obj)
        obj.name=src.name+'_Export';activate(obj)
        bpy.ops.object.convert(target='MESH');obj=bpy.context.object
        if obj.data.uv_layers:obj.data.uv_layers[0].name='SourceUV'
        else:obj.data.uv_layers.new(name='SourceUV')
        obj.data.transform(obj.matrix_world);obj.matrix_world=Matrix.Identity(4)
        copies.append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in copies:obj.select_set(True)
    bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join()
    obj=bpy.context.object;obj.name=NAMES[row['id']]
    tri=obj.modifiers.new('Final tangent-space triangles','TRIANGULATE')
    tri.keep_custom_normals=True;tri.quad_method='FIXED';tri.ngon_method='CLIP'
    bpy.ops.object.modifier_apply(modifier=tri.name)
    obj.data.uv_layers.new(name='BakeUV');obj.data.uv_layers.active_index=1
    obj.data.uv_layers['BakeUV'].active_render=True
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(55),island_margin=.006,correct_aspect=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    return obj

def principled(mat):return next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')

def channel_override(material,channel):
    nt=material.node_tree;n=nt.nodes;l=nt.links
    out=next(x for x in n if x.type=='OUTPUT_MATERIAL' and x.is_active_output)
    old=[(link.from_socket,link.to_socket) for link in out.inputs['Surface'].links]
    for link in list(out.inputs['Surface'].links):l.remove(link)
    emission=n.new('ShaderNodeEmission');p=principled(material);extra=[]
    if channel=='BaseColor':socket=p.inputs['Base Color']
    elif channel=='Metallic':socket=p.inputs['Metallic']
    elif channel=='Roughness':socket=p.inputs['Roughness']
    else:socket=p.inputs['Emission Color']
    if socket.is_linked:l.new(socket.links[0].from_socket,emission.inputs['Color'])
    else:
        value=socket.default_value
        emission.inputs['Color'].default_value=(value,value,value,1) if isinstance(value,(float,int)) else value
    if channel=='Emissive':
        emission.inputs['Strength'].default_value=p.inputs['Emission Strength'].default_value/3.
    l.new(emission.outputs[0],out.inputs['Surface'])
    return old,[emission]+extra

def bake(obj,key):
    folder=TEX/key;folder.mkdir(exist_ok=True);files={}
    materials=list(dict.fromkeys(obj.data.materials))
    for channel in ['BaseColor','Metallic','Roughness','Normal','Emissive']:
        im=bpy.data.images.new(key+'_'+channel,width=2048,height=2048,alpha=False)
        im.colorspace_settings.name='sRGB' if channel in ['BaseColor','Emissive'] else 'Non-Color'
        bake_nodes=[];restore=[]
        for mat in materials:
            nt=mat.node_tree
            for node in nt.nodes:node.select=False
            node=nt.nodes.new('ShaderNodeTexImage');node.image=im;node.select=True;nt.nodes.active=node;bake_nodes.append((nt,node))
            if channel!='Normal':restore.append((mat,*channel_override(mat,channel)))
        activate(obj)
        print('BAKE_BEGIN',key,channel,flush=True)
        bpy.ops.object.bake(type='NORMAL' if channel=='Normal' else 'EMIT',normal_space='TANGENT')
        path=folder/(key+'_'+channel+'.png');im.filepath_raw=str(path);im.file_format='PNG';im.save()
        files[channel]=str(path)
        for mat,old,temp in restore:
            for node in temp:mat.node_tree.nodes.remove(node)
            for a,b in old:mat.node_tree.links.new(a,b)
        for nt,node in bake_nodes:nt.nodes.remove(node)
        print('BAKE_SAVED',path,flush=True)
    return files

def baked_material(key,category,files):
    mat=bpy.data.materials.new('M_RunePommel_'+key+'_'+category);mat.use_nodes=True
    nt=mat.node_tree;p=principled(mat);uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='BakeUV'
    for channel,socket in [('BaseColor','Base Color'),('Metallic','Metallic'),('Roughness','Roughness'),('Emissive','Emission Color')]:
        tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(files[channel],check_existing=True)
        tex.image.colorspace_settings.name='sRGB' if channel in ['BaseColor','Emissive'] else 'Non-Color'
        nt.links.new(uv.outputs['UV'],tex.inputs['Vector']);nt.links.new(tex.outputs['Color'],p.inputs[socket])
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(files['Normal'],check_existing=True);tex.image.colorspace_settings.name='Non-Color'
    normal=nt.nodes.new('ShaderNodeNormalMap');normal.uv_map='BakeUV';nt.links.new(tex.outputs['Color'],normal.inputs['Color'])
    nt.links.new(uv.outputs['UV'],tex.inputs['Vector']);nt.links.new(normal.outputs['Normal'],p.inputs['Normal'])
    p.inputs['Emission Strength'].default_value=3.
    if category=='Crystal':
        p.inputs['Transmission Weight'].default_value=.65;p.inputs['IOR'].default_value=1.46
        p.inputs['Alpha'].default_value=.68
        mat.surface_render_method='DITHERED'
    return mat

for row in rows:
    key=row['id']
    # Hide every original authoring part from Cycles while retaining it in the source.
    for obj in scene.objects:obj.hide_render=True
    target=make_target(row)
    files=bake(target,key)
    categories=[]
    for mat in target.data.materials:
        categories.append('Crystal' if ('JadeCrystal' in mat.name or 'BlueGem' in mat.name) else 'Opaque')
    index={};final_mats=[]
    for category in categories:
        if category not in index:index[category]=len(final_mats);final_mats.append(baked_material(key,category,files))
    for poly in target.data.polygons:poly.material_index=index[categories[poly.material_index]]
    target.data.materials.clear()
    for mat in final_mats:target.data.materials.append(mat)
    # The delivery mesh has a single UV set; the editable components retain SourceUV.
    original=target.data.uv_layers.get('SourceUV')
    if original:target.data.uv_layers.remove(original)
    target.data.uv_layers.active_index=0
    target.data.calc_loop_triangles()
    activate(target)
    fbx=OUT/(target.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='COPY',embed_textures=False)
    glb=OUT/(target.name+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_apply=True,export_texcoords=True,export_normals=True,export_tangents=True)
    rowout={'id':key,'mesh':target.name,'fbx':str(fbx),'glb':str(glb),'textures':files,'materials':[m.name for m in final_mats],
       'interface':'azure_hilt_v1','location_cm':[0,0,-19.5],
       'vertices':len(target.data.vertices),'triangles':len(target.data.loop_triangles),
       'bounds_cm':[[min(v.co[i] for v in target.data.vertices)*100 for i in range(3)],[max(v.co[i] for v in target.data.vertices)*100 for i in range(3)]]}
    output.append(rowout)
    target.hide_set(True);target.hide_render=True
    print('MODEL_EXPORTED',json.dumps(rowout),flush=True)
    (P/'model_exports.json').write_text(json.dumps(output,indent=2),encoding='utf-8')

for obj in scene.objects:obj.hide_set(True);obj.hide_render=True
show=bpy.data.objects[NAMES['meteor']];show.hide_set(False);show.hide_render=False;activate(show)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'RuneSword_Pommels_PBR.blend'))
print('POMMEL_PBR_EXPORTS_COMPLETE',flush=True)
