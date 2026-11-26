"""Attach retained physical height fields to the editable baking source."""
from pathlib import Path
import json
import bpy,numpy as np
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ChapelNun20261115/BootFinishR8'
bpy.ops.wm.open_mainfile(filepath=str(R/'NunBoots_R8.blend'))
game=bpy.data.objects['GAME_NunBoots_R8'];high=bpy.data.objects['HIGH_BAKE_ONLY_NunBoots_R8']
for index,mat in enumerate(game.data.materials):
    mat.use_nodes=True;bsdf=mat.node_tree.nodes.get('Principled BSDF')
    family='NunBootRubber' if index==2 else 'NunBootWelt' if index==5 else 'NunBootLeather'
    if index in (1,2,4,5,6):
        colour=mat.node_tree.nodes.new('ShaderNodeTexImage');colour.image=bpy.data.images.load(str(R/'Textures'/(family+'_BaseColor.png')),check_existing=True)
        mat.node_tree.links.new(colour.outputs['Color'],bsdf.inputs['Base Color'])
        orm=mat.node_tree.nodes.new('ShaderNodeTexImage');orm.image=bpy.data.images.load(str(R/'Textures'/(family+'_ORM.png')),check_existing=True);orm.image.colorspace_settings.name='Non-Color'
        separate=mat.node_tree.nodes.new('ShaderNodeSeparateColor');mat.node_tree.links.new(orm.outputs['Color'],separate.inputs[0]);mat.node_tree.links.new(separate.outputs['Green'],bsdf.inputs['Roughness'])
        normal=mat.node_tree.nodes.new('ShaderNodeTexImage');normal.image=bpy.data.images.load(str(R/'Textures'/(family+'_Normal.png')),check_existing=True);normal.image.colorspace_settings.name='Non-Color'
        convert=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(normal.outputs['Color'],convert.inputs['Color']);mat.node_tree.links.new(convert.outputs['Normal'],bsdf.inputs['Normal'])
    else:
        bsdf.inputs['Base Color'].default_value=(.105,.112,.119,1) if index==0 else (.105,.076,.049,1) if index==3 else (.01,.01,.01,1)
        bsdf.inputs['Metallic'].default_value=1 if index==0 else 0;bsdf.inputs['Roughness'].default_value=.43 if index==0 else .78
for family,slots in [('NunBootLeather',[1,4,6]),('NunBootRubber',[2]),('NunBootWelt',[5])]:
    h=np.load(R/'Textures'/(family+'_height_cm.npy'));n=h.shape[0]
    image=bpy.data.images.new(family+'_PhysicalHeight',width=n,height=n,float_buffer=True)
    image.colorspace_settings.name='Non-Color';pixels=np.empty((n,n,4),dtype=np.float32);pixels[:,:,:3]=(.5+h/.02)[:,:,None];pixels[:,:,3]=1
    image.pixels.foreach_set(pixels.reshape(-1));image.pack()
    texture=bpy.data.textures.new(family+'_HeightField',type='IMAGE');texture.image=image
    vg=high.vertex_groups.new(name=family+'_HighOnly')
    indices=sorted({v for poly in high.data.polygons if poly.material_index in slots for v in poly.vertices});vg.add(indices,1.,'REPLACE')
    mod=high.modifiers.new(family+'_physical_microrelief','DISPLACE');mod.texture=texture;mod.texture_coords='UV';mod.uv_layer='NativeMetricUV';mod.mid_level=.5;mod.strength=.0002;mod.vertex_group=vg.name
high.hide_render=True;high.hide_set(True)
game['surface_shader_note']='UE material adds native rest-space wear masks; surface textures and material partitions retained here for editing.'
bpy.ops.file.pack_all();bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/'NunBoots_R8.blend'),compress=True)
meta=json.loads((R/'surfaces.json').read_text());meta['source_scan']='Existing project source: xjghdgl top-grain brown leather';(R/'surfaces.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
author=json.loads((R/'authored.json').read_text());author['editable_high_source']='HIGH_BAKE_ONLY_NunBoots_R8 with one SIMPLE subdivision and three physical-height displacements; excluded from game export';author['baking_height_units']='0.02 cm full range; .0002 m displacement in Blender';(R/'authored.json').write_text(json.dumps(author,indent=2),encoding='utf-8')
print('NUN_BOOT_R8_EDITABLE_SOURCE_SAVED',flush=True)
