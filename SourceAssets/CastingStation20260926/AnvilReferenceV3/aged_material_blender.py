"""Editable Blender counterpart of the UE aged-iron surface; no geometry operations."""
from pathlib import Path
import bpy

def make_aged_material(mat,here):
    mat.use_nodes=True;ns,ls=mat.node_tree.nodes,mat.node_tree.links;ns.clear()
    bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs['BSDF'],out.inputs['Surface'])
    library=here.parent.parent/'BlastFurnace20260923/Authored/Textures'
    def texture(path):
        n=ns.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(path),check_existing=True)
        n.image.colorspace_settings.name='sRGB' if path.stem.endswith('BaseColor') else 'Non-Color'
        return n.outputs['Color']
    def plug(value,socket):
        if isinstance(value,(int,float,tuple)):socket.default_value=value
        else:ls.new(value,socket)
    def math(op,a,b):
        n=ns.new('ShaderNodeMath');n.operation=op;plug(a,n.inputs[0]);plug(b,n.inputs[1]);return n.outputs[0]
    def mix(f,a,b,blend='MIX'):
        n=ns.new('ShaderNodeMixRGB');n.blend_type=blend;plug(f,n.inputs[0]);plug(a,n.inputs[1]);plug(b,n.inputs[2]);return n.outputs[0]
    body={k:texture(library/('BlastFurnace_WroughtIron_'+k+'.png')) for k in ['BaseColor','Roughness','Metallic','Normal']}
    work={k:texture(here/'Textures'/('T_Anvil_Worked_'+k+'.png')) for k in ['BaseColor','ORM','Normal']}
    wear=ns.new('ShaderNodeVertexColor');wear.layer_name='AnvilWear'
    clean=ns.new('ShaderNodeMapRange');clean.interpolation_type='SMOOTHSTEP';clean.clamp=True
    plug(body['Metallic'],clean.inputs['Value']);clean.inputs['From Min'].default_value=.15;clean.inputs['From Max'].default_value=.8
    rubbed=math('MULTIPLY',wear.outputs['Color'],math('ADD',.12,math('MULTIPLY',.58,clean.outputs['Result'])))
    lum=ns.new('ShaderNodeRGBToBW');plug(body['BaseColor'],lum.inputs['Color'])
    oxide=mix(1,mix(.25,body['BaseColor'],lum.outputs[0]),(.42,.42,.42,1),'MULTIPLY')
    steel=mix(1,work['BaseColor'],(.3298,.323,.3094,1),'MULTIPLY')
    plug(mix(rubbed,oxide,steel),bs.inputs['Base Color'])
    split=ns.new('ShaderNodeSeparateColor');plug(work['ORM'],split.inputs['Color'])
    iron_rough=math('ADD',.72,math('MULTIPLY',.2,body['Roughness']))
    work_rough=math('ADD',.60,math('MULTIPLY',.2,split.outputs['Green']))
    plug(mix(rubbed,iron_rough,work_rough),bs.inputs['Roughness'])
    iron_metal=math('ADD',.04,math('MULTIPLY',.62,body['Metallic']))
    plug(mix(rubbed,iron_metal,math('MULTIPLY',.88,split.outputs['Blue'])),bs.inputs['Metallic'])
    plug(math('ADD',.28,math('MULTIPLY',.22,rubbed)),bs.inputs['Specular IOR Level'])
    normals=[]
    for field,strength in [(body['Normal'],.65),(work['Normal'],1)]:
        channels=ns.new('ShaderNodeSeparateColor');plug(field,channels.inputs[0])
        rgb=ns.new('ShaderNodeCombineColor');plug(channels.outputs['Red'],rgb.inputs['Red'])
        plug(math('SUBTRACT',1,channels.outputs['Green']),rgb.inputs['Green']);plug(channels.outputs['Blue'],rgb.inputs['Blue'])
        normal=ns.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=strength;plug(rgb.outputs[0],normal.inputs['Color']);normals.append(normal.outputs['Normal'])
    unit=ns.new('ShaderNodeVectorMath');unit.operation='NORMALIZE';plug(mix(rubbed,*normals),unit.inputs[0]);plug(unit.outputs[0],bs.inputs['Normal'])
    mat['SurfaceRevision']='AgedIron4'
    return mat

if __name__=='__main__':
    here=Path(__file__).parent
    path=here/'Authored/CastingStation_AnvilReference_Source.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.preferences.filepaths.save_version=0
    make_aged_material(bpy.data.materials['AnvilSteel'],here)
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    print('ANVIL_AGED_SOURCE_MATERIAL_SAVED; geometry and FBX exports untouched',flush=True)
