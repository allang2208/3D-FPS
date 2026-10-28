"""Render actual current parts against one generated standard frame material."""
import bpy,json,runpy
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'Kukri_IconInputs_Editable.blend'))
scene=bpy.context.scene
manifest=json.loads((P/'icon-manifest.json').read_text(encoding='utf-8'))
objects=[bpy.data.objects[m['object']] for m in manifest['masters']]
# The split factory author file carries preview shaders; restore its real runtime
# PBR maps before the icon-only grayscale conversion.
factory=[]
for master in manifest['masters']:
    if master['id'] not in ('ue_kukri_blade_1_false','ue_kukri_grip_false','ue_kukri_pommel_false'):continue
    obj=bpy.data.objects[master['object']]
    m=bpy.data.materials.new('Icon_CurrentFactory_'+master['slot']);m.use_nodes=True
    nt=m.node_tree;bs=nt.nodes.get('Principled BSDF')
    for suffix in ('BaseColor','ORM','Normal'):
        t=nt.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(P.parent/'Kukri20261020/Textures'/('T_Kukri_'+suffix+'.png')),check_existing=True)
        t.image.colorspace_settings.name='sRGB' if suffix=='BaseColor' else 'Non-Color'
        if suffix=='BaseColor':nt.links.new(t.outputs[0],bs.inputs['Base Color'])
        elif suffix=='ORM':
            sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(t.outputs[0],sep.inputs[0]);nt.links.new(sep.outputs[1],bs.inputs['Roughness']);nt.links.new(sep.outputs[2],bs.inputs['Metallic'])
        else:
            n=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(t.outputs[0],n.inputs['Color']);nt.links.new(n.outputs[0],bs.inputs['Normal'])
    obj.data.materials.clear();obj.data.materials.append(m);factory.append(obj)
gray=runpy.run_path(str(P.parent/'KukriBladeVariants20261026/icon_grayscale.py'));gray['apply_grayscale'](factory)
size=scene.camera.data.ortho_scale
vertices=[(-size/2,.60,-size/2),(size/2,.60,-size/2),(size/2,.60,size/2),(-size/2,.60,size/2)]
mesh=bpy.data.meshes.new('StandardFramePlate');mesh.from_pydata(vertices,[],[(0,1,2,3)]);mesh.update()
uv=mesh.uv_layers.new(name='FrameUV')
for a,b in zip(uv.data,[(0,0),(1,0),(1,1),(0,1)]):a.uv=b
plate=bpy.data.objects.new('StandardFramePlate',mesh);scene.collection.objects.link(plate)
plate.visible_shadow=False;plate.visible_diffuse=False;plate.visible_glossy=False
m=bpy.data.materials.new('StandardFrame_ImageGen');m.use_nodes=True;nt=m.node_tree;nt.nodes.clear()
t=nt.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(P/'StandardEmptyFrame.png'));t.image.colorspace_settings.name='sRGB'
emission=nt.nodes.new('ShaderNodeEmission');nt.links.new(t.outputs['Color'],emission.inputs['Color'])
transparent=nt.nodes.new('ShaderNodeBsdfTransparent');mix=nt.nodes.new('ShaderNodeMixShader')
nt.links.new(t.outputs['Alpha'],mix.inputs[0]);nt.links.new(transparent.outputs[0],mix.inputs[1]);nt.links.new(emission.outputs[0],mix.inputs[2])
output=nt.nodes.new('ShaderNodeOutputMaterial');nt.links.new(mix.outputs[0],output.inputs['Surface']);mesh.materials.append(m)
# Standard view leaves the image-generated UI plate's grayscale values intact.
scene.view_settings.view_transform='Standard';scene.view_settings.look='None';scene.view_settings.exposure=0;scene.view_settings.gamma=1
scene.cycles.samples=64;scene.cycles.use_denoising=True
for obj in objects:
    radius=max((Vector((p.x,0,p.z))).length for p in (obj.matrix_world@v.co for v in obj.data.vertices))
    obj.scale*=min(1.,.72/radius);obj.location*=min(1.,.72/radius)
for master in manifest['masters']:
    obj=bpy.data.objects[master['object']]
    for other in objects:other.hide_set(other!=obj);other.hide_render=other!=obj
    scene.render.filepath=master['output'];bpy.ops.render.render(write_still=True)
    master['frame_source']=str(P/'StandardEmptyFrame.png');master['generation_method']='Real 3D model rendered against image_gen standard frame'
    print('KUKRI_STANDARD_ICON '+master['id'],flush=True)
manifest['rendering']='One image_gen standard frame material plus 20 current real-model/symbol renders; 26 runtime bindings'
(P/'icon-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Kukri_StandardIcons_Editable.blend'))
