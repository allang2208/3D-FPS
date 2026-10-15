"""User-requested check of normal combo stage 2 (left-to-right) and the mirror
route for a left-hand-top second cut. Reads the accepted NormalComboV4 source,
measures grips/joints and renders first-person contact sheets for inspection."""
import json,math,sys
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix,Vector,kdtree

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
idle=sample('A_Warhammer_Slash1',0.)
inv=rest['WPN_root'].inverted();hammer=bpy.data.objects['SM_SteelWarhammer']
local=[inv@(rig.matrix_world.inverted()@hammer.matrix_world@v.co) for v in hammer.data.vertices]
head_local=[p for p in local if p.z>.875];head_c=sum(head_local,Vector())/len(head_local)

# Mirror feasibility --------------------------------------------------------
M=Matrix.Diagonal((-1,1,1,1));S=Matrix.Diagonal((1,-1,1,1))
def partner(n):
    return n[:-2]+'_r' if n.endswith('_l') else n[:-2]+'_l' if n.endswith('_r') else n
fix={n:rest[partner(n)].inverted()@M@rest[n] for n in rest if partner(n) in rest}
asym=max((rest[n].translation-M@rest[partner(n)].translation).length for n in rest if partner(n) in rest)
lengths=max(abs(local_rest[n].translation.length-local_rest[partner(n)].translation.length) for n in rest if partner(n) in local_rest)
tree=kdtree.KDTree(len(local))
for i,p in enumerate(local):tree.insert(p,i)
tree.balance()
def symmetry(mat):
    d=[tree.find(mat@p)[2] for p in local[::23]];d.sort();return {'median_mm':d[len(d)//2]*1000,'p95_mm':d[int(len(d)*.95)]*1000,'max_mm':d[-1]*1000}
sym={'local_y_flip':symmetry(Matrix.Diagonal((1,-1,1))),'local_x_flip':symmetry(Matrix.Diagonal((-1,1,1)))}
def mirror_pose(pose):
    out={}
    for n in pose:
        q=partner(n)
        out[n]=M@pose[q]@fix[n] if n!='WPN_root' else M@pose[n]@S
    return out

def grip(pose,side):
    g=pose['WPN_root'].inverted()@pose['hand_'+side]
    return {'z':round(g.translation.z,4),'angle_deg':round(math.degrees(math.atan2(g.translation.y,g.translation.x)),1),'radius':round(g.translation.xy.length,4)}
fore_idle={s:(idle['hand_'+s].translation-idle['lowerarm_'+s].translation).normalized() for s in ('l','r')}
def bend(pose,s,ref):
    f0=(ref['hand_'+s].translation-ref['lowerarm_'+s].translation).normalized()
    f=(pose['hand_'+s].translation-pose['lowerarm_'+s].translation).normalized()
    d=pose['hand_'+s].to_quaternion()@ref['hand_'+s].to_quaternion().inverted()
    return round(math.degrees((d@f0).angle(f)),1)
def thumb_along(pose,s):
    axis=(pose['WPN_root'].to_quaternion()@Vector((0,0,1))).normalized()
    return round(((pose['thumb_03_'+s].translation-pose['hand_'+s].translation).normalized()).dot(axis),3)
TIMES=[0.,.40,.70,.85,.91,.97,1.05,1.15,1.35,1.75]
report={'mirror':{'rest_position_asymmetry_mm':asym*1000,'bone_length_asymmetry_mm':lengths*1000,'hammer_symmetry':sym},
    'idle':{'grip':{s:grip(idle,s) for s in ('l','r')},'thumb_along_shaft':{s:thumb_along(idle,s) for s in ('l','r')}},'actions':{}}
for action in ('A_Warhammer_Slash1','A_Warhammer_Slash2','A_Warhammer_Slash3'):
    rows=[]
    for t in TIMES:
        p=sample(action,t);w=p['WPN_root']
        rows.append({'t':t,'axis':[round(x,3) for x in (w.to_quaternion()@Vector((0,0,1)))],'head':[round(x,3) for x in w@head_c],
            'hands':{s:[round(x,3) for x in p['hand_'+s].translation] for s in ('l','r')},
            'elbows':{s:[round(x,3) for x in p['lowerarm_'+s].translation] for s in ('l','r')},
            'grip':{s:grip(p,s) for s in ('l','r')},'wrist_bend_vs_idle':{s:bend(p,s,idle) for s in ('l','r')}})
    report['actions'][action]=rows
# Stage 2 = mirrored stage 1: compare its endpoints to the real idle.
mi=mirror_pose(idle)
report['mirrored_idle']={'axis':[round(x,3) for x in mi['WPN_root'].to_quaternion()@Vector((0,0,1))],'grip':{s:grip(mi,s) for s in ('l','r')},
    'thumb_along_shaft':{s:thumb_along(mi,s) for s in ('l','r')}}
(P/'probe.json').write_text(json.dumps(report,indent=1),encoding='utf-8')
print('COMBO_PROBE '+json.dumps(report['mirror'])+' '+json.dumps(report['idle'])+' '+json.dumps(report['mirrored_idle']))

# First-person contact sheets ----------------------------------------------
def apply_pose(pose):
    for bone in rig.pose.bones:
        pi=pose[bone.parent.name].inverted() if bone.parent else Matrix.Identity(4)
        bone.matrix_basis=local_rest[bone.name].inverted()@pi@pose[bone.name]
    bpy.context.view_layer.update()
keep={'SK_RusticPickaxe_Rig','Warhammer_BareArmsV7','SM_SteelWarhammer'}
for o in scene.objects:o.hide_render=o.name not in keep
cam_data=bpy.data.cameras.new('ProbeCam');cam_data.sensor_fit='VERTICAL';cam_data.angle_y=math.radians(75.);cam_data.clip_start=.03
cam=bpy.data.objects.new('ProbeCam',cam_data);scene.collection.objects.link(cam);cam.rotation_euler=(math.pi/2,0,0);cam.location=(0,0,0)
scene.camera=cam;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='MATERIAL'
scene.render.resolution_x=480;scene.render.resolution_y=270;scene.render.resolution_percentage=100;scene.render.film_transparent=False
scene.render.image_settings.file_format='PNG'
def render(pose,path):
    rig.animation_data.action=None;apply_pose(pose);scene.render.filepath=str(path);bpy.ops.render.render(write_still=True)
def sheet(paths,out,cols):
    imgs=[bpy.data.images.load(str(p)) for p in paths];w,h=imgs[0].size;rows=math.ceil(len(imgs)/cols)
    canvas=np.zeros((rows*h,cols*w,4),dtype=np.float32)
    for i,im in enumerate(imgs):
        a=np.array(im.pixels[:],dtype=np.float32).reshape(h,w,4);r,c=divmod(i,cols)
        canvas[(rows-1-r)*h:(rows-r)*h,c*w:(c+1)*w]=a
    out_img=bpy.data.images.new(out.stem,cols*w,rows*h,alpha=True);out_img.pixels=canvas.ravel().tolist()
    out_img.filepath_raw=str(out);out_img.file_format='PNG';out_img.save()
frames=P/'Frames';frames.mkdir(exist_ok=True)
SHEET_TIMES=[0.,.55,.85,.93,.97,1.05,1.20,1.75]
for label,source,mirror in [('slash1','A_Warhammer_Slash1',False),('slash2_current','A_Warhammer_Slash2',False),('slash1_mirrored','A_Warhammer_Slash1',True)]:
    paths=[]
    for t in SHEET_TIMES:
        pose=sample(source,t)
        if mirror:pose=mirror_pose(pose)
        path=frames/f'{label}_{int(t*1000):04d}.png';render(pose,path);paths.append(path)
    sheet(paths,P/f'sheet_{label}.png',4)
print('COMBO_PROBE_SHEETS_DONE')
