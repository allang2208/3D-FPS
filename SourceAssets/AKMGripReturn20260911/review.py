import bpy,sys
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;args=sys.argv[sys.argv.index('--')+1:];variant,phase,clip=args
base=O.parent/'AKMReloadPolish20260911' if phase=='before' else O/'Final'
bpy.ops.wm.open_mainfile(filepath=str(base/variant/f'A_AKM_{variant}_{clip}.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=900;s.render.resolution_y=600;s.render.resolution_percentage=100
d=bpy.data.cameras.new('ReturnReview');c=bpy.data.objects.new('ReturnReview',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.65
for f in ([380,410,430,440,470,515] if 'empty' in clip else [270,300,320,330,360,400]):
 s.frame_set(f);target=r.matrix_world@r.pose.bones['WPN_root'].matrix@Vector((0,-.23,-.01));c.location=target+Vector((-.6,-.5,.3));c.rotation_euler=(target-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'{variant}_{phase}_{clip}_{f}.png');bpy.ops.render.render(write_still=True)
print('GRIP_RETURN_REVIEW_PASS')
