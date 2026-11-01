"""Revision-isolated export/import; the gameplay fields are left intact."""
from pathlib import Path
P=Path(__file__).resolve().parent;old=P.parent/'StaticFieldGripV1'
s=(old/'finalize.py').read_text(encoding='utf-8')
s=s.replace("for o in list(bpy.data.collections['DesignPresentation'].objects):bpy.data.objects.remove(o,do_unlink=True)\nbpy.data.collections.remove(bpy.data.collections['DesignPresentation'])",'')
s=s.replace("joined.name='SM_ThunderGodHammer_grip_static_field'","joined.name='SM_ThunderGodHammer_grip_static_field_V2'")
s=s.replace("revision='StaticFieldGripV1'","revision='StaticFieldGripV2'")
s=s.replace("design='Design/StaticField_ThreeViews.png'","design='../StaticFieldGripV1/Design/StaticField_ThreeViews.png'")
s=s.replace("geometry='Closed leather contact core; recessed silver conductors; solid fitted collars; original native UV and corner normals at both end lands'","geometry='Closed skived leather wrap with seam-adaptive topology, two-ply stitches, broad chased silver interlace and curved solid field seals; native end lands retained'")
s=s.replace("normal_maps='3 dedicated 4096 px physical-scale tangent normal maps; OpenGL source, flip green in UE'","normal_maps='4096x8192 leather atlas plus 4096x4096 steel/silver; cellular grain, exact needle sockets, forged grain, directional scratches; OpenGL source, UE flip green'")
setup="""
scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.world=bpy.data.worlds.new('IconNeutralStudio');scene.world.use_nodes=True
world=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND')
world.inputs[0].default_value=(.13,.13,.13,1);world.inputs[1].default_value=.3
scene.view_settings.view_transform='AgX'
def area(name,pos,power,size):
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.shape='DISK';d.size=size
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=pos;o.rotation_euler=(Vector((0,0,0))-o.location).to_track_quat('-Z','Y').to_euler()
area('IconKey',(-.35,-.45,.6),32,.45);area('IconRim',(.3,.15,.2),42,.4);area('IconFill',(.45,-.4,-.3),12,.4)
d=bpy.data.cameras.new('IconCamera');d.type='ORTHO';o=bpy.data.objects.new('IconCamera',d);scene.collection.objects.link(o);scene.camera=o
"""
s=s.replace('# Icon is authored from this exact model, as a separate scene/material copy.',setup+'\n# Production icon uses a separate grayscale authoring scene.')
(P/'finalize.py').write_text(s,encoding='utf-8')
s=(old/'import_assets.py').read_text(encoding='utf-8').replace('/StaticFieldGripV1','/StaticFieldGripV2')
s=s.replace("tex.set_editor_property('max_texture_size', 4096)","tex.set_editor_property('max_texture_size', 8192 if family=='Leather' else 4096)")
s=s.replace('settings.explicit_tangents = True','settings.explicit_tangents = True\nsettings.position_precision = 10\nsettings.normal_precision = 15\nsettings.tangent_precision = 12\nsettings.keep_percent_triangles = 1.\nsettings.trim_relative_error = 0.\nsettings.fallback_target = u.NaniteFallbackTarget.PERCENT_TRIANGLES')
s=s.replace("generator='Blender render of current model; imagegen unavailable'","generator='Blender render of current V2 model'")
(P/'import_assets.py').write_text(s,encoding='utf-8')
(P/'install.ps1').write_text((old/'install.ps1').read_text(encoding='utf-8'),encoding='utf-8')
print('V2_EXPORT_IMPORT_PIPELINE_READY')
