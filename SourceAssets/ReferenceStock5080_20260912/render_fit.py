import bpy,math,json
from mathutils import Vector,Matrix
from pathlib import Path
P=Path(__file__).parent;OLD=P.parent/'SkeletonStock20260912'
for key,origin in [('m4',(0,3.85,7.25)),('akm',(.08,8.3,3.5))]:
 bpy.ops.wm.open_mainfile(filepath=str(OLD/(key+'_fit_reference.blend')));s=bpy.context.scene
 with bpy.data.libraries.load(str(P/('AKM/ReferenceStock5080_AKM_Editable.blend' if key=='akm' else 'ReferenceStock5080_Game_Editable.blend')),link=False) as (a,b):b.objects=['SM_SkeletonStock']
 stock=b.objects[0];s.collection.objects.link(stock);stock.hide_set(False);stock.hide_render=False;stock.matrix_world=Matrix.Translation(origin)@Matrix.Rotation(math.pi/2,4,'Z')
 s.world=bpy.data.worlds.new('FitStudio');s.world.use_nodes=True;s.world.node_tree.nodes.clear();bg=s.world.node_tree.nodes.new('ShaderNodeBackground');bg.inputs[0].default_value=(.2,.23,.27,1);out=s.world.node_tree.nodes.new('ShaderNodeOutputWorld');s.world.node_tree.links.new(bg.outputs[0],out.inputs[0])
 s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True;s.render.resolution_x=1200;s.render.resolution_y=700;s.render.resolution_percentage=100;s.view_settings.exposure=.6
 target=Vector((0,-10,3))
 def aim(o):o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
 for pos,power in [((20,0,60),20000),((-25,-15,40),18000),((5,50,10),10000)]:
  bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.size=45;aim(o)
 bpy.ops.object.camera_add(location=(120,-10,30));cam=bpy.context.object;cam.data.type='ORTHO';cam.data.ortho_scale=105;s.camera=cam;aim(cam)
 s.render.filepath=str(P/(key+'_assembled.png'));bpy.ops.render.render(write_still=True)
 target=Vector(origin)+Vector((0,1,0));cam.location=target+Vector((45,20,16));cam.data.ortho_scale=17;aim(cam);s.render.filepath=str(P/(key+'_interface.png'));bpy.ops.render.render(write_still=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(P/(key+'_assembly_review.blend')))
