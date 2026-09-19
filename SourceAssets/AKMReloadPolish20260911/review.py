import bpy,sys,runpy
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
file=Path(args[0]) if args else O.parent/'AKMAttachments20260911/AKM_Attachments_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(file));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
if not args:r.animation_data.action=bpy.data.actions['AKM_Native_reload'];r.animation_data.action_slot=r.animation_data.action.slots[0]
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=900;s.render.resolution_y=600;s.render.resolution_percentage=100
runpy.run_path(str(O.parent/'AKMAttachments20260911/preview_visibility.py'))['configure_preview'](True)
for ob in s.objects:
 if ob.name.startswith('SM_AKM_'):ob.hide_render=ob.name!='SM_AKM_drum'
d=bpy.data.cameras.new('Review');cam=bpy.data.objects.new('Review',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.62
for f in ([0,52,60,64,68,72] if not args else [0,56,64,76,86,98]):
 s.frame_set(f);target=r.matrix_world@r.pose.bones['WPN_root'].matrix@Vector((0,-.08,-.07));cam.location=target+Vector((.8,.3,.20));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{"after" if args else "before"}_{f}.png');bpy.ops.render.render(write_still=True)
print('REVIEW_PASS')
