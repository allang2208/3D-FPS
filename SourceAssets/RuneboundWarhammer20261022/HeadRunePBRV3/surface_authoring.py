"""Production-only original-rune transfer and physically scaled metal detail.
No preview rendering. Rune masks are baked from the original head's geometry
and UVs onto the actual replacement surface, never drawn on floating cards.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Vector,Matrix
ROOT=Path('D:/FPS3D/FPSGAME')
FAMILY=ROOT/'SourceAssets/RuneboundWarhammer20261022'

def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.hide_render=False
    obj.select_set(True);bpy.context.view_layer.objects.active=obj

def configure_bake():
    s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=32
    s.render.bake.margin=16;s.render.threads_mode='FIXED';s.render.threads=12
    try:
        p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='CUDA';p.get_devices()
        if any(d.type=='CUDA' for d in p.devices):
            for d in p.devices:d.use=d.type=='CUDA'
            s.cycles.device='GPU'
    except Exception:pass

def transfer_runes(target,out_path,uv_index=0):
    configure_bake();scene=bpy.context.scene
    # Append an independent source, preserving the factory model and its UVs.
    with bpy.data.libraries.load(str(FAMILY/'ModulesV1/RuneboundWarhammer_Modular_Editable.blend'),link=False) as (src,dst):
        dst.objects=['SM_RuneboundWarhammer_hammer_heads_factory']
    donor=dst.objects[0];bpy.context.scene.collection.objects.link(donor)
    donor.data=donor.data.copy();donor.hide_render=False;donor.hide_set(False)
    bpy.context.view_layer.update()
    source=[donor.matrix_world@v.co for v in donor.data.vertices]
    dest=[target.matrix_world@v.co for v in target.data.vertices]
    lo=[min(p[i] for p in source) for i in range(3)];hi=[max(p[i] for p in source) for i in range(3)]
    tl=[min(p[i] for p in dest) for i in range(3)];th=[max(p[i] for p in dest) for i in range(3)]
    # This temporary projection donor alone is fitted to each replacement.
    # No delivered geometry, interface or grip is rescaled.
    donor.matrix_world=Matrix.Identity(4)
    for v,p in zip(donor.data.vertices,source):
        v.co=Vector([tl[i]+(p[i]-lo[i])*(th[i]-tl[i])/max(hi[i]-lo[i],1e-6) for i in range(3)])
    mat=bpy.data.materials.new('AUTHOR_OriginalHeadRuneProjection');mat.use_nodes=True
    nt=mat.node_tree;nt.nodes.clear()
    tex=nt.nodes.new('ShaderNodeTexImage')
    tex.image=bpy.data.images.load(str(FAMILY/'PassiveV1/Export/T_RuneboundNativeRuneMask.png'),check_existing=True)
    tex.image.colorspace_settings.name='Non-Color';tex.interpolation='Linear'
    emit=nt.nodes.new('ShaderNodeEmission');nt.links.new(tex.outputs['Color'],emit.inputs['Color'])
    output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(emit.outputs[0],output.inputs['Surface'])
    donor.data.materials.clear();donor.data.materials.append(mat)
    for f in donor.data.polygons:f.material_index=0
    target.data.uv_layers.active_index=uv_index
    for uv in target.data.uv_layers:uv.active_render=uv==target.data.uv_layers[uv_index]
    image=bpy.data.images.new(out_path.stem,width=2048,height=2048,alpha=False)
    image.colorspace_settings.name='Non-Color'
    targets=[]
    for material in target.data.materials:
        material.use_nodes=True;n=material.node_tree.nodes.new('ShaderNodeTexImage');n.image=image
        material.node_tree.nodes.active=n;targets.append((material.node_tree,n))
    activate(target);donor.select_set(True)
    scene.render.bake.use_selected_to_active=True;scene.render.bake.use_clear=True
    scene.render.bake.cage_extrusion=.085;scene.render.bake.max_ray_distance=.22
    bpy.context.view_layer.update()
    bpy.ops.object.bake(type='EMIT')
    out_path.parent.mkdir(parents=True,exist_ok=True)
    image.filepath_raw=str(out_path);image.file_format='PNG';image.save();image.pack()
    for tree,n in targets:tree.nodes.remove(n)
    bpy.data.objects.remove(donor,do_unlink=True)
    scene.render.bake.use_selected_to_active=False;scene.render.bake.cage_extrusion=0.
    target.data.uv_layers.active_index=0
    for i,uv in enumerate(target.data.uv_layers):uv.active_render=i==0
    activate(target)
    print('NATIVE_RUNE_TRANSFER_SAVED '+str(out_path),flush=True)
    return image

def refine_metal(material):
    nt=material.node_tree;p=nt.nodes.get('Principled BSDF')
    if not p:return
    tag=material.name.lower();bronze='brass' in tag or 'bronze' in tag;silver='silver' in tag
    coord=nt.nodes.new('ShaderNodeTexCoord')
    stretch=nt.nodes.new('ShaderNodeVectorMath');stretch.operation='MULTIPLY'
    stretch.inputs[1].default_value=(2300,115,820) if bronze else (130,3200,650)
    nt.links.new(coord.outputs['Object'],stretch.inputs[0])
    grain=nt.nodes.new('ShaderNodeTexNoise');grain.name='Directional machining at physical millimetre scale'
    grain.inputs['Scale'].default_value=1.;grain.inputs['Detail'].default_value=2.
    nt.links.new(stretch.outputs[0],grain.inputs['Vector'])
    bump=nt.nodes.new('ShaderNodeBump');bump.name='Subtle hand finished hairlines'
    bump.inputs['Strength'].default_value=.23;bump.inputs['Distance'].default_value=.000018 if bronze else .000012
    nt.links.new(grain.outputs['Fac'],bump.inputs['Height'])
    if p.inputs['Normal'].is_linked:nt.links.new(p.inputs['Normal'].links[0].from_socket,bump.inputs['Normal'])
    nt.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    pits=nt.nodes.new('ShaderNodeTexNoise');pits.name='Localized forge pores and aged alloy relief'
    pits.inputs['Scale'].default_value=740 if bronze else 930;pits.inputs['Detail'].default_value=3.
    nt.links.new(coord.outputs['Object'],pits.inputs['Vector'])
    ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.37;ramp.color_ramp.elements[1].position=.59
    nt.links.new(pits.outputs['Fac'],ramp.inputs[0])
    pore=nt.nodes.new('ShaderNodeBump');pore.name='Forging pores 35 micrometres';pore.invert=True
    pore.inputs['Strength'].default_value=.18;pore.inputs['Distance'].default_value=.000035
    nt.links.new(ramp.outputs[0],pore.inputs['Height']);nt.links.new(bump.outputs[0],pore.inputs['Normal'])
    nt.links.new(pore.outputs[0],p.inputs['Normal'])
    rough=nt.nodes.new('ShaderNodeMapRange');rough.name='Machined sheen variation'
    rough.inputs['To Min'].default_value=.21 if silver else .27 if bronze else .32
    rough.inputs['To Max'].default_value=.34 if silver else .47 if bronze else .51
    nt.links.new(grain.outputs['Fac'],rough.inputs['Value']);nt.links.new(rough.outputs[0],p.inputs['Roughness'])
    material['detail_revision']='HeadRunePBRV3: machining + forge pores + native incisions'

def engrave_native(material,image):
    nt=material.node_tree;p=nt.nodes.get('Principled BSDF')
    if not p:return
    mask=nt.nodes.new('ShaderNodeTexImage');mask.name='Original factory rune transferred to this head';mask.image=image
    uv=nt.nodes.new('ShaderNodeUVMap');uv.uv_map='UVMap';nt.links.new(uv.outputs[0],mask.inputs['Vector'])
    bump=nt.nodes.new('ShaderNodeBump');bump.name='Native rune incisions 0.16 mm';bump.invert=True
    bump.inputs['Strength'].default_value=.5;bump.inputs['Distance'].default_value=.00016
    nt.links.new(mask.outputs['Color'],bump.inputs['Height'])
    if p.inputs['Normal'].is_linked:nt.links.new(p.inputs['Normal'].links[0].from_socket,bump.inputs['Normal'])
    nt.links.new(bump.outputs[0],p.inputs['Normal'])
    tint=nt.nodes.new('ShaderNodeMixRGB');tint.name='Dark blue native inlay at rest'
    tint.inputs[2].default_value=(.025,.07,.105,1)
    if p.inputs['Base Color'].is_linked:nt.links.new(p.inputs['Base Color'].links[0].from_socket,tint.inputs[1])
    else:tint.inputs[1].default_value=p.inputs['Base Color'].default_value
    nt.links.new(mask.outputs['Color'],tint.inputs[0]);nt.links.new(tint.outputs[0],p.inputs['Base Color'])
