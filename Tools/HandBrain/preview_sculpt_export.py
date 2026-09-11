import bpy,sys,json
from pathlib import Path
r=Path('D:/FPS3D/FPSGAME/SourceAssets/HandBrain20260910/sculpt_v06')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(r/'A_HandBrain_Howl_Sculpt.fbx'))
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');mesh=next(o for o in bpy.data.objects if o.type=='MESH')
names=json.loads((r/'export_report.json').read_text())['slots']
with bpy.data.libraries.load(str(r/'HandBrain_Refined_Baked.blend')) as (source,target):target.materials=names
for i,material in enumerate(target.materials):mesh.data.materials[i]=material
sys.path.insert(0,str(r.parent/'hunyuan_v01'));import studio
s=bpy.context.scene;cam=studio.setup(768);s.cycles.samples=24
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for d in prefs.devices:d.use=d.type!='CPU'
s.cycles.device='GPU'
studio.aim(cam,(5,-2.4,1.5),(.5,0,.8));cam.data.ortho_scale=1.25
for frame in [1,16,34,66,91]:
 s.frame_set(frame);s.render.filepath=str(r/('Mouth_export_'+str(frame)+'.png'));bpy.ops.render.render(write_still=True)
frames=r/'preview_frames';frames.mkdir(exist_ok=True)
s.render.resolution_x=640;s.render.resolution_y=640;s.cycles.samples=12
studio.aim(cam,(5,-2.4,2.3),(.3,0,1.1));cam.data.ortho_scale=2.6
for frame in range(1,92,4):
 s.frame_set(frame);s.render.filepath=str(frames/(str(frame).zfill(3)+'.png'));bpy.ops.render.render(write_still=True)
(r/'fbx_validation.json').write_text(json.dumps({'imported_bones':len(rig.data.bones),'action_frames':list(rig.animation_data.action.frame_range),'mesh_vertices':len(mesh.data.vertices),'mouth_frames':[1,16,34,66,91]},indent=2))
print('HANDBRAIN_FBX_PREVIEW_COMPLETE')
