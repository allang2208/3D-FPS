"""Material-only editable revision of V38 Ice/Magma/Storm and V37 Jade."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parent
P=json.loads((ROOT/'parameters.json').read_text(encoding='utf-8'))
SOURCE=ROOT.parent/'ElementHeadsV38/Staff_ElementalCrystals_V38.blend'
JADE=ROOT.parent/'ElementHeadsV37/Staff_ElementalCrystals_V37.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(JADE),link=False) as (src,dst):
    dst.collections=['jade_spirit_crystal_Editable']
for collection in dst.collections:
    bpy.context.scene.collection.children.link(collection)
authored=[]
for kind,config in P['heads'].items():
    version=config['version']
    old=bpy.data.materials[f'M_StaffCraft_{kind}_V{version}']
    mat=old.copy();mat.name='M_ElementPolish_'+kind+'_V42'
    mat['ue_material_recipe']=str(ROOT/'ue_material.py')
    nodes,links=mat.node_tree.nodes,mat.node_tree.links
    bsdf=next(node for node in nodes if node.type=='BSDF_PRINCIPLED')
    for socket in ('Roughness','Normal'):
        for link in list(bsdf.inputs[socket].links):
            links.remove(link)

    def image_node(channel):
        name=f'T_StaffCraft_{kind}_{channel}_V{version}'
        image=bpy.data.images.get(name)
        if image is None:
            image=bpy.data.images.load(str(ROOT.parent/f'ElementHeadsV{version}/Export/Textures'/(name+'.png')),check_existing=True)
        image.colorspace_settings.name='Non-Color'
        image.pack()
        node=nodes.new('ShaderNodeTexImage');node.image=image
        return node

    if kind in ('Magma','Jade'):
        packed=image_node('RGE')
        split=nodes.new('ShaderNodeSeparateColor')
        links.new(packed.outputs['Color'],split.inputs['Color'])
        if kind=='Magma':
            heat=nodes.new('ShaderNodeMath');heat.operation='MULTIPLY';heat.use_clamp=True
            links.new(split.outputs['Blue'],heat.inputs[0]);heat.inputs[1].default_value=config['heat_mask_gain']
            rough=nodes.new('ShaderNodeMixRGB');rough.blend_type='MIX'
            rough.inputs[1].default_value=(config['crust_roughness'],)*3+(1.,)
            rough.inputs[2].default_value=(config['molten_roughness'],)*3+(1.,)
            links.new(heat.outputs[0],rough.inputs[0])
            normal=image_node('Normal')
            normal_map=nodes.new('ShaderNodeNormalMap');normal_map.inputs['Strength'].default_value=config['normal_strength']
            links.new(normal.outputs['Color'],normal_map.inputs['Color'])
            links.new(normal_map.outputs[0],bsdf.inputs['Normal'])
        else:
            rough=nodes.new('ShaderNodeMapRange');rough.clamp=True
            links.new(split.outputs['Red'],rough.inputs['Value'])
            for key,value in {'From Min':.125,'From Max':.245,'To Min':config['roughness_min'],
                              'To Max':config['roughness_max']}.items():
                rough.inputs[key].default_value=value
        links.new(rough.outputs[0],bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value=config['roughness']
    for obj in bpy.data.objects:
        if obj.type=='MESH':
            for slot in obj.material_slots:
                if slot.material==old:
                    slot.material=mat
    authored.append(dict(kind=kind,material=mat.name,baseline=old.name))
bpy.context.scene['revision']=42
bpy.context.scene['design']='clean ice facets, restrained lava rock relief, polished jade, clean storm shell; original geometry and inner lightning'
note=bpy.data.texts.new('ElementPolishV42_README')
note.write('Material-only revision. UE source: ue_material.py.\n'
           'UE retains the existing emissive and storm WPO graphs exactly.\n'
           'Blender keeps previous editable lightning geometry; UE HLSL is authoritative for animation.\n'
           'No geometry export, new texture baking, preview or gameplay test.\n'+json.dumps(P,indent=2))
target=ROOT/'Staff_ElementPolish_V42.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(target))
(ROOT/'author-receipt.json').write_text(json.dumps(dict(complete=True,blend=str(target),
    sources=[str(SOURCE),str(JADE)],materials=authored,geometry_changed=False,
    new_textures=0,runtime_tested=False,rendered=False),indent=2),encoding='utf-8')
print('STAFF_ELEMENT_POLISH_V42_AUTHORED heads=4 geometry_changed=false rendered=false',flush=True)
