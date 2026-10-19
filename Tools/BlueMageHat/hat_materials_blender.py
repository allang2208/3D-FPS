import bpy
def make_materials(root):
    def make(name,kind='fabric'):
        m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;p=n['Principled BSDF']
        if kind in ('thread','silver','gem'):
            c,r,metal={'thread':((.57,.55,.49),.60,.25),'silver':((.48,.46,.40),.34,1),'gem':((.012,.08,.45),.12,.45)}[kind];p.inputs['Base Color'].default_value=(*c,1);p.inputs['Roughness'].default_value=r;p.inputs['Metallic'].default_value=metal;return m
        embroidery=kind in ('band','border');family='BlueMageEmbroidery' if embroidery else 'BlueMageFabric';uv=n.new('ShaderNodeTexCoord');scale=n.new('ShaderNodeVectorMath');scale.operation='SCALE';scale.inputs[3].default_value=1 if embroidery else 6.25;l.new(uv.outputs['UV'],scale.inputs[0]);nodes={}
        for channel in ('BaseColor','Normal','ORM'):
            image=bpy.data.images.load(str(root/'Textures'/('T_'+family+'_'+channel+'.png')),check_existing=True)
            if channel!='BaseColor':image.colorspace_settings.name='Non-Color'
            t=n.new('ShaderNodeTexImage');t.image=image;l.new(scale.outputs[0],t.inputs['Vector']);nodes[channel]=t
        split=n.new('ShaderNodeSeparateColor');l.new(nodes['ORM'].outputs['Color'],split.inputs[0]);l.new(split.outputs['Green'],p.inputs['Roughness']);l.new(split.outputs['Blue'],p.inputs['Metallic']);normal=n.new('ShaderNodeNormalMap');l.new(nodes['Normal'].outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],p.inputs['Normal']);color=nodes['BaseColor'].outputs['Color']
        if kind=='lining':
            mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(.4,.43,.52,1);l.new(color,mul.inputs[1]);color=mul.outputs[0]
        if kind=='band':
            mul=n.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1;mul.inputs[2].default_value=(.22,.27,.34,1);l.new(color,mul.inputs[1]);mix=n.new('ShaderNodeMixRGB');l.new(split.outputs['Blue'],mix.inputs[0]);l.new(mul.outputs[0],mix.inputs[1]);l.new(color,mix.inputs[2]);color=mix.outputs[0]
        l.new(color,p.inputs['Base Color']);return m
    return [make('Fabric'),make('Lining','lining'),make('BandEmbroidery','band'),make('BorderEmbroidery','border'),make('Thread','thread'),make('Silver','silver'),make('Gem','gem')]
