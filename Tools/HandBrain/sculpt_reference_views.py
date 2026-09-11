import bpy,sys,json
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910');o=r/'sculpt_v06';o.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(r/'realism_v05/HandBrain_Refined_Baked.blend'))
rig=bpy.data.objects['SK_HandBrain'];rig.animation_data.action=bpy.data.actions['Idle'];rig.animation_data.action_slot=bpy.data.actions['Idle'].slots[0];bpy.context.scene.frame_set(1)
sys.path.insert(0,str(r/'hunyuan_v01'));import studio
s=bpy.context.scene;cam=studio.setup(1400);s.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU'
for name,loc in [('left',(0,-6,1)),('right',(0,6,1)),('front',(6,0,1)),('back',(-6,0,1))]:
 studio.aim(cam,loc,(0,0,1));cam.data.ortho_scale=2.18;s.render.filepath=str(o/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(o/'Sculpt_reference.blend'))
