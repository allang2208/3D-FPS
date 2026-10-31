"""Blender PBR preview: image textures are connected, not merely generated on disk.
DirectX PNG normals are flipped to OpenGL here; UE uses the original DirectX PNG.
"""
from pathlib import Path
import bpy

def material(role, spec, root):
    name='KP_'+role
    texture={'Enamel':'PetrolEnamel','Stone':'HonedStone','Tile':'GlazedTile','Steel':'BrushedSteel',
             'Wood':'SmokedWalnut','Linen':'LinenTowel','Porcelain':'Porcelain'}[role]
    mat=bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes=True
    mat.use_nodes=True
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    nodes.clear()
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.location=(660,80)
    out=nodes.new('ShaderNodeOutputMaterial');out.location=(940,80)
    links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    coord=nodes.new('ShaderNodeTexCoord');coord.location=(-840,0)
    scale=nodes.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.location=(-650,0)
    scale.inputs[3].default_value=1/spec['period']
    links.new(coord.outputs['UV'],scale.inputs[0])
    def image(suffix,color=False):
        path=Path(root)/'TexturesV2'/f'T_KP_{texture}_{suffix}.png'
        im=bpy.data.images.load(str(path),check_existing=True)
        im.colorspace_settings.name='sRGB' if color else 'Non-Color'
        node=nodes.new('ShaderNodeTexImage');node.image=im;node.extension='REPEAT';node.location=(-420,{'BC':300,'N':-80,'ORM':-400}[suffix])
        links.new(scale.outputs['Vector'],node.inputs['Vector'])
        return node
    bc=image('BC',True)
    tint=nodes.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1;tint.location=(120,280)
    tint.inputs[2].default_value=(*spec['tint'],1)
    links.new(bc.outputs['Color'],tint.inputs[1]);links.new(tint.outputs[0],bsdf.inputs['Base Color'])
    n=image('N');sep=nodes.new('ShaderNodeSeparateColor');sep.location=(-180,-100);links.new(n.outputs['Color'],sep.inputs[0])
    inv=nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;links.new(sep.outputs['Green'],inv.inputs[1]);inv.location=(-20,-230)
    combine=nodes.new('ShaderNodeCombineColor');combine.location=(140,-140)
    links.new(sep.outputs['Red'],combine.inputs['Red']);links.new(inv.outputs[0],combine.inputs['Green']);links.new(sep.outputs['Blue'],combine.inputs['Blue'])
    normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=spec['strength'];normal.location=(360,-80)
    links.new(combine.outputs[0],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
    orm=image('ORM');channels=nodes.new('ShaderNodeSeparateColor');channels.location=(-80,-480);links.new(orm.outputs['Color'],channels.inputs[0])
    rough=nodes.new('ShaderNodeMapRange');rough.location=(130,-420)
    rough.inputs['To Min'].default_value=max(.05,spec['roughness']-.055);rough.inputs['To Max'].default_value=min(1,spec['roughness']+.055)
    links.new(channels.outputs['Green'],rough.inputs[0]);links.new(rough.outputs[0],bsdf.inputs['Roughness'])
    links.new(channels.outputs['Blue'],bsdf.inputs['Metallic'])
    mat['NormalSource']=f'T_KP_{texture}_N.png (DirectX); preview flips G'
    mat['TexturePeriod_m']=spec['period']
    return mat

def simple(name,color,rough=.45,metal=0,emission=0):
    mat=bpy.data.materials.get('KP_'+name) or bpy.data.materials.new('KP_'+name)
    mat.use_nodes=True;bsdf=mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value=(*color,1);bsdf.inputs['Roughness'].default_value=rough;bsdf.inputs['Metallic'].default_value=metal
    if emission:
        bsdf.inputs['Emission Color'].default_value=(*color,1);bsdf.inputs['Emission Strength'].default_value=emission
    if name=='Glass':
        bsdf.inputs['Transmission Weight'].default_value=.92;bsdf.inputs['IOR'].default_value=1.46
    return mat

def all_materials(root,pbr):
    mats={role:material(role,spec,root) for role,spec in pbr.items()}
    for role,color,rough,metal,emission in [
        ('Graphite',(.022,.024,.028),.40,.65,0),('Rubber',(.012,.013,.015),.73,0,0),
        ('Inside',(.065,.067,.071),.67,.05,0),('Copper',(.25,.105,.046),.32,.85,0),
        ('Paper',(.56,.54,.43),.85,0,0),('Ink',(.016,.026,.030),.63,0,0),
        ('Leaf',(.047,.14,.065),.5,0,0),('Soil',(.025,.019,.012),.98,0,0),
        ('Glass',(.70,.73,.76),.14,0,0),('Coffee',(.018,.008,.003),.2,0,0),
        ('Warm',(.95,.72,.39),.32,0,3),('Cyan',(.028,.34,.39),.3,0,1.6),
        ('Red',(.27,.025,.017),.55,0,0),('Ochre',(.38,.18,.043),.51,0,0),
        ('Sage',(.12,.18,.12),.56,0,0),('Food',(.54,.33,.12),.6,0,0),
    ]: mats[role]=simple(role,color,rough,metal,emission)
    return mats
