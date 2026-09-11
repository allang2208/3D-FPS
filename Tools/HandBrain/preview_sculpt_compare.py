import bpy,sys
from pathlib import Path
from mathutils import Vector
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910');o=r/'sculpt_v06'
sys.path.insert(0,str(r/'hunyuan_v01'));import studio
for version,label in [('realism_v05','Before'),('sculpt_v06','After')]:
 bpy.ops.wm.open_mainfile(filepath=str(r/version/'HandBrain_Refined_Baked.blend'))
 if version=='sculpt_v06':
  bpy.context.view_layer.objects.active=bpy.data.objects['HandBrain_Body'];bpy.ops.mesh.customdata_custom_splitnormals_clear()
 for obj in list(bpy.data.objects):
  if obj.type in ['LIGHT','CAMERA'] or obj.name.startswith('PreviewFloor') or obj.name=='HandBrain_Sculpt_High':bpy.data.objects.remove(obj,do_unlink=True)
 s=bpy.context.scene;cam=studio.setup(1200);s.cycles.samples=32
 lights=[x for x in s.objects if x.type=='LIGHT']
 for light in lights:bpy.data.objects.remove(light,do_unlink=True)
 for loc,power,size in [((-1.5,-2,2.8),180,1),((2,-3,1.5),50,2)]:
  bpy.ops.object.light_add(type='AREA',location=loc);light=bpy.context.object;light.data.energy=power;light.data.size=size;light.rotation_euler=(Vector((0,0,1.1))-light.location).to_track_quat('-Z','Y').to_euler()
 s.world.node_tree.nodes['Background'].inputs[1].default_value=.15
 prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
 for d in prefs.devices:d.use=d.type!='CPU'
 s.cycles.device='GPU';studio.aim(cam,(0,-6,1.06),(0,0,1.06));cam.data.ortho_scale=.75
 s.render.filepath=str(o/('Hands_'+label+'.png'));bpy.ops.render.render(write_still=True)
 m=bpy.data.materials.new('Geometry inspection clay');m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(.3,.3,.3,1);p.inputs['Roughness'].default_value=.65
 s.view_layers[0].material_override=m;s.render.filepath=str(o/('Geometry_'+label+'.png'));bpy.ops.render.render(write_still=True)
print('SCULPT_COMPARISON_COMPLETE')
