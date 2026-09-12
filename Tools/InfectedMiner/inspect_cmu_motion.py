import bpy,json,math
from pathlib import Path
R=Path('D:/FPS3D/FPSGAME/SourceAssets/InfectedMiner20260912/Reference/CMU')
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.preferences.addon_enable(module='io_anim_bvh');s=bpy.context.scene;reports={}
for clip in ['79_01','80_71','02_07','02_08','02_09']:
    fps=120 if clip.startswith('02') else 60;s.render.fps=fps
    bpy.ops.import_anim.bvh(filepath=str(R/(clip+'.bvh')),global_scale=1,frame_start=1,use_fps_scale=False,update_scene_fps=False,rotate_mode='QUATERNION',axis_forward='-Z',axis_up='Y');r=bpy.context.object
    s.frame_set(1);bpy.context.view_layer.update();zs=[(r.matrix_world@b.head).z for b in r.pose.bones];r.scale*=1.78/(max(zs)-min(zs));bpy.context.view_layer.update();end=round(r.animation_data.action.frame_range[1]);rows=[]
    for f in range(2,end+1,fps//30):
        s.frame_set(f);bpy.context.view_layer.update();p={n:(r.matrix_world@r.pose.bones[n].matrix).translation for n in ['Hips','Head','LeftHand','RightHand','LeftForeArm','RightForeArm']};rows.append({'frame':f,'time':(f-2)/fps,'joints':{n:list(v) for n,v in p.items()}})
    peaks=[]
    for side in ['RightHand','LeftHand']:
        v=[(30*(b['joints'][side][2]-a['joints'][side][2]),b['time'],b['frame']) for a,b in zip(rows,rows[1:])];picked=[]
        for speed,t,f in sorted(v):
            if all(abs(t-e[1])>.7 for e in picked):picked.append((speed,t,f))
            if len(picked)==3:break
        peaks.append({'hand':side,'maximum_z':max(row['joints'][side][2] for row in rows),'downward_velocity_peaks':picked})
    reports[clip]={'fps':fps,'seconds':(end-2)/fps,'peaks':peaks,'samples':rows};bpy.data.objects.remove(r,do_unlink=True)
(R/'motion-analysis.json').write_text(json.dumps(reports,indent=2));print('CMU_PEAKS '+json.dumps({n:{k:v for k,v in r.items() if k!='samples'} for n,r in reports.items()}))
