import bpy,math,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_ReceiverContinuityV2_Editable.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=40
scene.render.resolution_x=2000;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('ReceiverV2NeutralStudio');scene.world.use_nodes=True
n=scene.world.node_tree.nodes;n.clear();bg=n.new('ShaderNodeBackground');out=n.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs[0],out.inputs[0]);bg.inputs[0].default_value=(.12,.14,.17,1);bg.inputs[1].default_value=.5
for ob in list(bpy.data.objects):
 if ob.type in ('LIGHT','CAMERA'):bpy.data.objects.remove(ob,do_unlink=True)
for loc,power,size in [((.6,-.05,.8),65,1.2),((-.3,.2,.5),50,.8),((.5,-.6,.25),20,.65)]:
 bpy.ops.object.light_add(type='AREA',location=loc);li=bpy.context.object;li.data.energy=power;li.data.shape='DISK';li.data.size=size;li.rotation_euler=(Vector((0,.05,.05))-li.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera;scene.view_settings.view_transform='AgX'
def render(name,loc,target,scale):
 camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
 scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
render('assembly_side',(1.5,.25,.105),(0,.25,.105),1.34)
render('receiver_close',(1.5,.036,.085),(0,.036,.085),.48)
render('receiver_oblique',(1.5,-.45,.34),(0,.045,.08),.48)
print('M24_RECEIVER_V2_PREVIEW_COMPLETE',flush=True)
