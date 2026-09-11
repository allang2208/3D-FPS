import bpy,json
from pathlib import Path
P=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(P/'magic_dust_physical_editable.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.margin=8
for name in ['Individual powder grains','Packed powder side grains']:
    obj=bpy.data.objects[name];obj.data.materials[0]=obj.data.materials[0].copy()
for name,tag,low,high in [('Closed steel lid with geometric knurling','lid',.25,.43),('Contained powder volume','powder',.72,.92)]:
    o=bpy.data.objects[name];bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
    m=o.data.materials[0];nt=m.node_tree;p=nt.nodes.get('Principled BSDF');out=nt.nodes.get('Material Output')
    img=bpy.data.images.new('magic_dust_'+tag+'_normal',width=2048,height=2048);img.colorspace_settings.name='Non-Color'
    tex=nt.nodes.new('ShaderNodeTexImage');tex.image=img;nt.nodes.active=tex
    bpy.ops.object.bake(type='NORMAL');img.filepath_raw=str(P/(img.name+'.png'));img.file_format='PNG';img.save()
    normal=nt.nodes.new('ShaderNodeNormalMap');nt.links.new(tex.outputs['Color'],normal.inputs['Color']);nt.links.new(normal.outputs['Normal'],p.inputs['Normal'])
    rough=bpy.data.images.new('magic_dust_'+tag+'_roughness',width=2048,height=2048);rough.colorspace_settings.name='Non-Color'
    rt=nt.nodes.new('ShaderNodeTexImage');rt.image=rough;nt.nodes.active=rt
    noise=nt.nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=17;noise.inputs['Detail'].default_value=4
    ramp=nt.nodes.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(low,low,low,1);ramp.color_ramp.elements[1].color=(high,high,high,1)
    em=nt.nodes.new('ShaderNodeEmission');nt.links.new(noise.outputs['Fac'],ramp.inputs['Fac']);nt.links.new(ramp.outputs['Color'],em.inputs['Color']);nt.links.new(em.outputs[0],out.inputs['Surface'])
    bpy.ops.object.bake(type='EMIT');rough.filepath_raw=str(P/(rough.name+'.png'));rough.file_format='PNG';rough.save()
    nt.links.new(p.outputs[0],out.inputs['Surface']);nt.links.new(rt.outputs['Color'],p.inputs['Roughness'])
    img.pack();rough.pack()
    albedo=bpy.data.images.new('magic_dust_'+tag+'_basecolor',width=2048,height=2048)
    at=nt.nodes.new('ShaderNodeTexImage');at.image=albedo;nt.nodes.active=at
    noise.inputs['Scale'].default_value=38 if tag=='lid' else 180
    ramp.color_ramp.elements[0].color=(.18,.20,.22,1) if tag=='lid' else (.34,.38,.41,1)
    ramp.color_ramp.elements[1].color=(.40,.43,.46,1) if tag=='lid' else (.54,.58,.61,1)
    nt.links.new(em.outputs[0],out.inputs['Surface']);bpy.ops.object.bake(type='EMIT')
    albedo.filepath_raw=str(P/(albedo.name+'.png'));albedo.file_format='PNG';albedo.save();albedo.pack()
    nt.links.new(p.outputs[0],out.inputs['Surface']);nt.links.new(at.outputs['Color'],p.inputs['Base Color'])
bpy.data.objects['Glass vessel with interior wall'].visible_shadow=False
bpy.ops.wm.save_as_mainfile(filepath=str(P/'magic_dust_physical_editable.blend'))
bpy.ops.export_scene.gltf(filepath=str(P/'magic_dust_physical_candidate.glb'),export_format='GLB')
provenance=json.loads((P/'magic_dust_physical_provenance.json').read_text(encoding='utf-8-sig'))
provenance['procedural_micro_bump']='Steel lid and powder volume baked to 2048 base color, tangent normal and roughness textures; packed in Blender and GLB.'
provenance['preview_shadow_approximation']='Glass shadow visibility disabled in studio render to avoid dark interiors without refractive caustics; not UE runtime validation.'
(P/'magic_dust_physical_provenance.json').write_text(json.dumps(provenance,indent=2))
