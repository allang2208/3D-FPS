import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;variant=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'prism';clip=sys.argv[sys.argv.index('--')+2] if '--' in sys.argv and len(sys.argv)>sys.argv.index('--')+2 else 'idle'
bpy.ops.wm.open_mainfile(filepath=str(O/variant/f'A_AKM_{variant}_{clip}.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;s.frame_set(0 if clip=='idle' else 22)
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
d=bpy.data.cameras.new('Contact');cam=bpy.data.objects.new('Contact',d);s.collection.objects.link(cam);s.camera=cam;d.type='ORTHO';d.ortho_scale=.55
target=r.matrix_world@r.pose.bones['hand_l'].matrix.translation
for tag,offset in [('palm',(-.5,.35,.25)),('back',(.5,-.35,.3))]:
 cam.location=target+Vector(offset);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{variant}_{clip}_{tag}.png');bpy.ops.render.render(write_still=True)
