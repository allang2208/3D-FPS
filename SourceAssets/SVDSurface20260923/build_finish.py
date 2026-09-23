"""Author and bake SVD-specific material layers onto the existing corrected UV0.

No mesh export, normal-map filtering, animation edits, render preview or tests.
"""
import bpy, json, math, shutil
from pathlib import Path
from mathutils import Vector

O=Path(__file__).resolve().parent; S=O.parent
T=O/'Textures'; T.mkdir(exist_ok=True)
C=S/'SVDCompletion20260923'
SOURCE=S/'SVDDragunov20260922/Textures'
PARTS={'Body':'svd','Magazine':'svd','Trigger':'svd','ChargingHandle':'svd',
       'SafetyLever':'svd','ScopeBody':'pso','ScopeMount':'pso'}
bpy.context.preferences.filepaths.save_version=0
backup=O/'Before/SVD_Complete_Editable.blend'; backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(C/'SVD_Complete_Editable.blend',backup)
bpy.ops.wm.open_mainfile(filepath=str(C/'SVD_Complete_Editable.blend'))
scene=bpy.context.scene
rig=next(o for o in scene.objects if o.type=='ARMATURE')
rig.animation_data.action=bpy.data.actions['A_SVD_idle']
rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0)
images={}
for atlas in ('svd','pso'):
    for role in ('basecolor','metallic','roughness','ao','normal'):
        image=bpy.data.images.load(str(SOURCE/('T_SVD_'+atlas+'_'+role+('.png' if role=='normal' else '.jpg'))),check_existing=True)
        image.colorspace_settings.name='sRGB' if role=='basecolor' else 'Non-Color'
        images[atlas,role]=image

# Material values are independent for coatings, steel and non-metal furniture.
FINISH={
 'Receiver':((.027,.034,.041),.84,.31,.18),
 'Magazine':((.024,.029,.036),.92,.285,.18),
 'MachinedSteel':((.064,.074,.085),.96,.235,.16),
 'Polymer':((.017,.020,.023),0.,.50,.18),
 'Rubber':((.006,.007,.008),0.,.72,.14),
 'CheekPad':((.065,.031,.016),0.,.53,.78),
 'Scope':((.080,.092,.099),.80,.325,.14),
 'Mount':((.043,.052,.060),.88,.30,.16),
}
authors={}
def author_material(atlas,kind):
    key=atlas+':'+kind
    if key in authors:return authors[key]
    base,metal,rough,source_share=FINISH[kind]
    mat=bpy.data.materials.new('AUTH_SVD_'+atlas+'_'+kind);mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    def mathnode(op,a,b=0.):
        n=nodes.new('ShaderNodeMath');n.operation=op
        for value,index in ((a,0),(b,1)):
            if hasattr(value,'node'):links.new(value,n.inputs[index])
            else:n.inputs[index].default_value=value
        return n.outputs[0]
    def mix(factor,a,b):
        n=nodes.new('ShaderNodeMixRGB');n.blend_type='MIX'
        for value,index in ((factor,0),(a,1),(b,2)):
            if hasattr(value,'node'):links.new(value,n.inputs[index])
            else:n.inputs[index].default_value=value
        return n.outputs[0]
    def tex(role):
        n=nodes.new('ShaderNodeTexImage');n.image=images[atlas,role]
        uv=nodes.get('SOURCE_UV')
        if uv is None:uv=nodes.new('ShaderNodeUVMap');uv.name='SOURCE_UV';uv.uv_map='UVMap'
        links.new(uv.outputs['UV'],n.inputs['Vector'])
        return n.outputs['Color']
    source=tex('basecolor');source_metal=tex('metallic')
    bw=nodes.new('ShaderNodeRGBToBW');links.new(source,bw.inputs[0])
    luminance=bw.outputs[0]
    # Preserve paint/lettering identified by the original non-metal mask.
    marking=mathnode('MULTIPLY',mathnode('LESS_THAN',source_metal,.15),mathnode('GREATER_THAN',luminance,.035)) if metal else 0.
    color=mix(source_share,(*base,1),source)
    color=mix(marking,color,source)
    coords=nodes.new('ShaderNodeTexCoord')
    noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=1150 if metal else 750
    noise.inputs['Detail'].default_value=2.;links.new(coords.outputs['Object'],noise.inputs['Vector'])
    # Millimetre-scale coating grain mainly affects roughness, not embossed bumps.
    rough_out=mathnode('ADD',rough,mathnode('MULTIPLY',mathnode('SUBTRACT',noise.outputs['Fac'],.5),.026 if metal else .045))
    rough_out=mathnode('ADD',rough_out,mathnode('MULTIPLY',mathnode('SUBTRACT',tex('roughness'),.5),.08 if metal else .10))
    metallic=mathnode('MULTIPLY',metal,mathnode('SUBTRACT',1.,marking)) if metal else 0.
    if atlas=='pso':
        # Retain the black eyecup/interior and painted letters independently of the shell.
        rubber=mathnode('MULTIPLY',mathnode('LESS_THAN',source_metal,.12),mathnode('LESS_THAN',luminance,.02))
        color=mix(rubber,color,(.007,.008,.009,1))
        rough_out=mix(rubber,rough_out,(.69,.69,.69,1))
        metallic=mathnode('MULTIPLY',metallic,mathnode('SUBTRACT',1.,rubber))
    # AO is a separate lighting input; it no longer darkens BaseColor twice.
    ao=mathnode('ADD',.45,mathnode('MULTIPLY',tex('ao'),.55))
    orm=nodes.new('ShaderNodeCombineColor');orm.mode='RGB'
    for socket,value in zip(orm.inputs,(ao,rough_out,metallic)):
        if hasattr(value,'node'):links.new(value,socket)
        else:socket.default_value=value
    bs=nodes.new('ShaderNodeBsdfPrincipled');links.new(color,bs.inputs['Base Color'])
    links.new(rough_out,bs.inputs['Roughness'])
    if hasattr(metallic,'node'):links.new(metallic,bs.inputs['Metallic'])
    else:bs.inputs['Metallic'].default_value=metallic
    normal=nodes.new('ShaderNodeNormalMap');normal.uv_map='UVMap';normal.inputs['Strength'].default_value=1.
    links.new(tex('normal'),normal.inputs['Color']);links.new(normal.outputs[0],bs.inputs['Normal'])
    out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs[0])
    mat['base_node']=color.node.name;mat['base_socket']=color.name;mat['orm_node']=orm.name
    mat['surface_kind']=kind;authors[key]=mat
    return mat

