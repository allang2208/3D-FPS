"""Dense first-person and external views of current Slash2 vs mirrored Slash1 (diagnosis only)."""
import math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[3]
SOURCE=ROOT/'SourceAssets/SteelWarhammer20261014/NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
FPS=300
def sample(action,t):
    rig.animation_data.action=bpy.data.actions[action];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    f=t*FPS;scene.frame_set(int(f),subframe=f-int(f))
    return {b.name:b.matrix.copy() for b in rig.pose.bones}
M=Matrix.Diagonal((-1,1,1,1));S=Matrix.Diagonal((1,-1,1,1))
def partner(n):return n[:-2]+'_r' if n.endswith('_l') else n[:-2]+'_l' if n.endswith('_r') else n
fix={n:rest[partner(n)].inverted()@M@rest[n] for n in rest}
def mirror_pose(pose):return {n:(M@pose[n]@S if n=='WPN_root' else M@pose[partner(n)]@fix[n]) for n in pose}
def apply_pose(pose):
    for bone in rig.pose.bones:
        pi=pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
        bone.matrix_basis=local_rest[bone.name].inverted()@pi@pose[bone.name]
    bpy.context.view_layer.update()
keep={'SK_RusticPickaxe_Rig','Warhammer_BareArmsV7','SM_SteelWarhammer'}
for o in scene.objects:o.hide_render=o.name not in keep
def camera(name,loc,target,fov):
    d=bpy.data.cameras.new(name);d.sensor_fit='VERTICAL';d.angle_y=math.radians(fov);d.clip_start=.03
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc
    o.rotation_euler=(Vector(target)-Vector(loc)).to_track_quat('-Z','Y').to_euler();return o
fp=camera('FP',(0,0,0),(0,1,0),75.);ext=camera('EXT',(-1.1,2.1,.55),(0,.15,-.05),48.)
top=camera('TOP',(0,-.35,2.3),(0,.25,-.1),48.)
# Eye marker so the external view shows where the camera is.
bpy.ops.mesh.primitive_uv_sphere_add(radius=.035,location=(0,0,0));eye=bpy.context.active_object;eye.name='EyeMarker'
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.render.resolution_x=400;scene.render.resolution_y=225;scene.render.image_settings.file_format='PNG'
def render(cam,path):scene.camera=cam;scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
def sheet(paths,out,cols):
    imgs=[bpy.data.images.load(str(p)) for p in paths];w,h=imgs[0].size;rows=math.ceil(len(imgs)/cols)
    canvas=np.zeros((rows*h,cols*w,4),dtype=np.float32)
    for i,im in enumerate(imgs):
        a=np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4);r,c=divmod(i,cols)
        canvas[(rows-1-r)*h:(rows-r)*h,c*w:(c+1)*w]=a
    o=bpy.data.images.new(out.stem,cols*w,rows*h,alpha=True);o.pixels=canvas.ravel().tolist();o.filepath_raw=str(out);o.file_format='PNG';o.save()
frames=P/'Frames';frames.mkdir(exist_ok=True)
TIMES=[float(x) for x in sys.argv[sys.argv.index('--')+1].split(',')] if '--' in sys.argv else [.2,.3,.4,.5,.6,.7,.85,.97,1.1,1.25,1.4,1.55]
for label,source,mirror in [('slash2_current','A_Warhammer_Slash2',False),('slash1_mirrored','A_Warhammer_Slash1',True)]:
    for view,cam in (('fp',fp),('ext',ext),('top',top)):
        paths=[]
        for t in TIMES:
            pose=sample(source,t)
            if mirror:pose=mirror_pose(pose)
            rig.animation_data.action=None;apply_pose(pose)
            path=frames/f'{label}_{view}_{int(t*1000):04d}.png';render(cam,path);paths.append(path)
        sheet(paths,P/f'dense_{label}_{view}.png',4)
print('RENDER_COMPARE_DONE')
