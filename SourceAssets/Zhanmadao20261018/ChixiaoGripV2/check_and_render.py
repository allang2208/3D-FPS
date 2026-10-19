"""Requested grip inspection: source geometry, joint metrics and matched offline views."""
import json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
P=Path(__file__).resolve().parent;V1=P.parent/'ChixiaoDoubleHeavyV1'
env={'__file__':str(V1/'author_motion.py')}
exec(compile((V1/'author_motion.py').read_text('utf-8').split('receipt=')[0],str(V1/'author_motion.py'),'exec'),env)
A=env['A'];pose_at=env['pose_at'];rigid=env['grip_frame']
report={}
for variant in ('Standard','LongGrip'):
    versions={v:json.loads((folder/variant/'editable_keys.json').read_text('utf-8')) for v,folder in [('V1',V1),('V2',P)]}
    idle=pose_at(versions['V1'],1.);land=pose_at(versions['V1'],.12)
    fingers={s:{n:rigid(land['hand_'+s]).inverted()@land[n].translation for n in A.HANDS[s]} for s in ('l','r')}
    out={}
    for version,clip in versions.items():
        rows=[]
        for sample in clip['samples']:
            w=A.pose_from_rows(sample['bones']);row={'t':sample['seconds'],'sides':{}}
            for s in ('l','r'):
                hn,ln,un=['hand_'+s,'lowerarm_'+s,'upperarm_'+s];h,l,u=[w[n] for n in (hn,ln,un)]
                axis=(h.to_quaternion()@idle[hn].to_quaternion().inverted())@(idle[hn].translation-idle[ln].translation).normalized()
                inv=rigid(h).inverted();grip=rigid(w['WPN_root']).inverted()@h.translation
                row['sides'][s]={'wrist_bend_deg':math.degrees(axis.angle((h.translation-l.translation).normalized())),
                    'finger_shape_error_cm':max(((inv@w[n].translation)-p).length*100 for n,p in fingers[s].items()),
                    'grip_radius_cm':math.hypot(grip.x,grip.y)*100,
                    'upper_cm':(l.translation-u.translation).length*100,'lower_cm':(h.translation-l.translation).length*100}
            rows.append(row)
        focus=[r for r in rows if .12<r['t']<1.]
        peaks={s:{k:dict(t=(m:=max(focus,key=lambda r:r['sides'][s][k]))['t'],value=m['sides'][s][k]) for k in ('wrist_bend_deg','finger_shape_error_cm')} for s in ('l','r')}
        out[version]={'peaks':peaks,'selected':[min(rows,key=lambda r:abs(r['t']-t)) for t in (.12,.18,.24,.30,.38,.5,.75,.9,1.)]}
        print(variant,version,json.dumps(peaks),flush=True)
    out['weapon_max_delta_cm']=max((pose_at(versions['V1'],s['seconds'])['WPN_root'].translation-
        A.pose_from_rows(s['bones'])['WPN_root'].translation).length*100 for s in versions['V2']['samples'])
    report[variant]=out
(P/'contact-check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
for version,folder,blendname in [('V1',V1,'Chixiao_DoubleHeavy_Editable.blend'),('V2',P,'Chixiao_GripV2_Editable.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(folder/'Standard'/blendname));scene=bpy.context.scene
    for ob in scene.objects:
        if ob.type=='MESH':ob.color=(.54,.31,.20,1);ob.hide_render=not bool(ob.vertex_groups)
    with bpy.data.libraries.load(str(P.parent/'ChixiaoBladeV1/Chixiao_Blade_Editable.blend'),link=False) as (available,loaded):
        loaded.objects=[n for n in ('SM_Zhanmadao_Blade_chixiao_V1_LOD0','SM_Zhanmadao_Guard_V1','SM_Zhanmadao_Grip_V1','SM_Zhanmadao_Pommel_V1') if n in available.objects]
    parts=[]
    for ob in loaded.objects:
        scene.collection.objects.link(ob);ob.hide_render=False;ob.hide_set(False);ob.parent=None
        parts.append((ob,ob.matrix_world.copy()));ob.color=(.12,.13,.15,1)
    clip=json.loads((folder/'Standard/editable_keys.json').read_text('utf-8'))
    bpy.ops.object.camera_add(location=(0,0,0));cam=bpy.context.object;cam.rotation_euler=Vector((0,1,0)).to_track_quat('-Z','Y').to_euler()
    cam.data.sensor_fit='VERTICAL';cam.data.sensor_height=24;cam.data.lens=24/(2*math.tan(math.radians(75)/2));cam.data.clip_start=.01;scene.camera=cam
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='STUDIO';scene.display.shading.color_type='OBJECT'
    scene.display.shading.show_shadows=True;scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
    scene.display.shading.background_type='WORLD'
    if not scene.world:scene.world=bpy.data.worlds.new('ChixiaoGripReviewWorld')
    scene.world.color=(.07,.085,.10)
    scene.render.resolution_x=1100;scene.render.resolution_y=600;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    out=P/'PoseReview';out.mkdir(exist_ok=True)
    for t in (.24,.30,.70):
        scene.frame_set(round(t*clip['fps']));w=pose_at(clip,t)
        frame=rigid(w['WPN_root'])@Matrix.Translation((0,0,.045))
        for ob,local in parts:ob.matrix_world=frame@local
        scene.render.filepath=str(out/(version+'_'+str(round(t*100))+'.png'));bpy.ops.render.render(write_still=True)
print('CHIXIAO_GRIP_CHECK_AND_OFFLINE_VIEWS_SAVED',flush=True)
