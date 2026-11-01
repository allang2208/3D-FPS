import bpy,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M24_StockContinuity_Editable.blend'),load_ui=False,use_scripts=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48
scene.render.resolution_x=1800;scene.render.resolution_y=700;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('M24ContinuityPreview');scene.world.use_nodes=True
n=scene.world.node_tree.nodes;n.clear();bg=n.new('ShaderNodeBackground');out=n.new('ShaderNodeOutputWorld');scene.world.node_tree.links.new(bg.outputs[0],out.inputs[0]);bg.inputs[0].default_value=(.12,.14,.17,1);bg.inputs[1].default_value=.5
for loc,power,size in [((.6,-.05,.8),65,1.2),((-.3,.2,.5),50,.8),((.5,-.6,.25),20,.65)]:
 bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.shape='DISK';light.data.size=size;light.rotation_euler=(Vector((0,.05,.05))-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera;scene.view_settings.view_transform='AgX'
def render(name,loc,target,scale):
 camera.location=loc;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
 scene.render.filepath=str(O/(name+'.png'));bpy.ops.render.render(write_still=True)
render('after_side',(1.5,.12,.074),(0,.12,.074),1.10)
render('after_connection',(1.5,-.001,.16),(0,-.001,.068),.40)
print('M24_CONTINUITY_PREVIEWS_SAVED',flush=True)
