"""Finish the editable materials and retain all four fitted alternatives."""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector
O=Path(__file__).parent;auth=json.loads((O/'authoring.json').read_text())
bpy.context.preferences.filepaths.save_version=0
for key in auth:
    path=O/key/'DW715_Attachment_Editable.blend';bpy.ops.wm.open_mainfile(filepath=str(path))
    ob=next(x for x in bpy.context.scene.objects if x.type=='MESH')
    for m in ob.data.materials:
        if any(word in m.name for word in ['Glass','Reticle']):continue
        m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
        replaced=False
        for node in n:
            if node.type=='UVMAP' and 'Coating' in node.uv_map:node.uv_map='DW715FinishUV'
            if node.type=='TEX_IMAGE' and node.image and 'T_M1911_Attachment_' in node.image.name:
                kind='ORM' if 'ORM' in node.image.name else 'BaseColor'
                node.image=bpy.data.images.load(str(O/'Textures'/('T_DW715_Attachment_'+kind+'.png')),check_existing=True)
                node.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';replaced=True
        if replaced:continue
        uv=n.new('ShaderNodeUVMap');uv.uv_map='DW715FinishUV';tex={}
        for kind in ['BaseColor','ORM']:
            sample=n.new('ShaderNodeTexImage');sample.image=bpy.data.images.load(str(O/'Textures'/('T_DW715_Attachment_'+kind+'.png')),check_existing=True)
            sample.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color';l.new(uv.outputs[0],sample.inputs['Vector']);tex[kind]=sample
        orm=n.new('ShaderNodeSeparateColor');l.new(tex['ORM'].outputs[0],orm.inputs[0])
        # Retain the imported structural normal. Separate glass/reticle slots
        # and existing tactical aperture masks remain untouched above.
        l.new(tex['BaseColor'].outputs[0],bs.inputs['Base Color']);l.new(orm.outputs[1],bs.inputs['Roughness']);l.new(orm.outputs[2],bs.inputs['Metallic'])
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(path))
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'DanWesson715MetalFinish20260914/DanWesson715_MetalFinish_Editable.blend'))
except RuntimeError as error:
    if 'Missing library override hierarchy root data' not in str(error):raise
rig=bpy.data.objects['SK_DW715_Manny'];mode=rig.data.pose_position;rig.data.pose_position='REST';bpy.context.view_layer.update()
root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
collection=bpy.data.collections.new('DW715_ATTACHMENT_ALTERNATIVES');bpy.context.scene.collection.children.link(collection)
for key,info in auth.items():
    name='SM_TacticalDevice' if key in ['laser','flashlight'] else 'SM_DW715_'+key
    with bpy.data.libraries.load(str(O/key/'DW715_Attachment_Editable.blend'),link=False) as (src,dst):dst.objects=[name]
    ob=dst.objects[0];collection.objects.link(ob);ob.name='DW715_Attachment_'+key
    local=Matrix.Identity(4) if key in ['laser','flashlight'] else Matrix.Translation(Vector(info['mount_root_m']))@Matrix.Rotation(-math.pi/2,4,'Z')
    ob.parent=rig;ob.parent_type='BONE';ob.parent_bone='WPN_root';ob.matrix_world=root@local
    ob.hide_set(key in ['panoramic_red_dot','flashlight']);ob.hide_render=key in ['panoramic_red_dot','flashlight']
rig.data.pose_position=mode;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_Attachments_Editable.blend'))
print('DW715_ATTACHMENT_ASSEMBLY_SAVED',flush=True)
