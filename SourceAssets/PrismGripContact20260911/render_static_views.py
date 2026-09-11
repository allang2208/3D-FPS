from pathlib import Path
import sys,bpy
from mathutils import Vector
O=Path(__file__).parent/'prism';sys.argv=['render','--idle'];__file__=str(O/'review_animation.py');exec(compile((O/'review_animation.py').read_text(),str(O/'review_animation.py'),'exec'));s.frame_set(0);s.render.resolution_x=1000;s.render.resolution_y=800;d=cam.data;d.ortho_scale=.25
for label,offset in [('palm',Vector((0,-.35,-.03))),('back',Vector((0,.35,-.03))),('front',Vector((.35,0,-.03)))]:
 cam.location=focus+grip.to_3x3()@offset;cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/f'final_{label}.png');bpy.ops.render.render(write_still=True)
