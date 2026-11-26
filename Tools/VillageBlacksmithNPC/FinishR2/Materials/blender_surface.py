"""Apply the cloth response and the rest-position apron patina to the actual Blender outfit."""
from pathlib import Path
import json
import numpy as np
import bpy

def apply(outfit,texture_dir):
    texture_dir=Path(texture_dir)
    settings=json.loads((texture_dir.parent/'material_settings.json').read_text())
    attribute_name='Smith garment rest position (m)'
    rest=outfit.data.attributes.get(attribute_name) or outfit.data.attributes.new(attribute_name,'FLOAT_VECTOR','POINT')
    coords=np.empty(len(outfit.data.vertices)*3,np.float32)
    outfit.data.vertices.foreach_get('co',coords)
    rest.data.foreach_set('vector',coords)
    for mat in outfit.data.materials:
        if not mat or not mat.use_nodes:continue
        slot=mat.name.split('.')[0].split('M_Smith_')[-1]
        if slot not in settings['specular']:continue
        n=mat.node_tree.nodes;l=mat.node_tree.links
        sh=next(x for x in n if x.type=='BSDF_PRINCIPLED')
        sh.inputs['Specular IOR Level'].default_value=settings['specular'][slot]
        if slot in ('Linen','Twill'):
            sh.inputs['Sheen Weight'].default_value=.22
            sh.inputs['Sheen Roughness'].default_value=.79
        if slot!='Apron':continue
        base=sh.inputs['Base Color'].links[0].from_socket
        rough=sh.inputs['Roughness'].links[0].from_socket
        def attach(src,dst):
            if isinstance(src,(float,int,tuple)):dst.default_value=src
            else:l.new(src,dst)
        def math_node(op,x,y=0):
            node=n.new('ShaderNodeMath');node.operation=op
            attach(x,node.inputs[0]);attach(y,node.inputs[1]);return node.outputs[0]
        def vector_node(op,x,y):
            node=n.new('ShaderNodeVectorMath');node.operation=op
            attach(x,node.inputs[0]);attach(y,node.inputs['Scale'] if op=='SCALE' else node.inputs[1]);return node.outputs[0]
        bind=n.new('ShaderNodeAttribute');bind.attribute_name=attribute_name
        separate=n.new('ShaderNodeSeparateXYZ');l.new(bind.outputs['Vector'],separate.inputs[0])
        u=math_node('ADD',math_node('MULTIPLY',separate.outputs['X'],100/37),.5)
        # Blender texture coordinates use the lower left as their origin.
        v=math_node('DIVIDE',math_node('SUBTRACT',math_node('MULTIPLY',separate.outputs['Z'],100),55.2),81.)
        vec=n.new('ShaderNodeCombineXYZ');attach(u,vec.inputs['X']);attach(v,vec.inputs['Y'])
        contact=n.new('ShaderNodeTexImage');contact.image=bpy.data.images.load(str(texture_dir/'T_Smith_Apron_Contact.png'),check_existing=True)
        contact.image.colorspace_settings.name='Non-Color';contact.extension='EXTEND';l.new(vec.outputs[0],contact.inputs[0])
        split=n.new('ShaderNodeSeparateColor');l.new(contact.outputs['Color'],split.inputs[0])
        wear,oil,soot=split.outputs[0:3]
        bc=vector_node('ADD',base,vector_node('SCALE',(.086,.045,.017),wear))
        shade=math_node('SUBTRACT',math_node('SUBTRACT',1.,math_node('MULTIPLY',oil,.39)),math_node('MULTIPLY',soot,.35))
        attach(vector_node('SCALE',bc,shade),sh.inputs['Base Color'])
        r=math_node('ADD',rough,math_node('MULTIPLY',wear,.09))
        r=math_node('SUBTRACT',r,math_node('MULTIPLY',oil,.24))
        attach(math_node('ADD',r,math_node('MULTIPLY',soot,.14)),sh.inputs['Roughness'])

