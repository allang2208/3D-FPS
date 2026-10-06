"""Render the actual RSH factory trigger (17_l) as a UI image source."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent;S=O.parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
p=next(x for x in json.loads((S/'RSH12Integration20261003/canonical_parts.json').read_text()) if x['name']=='17_l')
me=bpy.data.meshes.new('RSH_FactoryTrigger_17_l');me.from_pydata(p['verts'],[],p['faces']);me.update()
uv=me.uv_layers.new(name='UV0')
for dst,src in zip(uv.data,p['uv']):dst.uv=src
for face in me.polygons:face.use_smooth=True
me.normals_split_custom_set(p['normals'])
ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
mat=bpy.data.materials.new('RSH_FactoryTrigger_SourcePBR');mat.use_nodes=True;me.materials.append(mat)
n=mat.node_tree.nodes;l=mat.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED')
folder=S/'RSH12Integration20261003/Original/Extracted/textures'
for key,socket in [('albedo','Base Color'),('roughness','Roughness'),('metallic','Metallic'),('normal','Normal')]:
    tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(folder/('DefaultMaterial_'+key+('.png' if key=='normal' else '.jpg'))))
    tex.image.colorspace_settings.name='sRGB' if key=='albedo' else 'Non-Color'
    if key=='normal':
        normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs[socket])
    else:l.new(tex.outputs['Color'],bs.inputs[socket])
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale([ob]);scene=bpy.context.scene;neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
lo=Vector(tuple(min(v[i] for v in p['verts']) for i in range(3)));hi=Vector(tuple(max(v[i] for v in p['verts']) for i in range(3)))
center=(lo+hi)*.5;span=max(hi-lo)
d=bpy.data.cameras.new('FactoryTriggerCamera');cam=bpy.data.objects.new(d.name,d);scene.collection.objects.link(cam)
d.type='ORTHO';d.ortho_scale=span*1.27;d.clip_start=.0001;d.clip_end=10
cam.location=center+Vector((1,.14,0)).normalized()*span*4
cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.world=bpy.data.worlds.new('NeutralIconWorld');scene.world.use_nodes=True
scene.world.node_tree.nodes.clear()
bg=scene.world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.3
out=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs['Background'],out.inputs['Surface'])
for i,(offset,power) in enumerate([((.12,-.07,.13),1.),((.12,.12,.03),.65),((-.1,.04,.08),.85)]):
    light=bpy.data.lights.new('TriggerLight'+str(i),'AREA');light.energy=power;light.size=.10
    lamp=bpy.data.objects.new(light.name,light);scene.collection.objects.link(lamp);lamp.location=center+Vector(offset)
    lamp.rotation_euler=(center-lamp.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.file.pack_all();scene.render.filepath=str(O/'FactoryTrigger_Source.png')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'FactoryTrigger_Icon.blend'))
(O/'source.json').write_text(json.dumps({'part':'17_l','bone':'WPN_Trigger','weapon':'ue_rsh12','slot':'trigger','option':'false',
 'mesh':'/Game/Weapons/RSH12/Native71520261003/single/SK_RSH12_Manny','geometry':'SourceAssets/RSH12Integration20261003/canonical_parts.json',
 'texture_source':str(folder),'camera':'orthographic level; forward (-Y) left; 8 degree side yaw','runtime_modified':False},indent=2))
bpy.ops.render.render(write_still=True)
print('RSH_FACTORY_TRIGGER_ICON_SOURCE_SAVED',flush=True)