regions=json.loads((O/'body_regions.json').read_text())
region_material={}
for row in regions:
    lo,hi,size=row['min'],row['max'],row['size'];kind='Receiver'
    if lo[1]>.33 and size[2]>.12:kind='Rubber'
    elif lo[1]>.14 and hi[1]<.27 and lo[2]>.045 and size[1]>.09:kind='CheekPad'
    elif lo[1]>.05 and size[1]>.24 and size[2]>.12:kind='Polymer'
    elif lo[1]<-.47 and -.24<hi[1]<-.21 and size[0]>.030:kind='Polymer'
    for face in row['faces']:region_material[face]=kind

collection=bpy.data.collections.new('SVD_SURFACE_AUTHOR');scene.collection.children.link(collection)
bake_objects={};bindings={};partition_counts={}
for part,atlas in PARTS.items():
    original=bpy.data.objects['SM_SVD_'+part]
    bindings[part]=original.data.materials[0]
    obj=original.copy();obj.data=original.data.copy();obj.name='BAKE_SVD_'+part
    collection.objects.link(obj);obj.parent=None;obj.matrix_world=original.matrix_world.copy()
    for modifier in list(obj.modifiers):obj.modifiers.remove(modifier)
    obj.data.materials.clear()
    kinds=list(FINISH) if part=='Body' else ['MachinedSteel' if part in ('Trigger','ChargingHandle') else 'Magazine' if part=='Magazine' else 'Scope' if part=='ScopeBody' else 'Mount' if part=='ScopeMount' else 'Receiver']
    for kind in kinds:obj.data.materials.append(author_material(atlas,kind))
    for face in obj.data.polygons:
        kind=region_material[face.index] if part=='Body' else kinds[0]
        face.material_index=kinds.index(kind)
        partition_counts[kind]=partition_counts.get(kind,0)+1
    uvname=obj.data.uv_layers[0].name
    for mat in obj.data.materials:
        mat.node_tree.nodes['SOURCE_UV'].uv_map=uvname
        for node in mat.node_tree.nodes:
            if node.type=='NORMAL_MAP':node.uv_map=uvname
    bake_objects.setdefault(atlas,[]).append(obj)

