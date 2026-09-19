"""Package the actual UE-produced FBX geometry as editable Blender sources."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
receipt=json.loads((O/'installed.json').read_text())
for kind,part in receipt['parts'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=part['fbx'],use_custom_normals=True)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    for obj in meshes:
        for slot in obj.material_slots:
            m=slot.material;m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF')
            p.inputs['Base Color'].default_value=(.09,.095,.103,1)
            p.inputs['Metallic'].default_value=.7;p.inputs['Roughness'].default_value=.45
            if 'Tactical_'+kind not in m.name:continue
            n=m.node_tree.nodes;l=m.node_tree.links
            prefix=S/'TacticalDevices20260913'
            if kind=='flashlight':prefix=prefix/'HunyuanV3'
            texture=bpy.data.images.load(str(prefix/kind/('T_'+kind+'_BaseColor.png')))
            tex=n.new('ShaderNodeTexImage');tex.image=texture
            # Blender is an editable authoring source; actual runtime shader is
            # the UE dry/wet graph, including its spatial optical mask.
            vc=n.new('ShaderNodeVertexColor')
            if obj.data.color_attributes:vc.layer_name=obj.data.color_attributes[0].name
            mix=n.new('ShaderNodeMixRGB');mix.blend_type='MIX';mix.inputs[2].default_value=(.09,.095,.103,1)
            l.new(vc.outputs['Color'],mix.inputs[0]);l.new(tex.outputs['Color'],mix.inputs[1]);l.new(mix.outputs[0],p.inputs['Base Color'])
            normalfile=prefix/kind/('T_'+kind+'_Normal.png')
            if normalfile.exists():
                im=bpy.data.images.load(str(normalfile));im.colorspace_settings.name='Non-Color'
                t=n.new('ShaderNodeTexImage');t.image=im;normal=n.new('ShaderNodeNormalMap')
                l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],p.inputs['Normal'])
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(O/('ASH12_'+kind+'_Editable.blend')))
print('ASH_TACTICAL_EDITABLE_SOURCES_SAVED',flush=True)
