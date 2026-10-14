"""Attach packed PBR authoring materials to the editable source; does not render."""
import bpy
from pathlib import Path

def attach(root):
    style={'Yellow':(0,4,(.80,.57,.025,1)), 'Steel':(1,7,(1,1,1,1)),
        'Rubber':(2,16,(.15,.16,.17,1)), 'Cotton':(3,16,(.85,.83,.71,1)),
        'Teal':(0,5,(.036,.15,.119,1)), 'Board':(3,3,(.47,.32,.15,1)),
        'Paper':(3,4,(.94,.90,.79,1)), 'Forms':(-1,1,(1,1,1,1)), 'Caution':(-2,7,(1,1,1,1))}
    images={}
    for p in (Path(root)/'Authored/Textures').glob('*.png'):
        img=bpy.data.images.load(str(p),check_existing=True)
        if not p.stem.endswith('_BC'):img.colorspace_settings.name='Non-Color'
        img.pack();images[p.stem.removeprefix('T_IncidentDetail_')]=img
    for role,(tile,scale,tint) in style.items():
        mat=bpy.data.materials.get('ID2_'+role)
        if not mat:continue
        mat.use_nodes=True;n=mat.node_tree.nodes;n.clear();w=mat.node_tree.links
        out=n.new('ShaderNodeOutputMaterial');p=n.new('ShaderNodeBsdfPrincipled');w.new(p.outputs['BSDF'],out.inputs['Surface'])
        uv=n.new('ShaderNodeTexCoord');coord=uv.outputs['UV']
        if tile!=-1:
            mul=n.new('ShaderNodeVectorMath');mul.operation='SCALE';mul.inputs['Scale'].default_value=scale;w.new(coord,mul.inputs[0])
            frac=n.new('ShaderNodeVectorMath');frac.operation='FRACTION';w.new(mul.outputs['Vector'],frac.inputs[0])
            m=n.new('ShaderNodeVectorMath');m.operation='SCALE';m.inputs['Scale'].default_value=.496;w.new(frac.outputs['Vector'],m.inputs[0])
            plus=n.new('ShaderNodeVectorMath');plus.operation='ADD';plus.inputs[1].default_value=((max(0,tile)%2)*.5+.002,(1-max(0,tile)//2)*.5+.002,0)
            w.new(m.outputs['Vector'],plus.inputs[0]);coord=plus.outputs['Vector']
        source='Forms' if tile==-1 else 'Surfaces'
        def sample(key,c):
            t=n.new('ShaderNodeTexImage');t.image=images[key];t.interpolation='Linear';t.extension='EXTEND';w.new(c,t.inputs['Vector']);return t
        color=sample('Caution_BC' if tile==-2 else source+'_BC',uv.outputs['UV'] if tile==-2 else coord)
        masks=sample(source+'_ORM',coord);normal=sample(source+'_NormalDX',coord)
        mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=tint;w.new(color.outputs['Color'],mul.inputs[1])
        wear=n.new('ShaderNodeVertexColor');wear.layer_name='Wear';channels=n.new('ShaderNodeSeparateColor');w.new(wear.outputs['Color'],channels.inputs[0])
        strength=n.new('ShaderNodeMath');strength.operation='MULTIPLY';strength.inputs[1].default_value=.38;w.new(channels.outputs['Red'],strength.inputs[0])
        mix=n.new('ShaderNodeMixRGB');w.new(strength.outputs[0],mix.inputs[0]);w.new(mul.outputs[0],mix.inputs[1]);mix.inputs[2].default_value=(.034,.026,.016,1);w.new(mix.outputs[0],p.inputs['Base Color'])
        channels2=n.new('ShaderNodeSeparateColor');w.new(masks.outputs['Color'],channels2.inputs[0]);w.new(channels2.outputs['Green'],p.inputs['Roughness']);w.new(channels2.outputs['Blue'],p.inputs['Metallic'])
        # Convert DirectX Y to Blender's OpenGL tangent normal convention.
        sep=n.new('ShaderNodeSeparateColor');w.new(normal.outputs['Color'],sep.inputs[0]);inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1;w.new(sep.outputs['Green'],inv.inputs[1])
        combine=n.new('ShaderNodeCombineColor');w.new(sep.outputs['Red'],combine.inputs['Red']);w.new(inv.outputs[0],combine.inputs['Green']);w.new(sep.outputs['Blue'],combine.inputs['Blue'])
        normalnode=n.new('ShaderNodeNormalMap');w.new(combine.outputs[0],normalnode.inputs['Color']);w.new(normalnode.outputs[0],p.inputs['Normal'])
