"""Mirror UE's regional finish in the editable Blender materials."""
def apply_regions(gun):
    for mat in gun.data.materials:
        if mat.get('ASH12SurfaceRegions'):
            continue
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        bsdf=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
        attr=nodes.new('ShaderNodeAttribute');attr.attribute_name='SurfaceRegions'
        split=nodes.new('ShaderNodeSeparateColor');links.new(attr.outputs['Color'],split.inputs[0])
        def mix(source, value, weight):
            n=nodes.new('ShaderNodeMixRGB');n.blend_type='MIX'
            links.new(weight,n.inputs[0]);links.new(source,n.inputs[1]);n.inputs[2].default_value=(*value,1)
            return n.outputs[0]
        regions={
            'Base Color':[(.025,.026,.028),(.22,.24,.26),(.010,.011,.012)],
            'Roughness':[(.62,)*3,(.30,)*3,(.87,)*3],
            'Metallic':[(.03,)*3,(.90,)*3,(.05,)*3]}
        for name,values in regions.items():
            pin=bsdf.inputs[name]
            if pin.is_linked:source=pin.links[0].from_socket
            else:
                n=nodes.new('ShaderNodeRGB')
                n.outputs[0].default_value=pin.default_value if name=='Base Color' else (pin.default_value,)*3+(1,)
                source=n.outputs[0]
            for index,value in enumerate(values):source=mix(source,value,split.outputs[index])
            links.new(source,pin)
        mat['ASH12SurfaceRegions']=1
