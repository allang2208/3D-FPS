"""User-requested material/connection close-up of the delivered Blender model."""
import bpy,math
from pathlib import Path
from mathutils import Vector,Matrix
P=Path(__file__).parent
OUT=P/'Review';OUT.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(P/'Bow_FineRingSight.blend'))
sight=bpy.data.objects['SM_Bow_FineRingSight']
for o in list(bpy.data.objects):
    if o!=sight:bpy.data.objects.remove(o,do_unlink=True)
sight.data.transform(Matrix.Scale(.01,4));sight.matrix_world=Matrix.Identity(4)
bodyfile=P.parent/'DarkBow20260925/WoodLongbow20260925/WoodLongbow_Editable.blend'
with bpy.data.libraries.load(str(bodyfile),link=False) as (source,target):
    target.objects=['SM_DarkBow_WoodLongbow']
body=target.objects[0];bpy.context.scene.collection.objects.link(body)
body.hide_render=False;body.hide_set(False)
points=[body.matrix_world@v.co for v in body.data.vertices]
extent=max(max(v[i] for v in points)-min(v[i] for v in points) for i in range(3))
body.data=body.data.copy();body.data.transform(Matrix.Scale(.01 if extent>5 else 1.,4)@body.matrix_world)
body.matrix_world=Matrix.Identity(4)
scene=bpy.context.scene;scene.unit_settings.scale_length=1.
scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
scene.render.resolution_x=1600;scene.render.resolution_y=1200;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
world=bpy.data.worlds.new('Neutral close-up studio');world.use_nodes=True;scene.world=world
world.node_tree.nodes.clear()
background=world.node_tree.nodes.new('ShaderNodeBackground')
output=world.node_tree.nodes.new('ShaderNodeOutputWorld')
world.node_tree.links.new(background.outputs[0],output.inputs['Surface'])
background.inputs['Color'].default_value=(.065,.080,.10,1)
background.inputs['Strength'].default_value=.45
center=Vector((-.018,.053,.165))
camdata=bpy.data.cameras.new('DetailCamera');cam=bpy.data.objects.new('DetailCamera',camdata)
scene.collection.objects.link(cam);scene.camera=cam;camdata.type='ORTHO';camdata.ortho_scale=.182;camdata.clip_start=.001
cam.location=center+Vector((-.35,.34,.105));cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
for name,delta,power,size in [('Key',(-.35,.40,.42),22,.48),('Fill',(-.25,-.28,.15),9,.35),('Rim',(.3,.05,.25),16,.28)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=center+Vector(delta)
    ob.rotation_euler=(center-ob.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'sight_connection_detail.png')
bpy.ops.render.render(write_still=True)
print('BOW_RING_DETAIL_RENDERED',scene.render.filepath)
