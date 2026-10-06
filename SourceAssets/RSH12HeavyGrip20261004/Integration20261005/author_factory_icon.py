"""Produce a factory-grip UI icon source from the actual 9_l mesh."""
import bpy,json,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent.parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'RSH12_HeavyGrip_Editable.blend'))
for ob in list(bpy.data.objects):bpy.data.objects.remove(ob,do_unlink=True)
p=next(v for v in json.loads((S/'RSH12Integration20261003/canonical_parts.json').read_text()) if v['name']=='9_l')
me=bpy.data.meshes.new('RSH_FactoryGrip');me.from_pydata(p['verts'],[],p['faces']);me.update()
me.materials.append(bpy.data.materials['RSH12HeavyGrip_OriginalContactShell'])
uv=me.uv_layers.new(name='UV0')
for dst,src in zip(uv.data,p['uv']):dst.uv=src
for f in me.polygons:f.use_smooth=True
me.normals_split_custom_set(p['normals'])
ob=bpy.data.objects.new(me.name,me);bpy.context.scene.collection.objects.link(ob)
sys.path.insert(0,'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale,neutral_output
apply_grayscale([ob]);scene=bpy.context.scene;neutral_output(scene)
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA';scene.render.film_transparent=True
lo=Vector(tuple(min(v[i] for v in p['verts']) for i in range(3)));hi=Vector(tuple(max(v[i] for v in p['verts']) for i in range(3)));center=(lo+hi)*.5;span=max(hi-lo)
d=bpy.data.cameras.new('FactoryGrip_IconCamera');cam=bpy.data.objects.new(d.name,d);scene.collection.objects.link(cam);d.type='ORTHO';d.ortho_scale=span*1.24;d.clip_start=.001
cam.location=center+Vector((1,.5,.12)).normalized()*span*3;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();scene.camera=cam
scene.world=bpy.data.worlds.new('IconWorld');scene.world.use_nodes=True
bg=scene.world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.5
out=scene.world.node_tree.nodes.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs['Background'],out.inputs['Surface'])
for i,(offset,power) in enumerate([((.15,-.10,.18),10),((.10,.20,.13),8),((-.15,.08,.15),10)]):
    light=bpy.data.lights.new('IconLight'+str(i),'AREA');light.energy=power;light.size=.15;obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=center+Vector(offset);obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'FactoryGrip_Source.png');bpy.ops.render.render(write_still=True)
print('RSH_FACTORY_ICON_SOURCE_SAVED')
