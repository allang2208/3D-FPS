"""Use existing PBR materials and light setup for the two revised pocket mouths."""
import bpy,os,math
from pathlib import Path
from mathutils import Vector

P=Path('D:/FPS3D/FPSGAME');S=P/'SourceAssets/PortableBackpackAlice20261019'
R=P/'SourceAssets/BackpacksReview20261021';O=R/'Preview';O.mkdir(exist_ok=True)
os.environ['ALICE_PREVIEW_SRC']=str(R/'AliceBackpack_side_openings.blend')
code=(S/'render_preview.py').read_text(encoding='utf-8-sig')
# Reuse material/light creation only, preserving this task's independent output.
namespace={};exec(compile(code.split('for degree in (0, 90, 180, 270):')[0],str(S/'render_preview.py'),'exec'),namespace)
scene=bpy.context.scene;cam=scene.camera
for con in list(cam.constraints):cam.constraints.remove(con)
scene.render.resolution_x=1000;scene.render.resolution_y=1000;cam.data.dof.use_dof=False
cam.data.type='ORTHO'
for side in (-1,1):
    target=Vector((side*.20,-.065,-.035));cam.location=target+Vector((side*.50,-.28,.25));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.ortho_scale=.28
    scene.render.filepath=str(O/('pocket_left.png' if side<0 else 'pocket_right.png'));bpy.ops.render.render(write_still=True)
cam.data.ortho_scale=.68;target=Vector((0,-.02,.05));cam.location=(.8,-1.1,.65);cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(O/'alice_front.png');bpy.ops.render.render(write_still=True)
