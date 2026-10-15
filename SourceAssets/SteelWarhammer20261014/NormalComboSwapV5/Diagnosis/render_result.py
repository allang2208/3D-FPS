"""Contact sheets of the authored hand-swap stage 2 (diagnosis for the user's check request)."""
import math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector

P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'Warhammer_Combo_Swap_Editable.blend'))
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig']
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ACTION=args[0] if args else 'A_Warhammer_Slash2'
TIMES=[float(x) for x in args[1].split(',')] if len(args)>1 else [0.,.28,.34,.40,.46,.52,.58,.70,.82,.97,1.10,1.17,1.24,1.31,1.40,1.60]
keep={'SK_RusticPickaxe_Rig','Warhammer_BareArmsV7','SM_SteelWarhammer'}
for o in scene.objects:o.hide_render=o.name not in keep
def camera(name,loc,target,fov):
    d=bpy.data.cameras.new(name);d.sensor_fit='VERTICAL';d.angle_y=math.radians(fov);d.clip_start=.03
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();return o
views={'fp':camera('FP',(0,0,0),(0,1,0),75.),'front':camera('FRONT',(-.55,1.55,.25),(0,.2,-.05),45.),'top':camera('TOP',(0,-.25,1.7),(0,.3,-.1),55.)}
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.render.resolution_x=400;scene.render.resolution_y=225;scene.render.image_settings.file_format='PNG'
rig.animation_data.action=bpy.data.actions[ACTION];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
frames=P/'Frames';frames.mkdir(exist_ok=True)
def sheet(paths,out,cols):
    imgs=[bpy.data.images.load(str(p)) for p in paths];w,h=imgs[0].size;rows=math.ceil(len(imgs)/cols)
    canvas=np.zeros((rows*h,cols*w,4),dtype=np.float32)
    for i,im in enumerate(imgs):
        a=np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4);r,c=divmod(i,cols)
        canvas[(rows-1-r)*h:(rows-r)*h,c*w:(c+1)*w]=a
    o=bpy.data.images.new(out.stem,cols*w,rows*h,alpha=True);o.pixels=canvas.ravel().tolist();o.filepath_raw=str(out);o.file_format='PNG';o.save()
for view,cam in views.items():
    scene.camera=cam;paths=[]
    for t in TIMES:
        f=t*300;scene.frame_set(int(f),subframe=f-int(f))
        path=frames/f'result_{ACTION}_{view}_{int(t*1000):04d}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);paths.append(path)
    sheet(paths,P/f'result_{ACTION}_{view}.png',4)
print('RENDER_RESULT_DONE')