scene.render.engine='CYCLES';scene.cycles.samples=1;scene.cycles.use_denoising=False
scene.render.bake.use_selected_to_active=False;scene.render.bake.use_clear=False;scene.render.bake.margin=16
try:
    prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
    for device in prefs.devices:device.use=device.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'
manifest={};baked={}
for atlas,objects in bake_objects.items():
    manifest[atlas]={'size':4096,'textures':{},'normal_source':str(SOURCE/('T_SVD_'+atlas+'_normal.png'))}
    for kind in ('BaseColor','ORM'):
        name='T_SVD_Surface_'+atlas+'_'+kind
        image=bpy.data.images.new(name,width=4096,height=4096,alpha=False)
        image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
        image.generated_color=(.02,.02,.02,1) if kind=='BaseColor' else (1,.5,0,1)
        for obj in objects:
            for mat in obj.data.materials:
                nodes=mat.node_tree.nodes;links=mat.node_tree.links
                target=nodes.get('BAKE_TARGET') or nodes.new('ShaderNodeTexImage');target.name='BAKE_TARGET';target.image=image;nodes.active=target
                emit=nodes.get('BAKE_EMISSION') or nodes.new('ShaderNodeEmission');emit.name='BAKE_EMISSION'
                value=nodes[mat['base_node']].outputs[mat['base_socket']] if kind=='BaseColor' else nodes[mat['orm_node']].outputs[0]
                links.new(value,emit.inputs['Color']);links.new(emit.outputs[0],next(n for n in nodes if n.type=='OUTPUT_MATERIAL').inputs['Surface'])
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.hide_set(False);obj.hide_render=False;obj.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.bake(type='EMIT')
        image.filepath_raw=str(T/(name+'.png'));image.file_format='PNG';image.save()
        manifest[atlas]['textures'][kind]=str(image.filepath_raw);baked[atlas,kind]=image
        print('SVD_SURFACE_BAKED',atlas,kind,flush=True)

for mat in authors.values():
    nodes=mat.node_tree.nodes
    mat.node_tree.links.new(next(n for n in nodes if n.type=='BSDF_PRINCIPLED').outputs[0],next(n for n in nodes if n.type=='OUTPUT_MATERIAL').inputs[0])
# Preserve the live source's one material per part and original material names.
for part,mat in bindings.items():
    atlas=PARTS[part];nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear()
    bs=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bs.outputs[0],out.inputs[0])
    uv=nodes.new('ShaderNodeUVMap');uv.uv_map=bpy.data.objects['SM_SVD_'+part].data.uv_layers[0].name
    for kind in ('BaseColor','ORM','Normal'):
        tex=nodes.new('ShaderNodeTexImage');tex.image=images[atlas,'normal'] if kind=='Normal' else baked[atlas,kind]
        links.new(uv.outputs[0],tex.inputs['Vector'])
        if kind=='BaseColor':links.new(tex.outputs['Color'],bs.inputs['Base Color'])
        elif kind=='ORM':
            sep=nodes.new('ShaderNodeSeparateColor');links.new(tex.outputs['Color'],sep.inputs[0])
            links.new(sep.outputs['Green'],bs.inputs['Roughness']);links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        else:
            normal=nodes.new('ShaderNodeNormalMap');normal.uv_map=uv.uv_map;normal.inputs['Strength'].default_value=1.
            links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],bs.inputs['Normal'])
    mat['ue_surface_atlas']=atlas
for objects in bake_objects.values():
    for obj in objects:obj.hide_render=True;obj.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_Surface_Editable.blend'))
for objects in bake_objects.values():
    for obj in objects:bpy.data.objects.remove(obj,do_unlink=True)
bpy.data.collections.remove(collection)
bpy.ops.wm.save_as_mainfile(filepath=str(C/'SVD_Complete_Editable.blend'))
(O/'textures.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(O/'authoring.json').write_text(json.dumps({'parts':PARTS,'finish_parameters':FINISH,'partition_faces':partition_counts,
    'source':'Existing corrected UV0, full structural normals, existing SVD geometry and Manny rig',
    'status':'Material authoring and texture baking only; no visual or gameplay test'},indent=2),encoding='utf-8')
print('SVD_SURFACE_AUTHORING_COMPLETE',flush=True)
