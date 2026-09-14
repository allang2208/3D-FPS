"""Mirror-polished 715 surface authoring; detail normals separate from broad shape."""
from pathlib import Path
import bpy

FINISH = {
    'Frame': dict(base=(.62, .64, .66), rough=.045, detail_strength=.45),
    'Cylinder': dict(base=(.65, .665, .68), rough=.035, detail_strength=0.),
    'Steel': dict(base=(.58, .60, .62), rough=.060, detail_strength=.45),
}

def author_material(group, engraved=False):
    cfg=FINISH[group]
    m=bpy.data.materials.new('AUTH_DW715_Mirror_'+group+('_Engraving' if engraved else ''))
    m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    out=n.new('ShaderNodeOutputMaterial');bs=n.new('ShaderNodeBsdfPrincipled');l.new(bs.outputs[0],out.inputs['Surface'])
    def op(kind,a,b=0):
        node=n.new('ShaderNodeMath');node.operation=kind
        for i,v in enumerate((a,b)):
            if isinstance(v,(int,float)):node.inputs[i].default_value=v
            else:l.new(v,node.inputs[i])
        return node.outputs[0]
    def vec(kind,a,b):
        node=n.new('ShaderNodeVectorMath');node.operation=kind
        for i,v in enumerate((a,b)):
            if isinstance(v,(tuple,list)):node.inputs[i].default_value=v
            else:l.new(v,node.inputs[i])
        return node.outputs[0]
    color=n.new('ShaderNodeRGB');color.outputs[0].default_value=(*cfg['base'],1);base=color.outputs[0]
    geometry=n.new('ShaderNodeNewGeometry')
    convex=op('MINIMUM',op('MAXIMUM',op('MULTIPLY',op('SUBTRACT',geometry.outputs['Pointiness'],.505),18),0),1)
    cavity=op('MINIMUM',op('MAXIMUM',op('MULTIPLY',op('SUBTRACT',.495,geometry.outputs['Pointiness']),12),0),1)
    rough=op('ADD',op('SUBTRACT',cfg['rough'],op('MULTIPLY',convex,.008)),op('MULTIPLY',cavity,.08))

    if engraved:
        source=bpy.data.images.load(str(Path(__file__).parent.parent/'DanWesson71520260913/Textures/T_DW715_Normal.png'),check_existing=True)
        source.colorspace_settings.name='Non-Color'
        uv=n.new('ShaderNodeUVMap');uv.uv_map='SourceUV'
        # Remove the source's broad tangent-normal gradients before rebaking.
        # The 3x3 separable Gaussian spans 12 source texels in either direction.
        # New high-poly bevels are baked independently at full strength below.
        radius_x=12/max(1,source.size[0]);radius_y=12/max(1,source.size[1])
        samples={};average=None
        for x,y,weight in [(0,0,4),(-1,0,2),(1,0,2),(0,-1,2),(0,1,2),(-1,-1,1),(-1,1,1),(1,-1,1),(1,1,1)]:
            tex=n.new('ShaderNodeTexImage');tex.image=source;tex.interpolation='Linear'
            coord=vec('ADD',uv.outputs[0],(x*radius_x,y*radius_y,0))
            l.new(coord,tex.inputs['Vector']);samples[x,y]=tex.outputs['Color']
            weighted=vec('MULTIPLY',tex.outputs['Color'],(weight/16,)*3)
            average=weighted if average is None else vec('ADD',average,weighted)
        difference=vec('SUBTRACT',samples[0,0],average)
        split=n.new('ShaderNodeSeparateXYZ');l.new(difference,split.inputs[0])
        dx=op('MULTIPLY',split.outputs['X'],2*cfg['detail_strength'])
        dy=op('MULTIPLY',split.outputs['Y'],2*cfg['detail_strength'])
        square=op('ADD',op('MULTIPLY',dx,dx),op('MULTIPLY',dy,dy))
        dz=op('SQRT',op('MAXIMUM',op('SUBTRACT',1,square),.01))
        encoded=n.new('ShaderNodeCombineXYZ')
        for i,value in enumerate((dx,dy,dz)):l.new(op('ADD',.5,op('MULTIPLY',value,.5)),encoded.inputs[i])
        normal=n.new('ShaderNodeNormalMap');normal.uv_map='SourceUV';normal.inputs['Strength'].default_value=1
        l.new(encoded.outputs[0],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
        detail=op('MINIMUM',op('MAXIMUM',op('MULTIPLY',op('SUBTRACT',op('SQRT',square),.012),5),0),1)
        # Etched marks are slightly less polished than the uninterrupted panels.
        rough=op('ADD',rough,op('MULTIPLY',detail,.08))
        tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1
        l.new(base,tint.inputs[1]);l.new(op('SUBTRACT',1,op('MULTIPLY',detail,.14)),tint.inputs[2]);base=tint.outputs[0]
    l.new(base,bs.inputs['Base Color']);l.new(rough,bs.inputs['Roughness']);bs.inputs['Metallic'].default_value=1
    # No brushed bump, broad tint noise, clear-coat layer, or baked old shadows.
    ao=n.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=.0018;ao.samples=4;ao.only_local=True
    orm=n.new('ShaderNodeCombineColor');l.new(op('ADD',.4,op('MULTIPLY',ao.outputs['AO'],.6)),orm.inputs[0]);l.new(rough,orm.inputs[1]);orm.inputs[2].default_value=1
    m['base_node']=base.node.name;m['base_socket']=base.name;m['orm_node']=orm.name
    m['finish']='Mirror polished; filtered source engravings; full high-poly bevels; no micro bump'
    return m
