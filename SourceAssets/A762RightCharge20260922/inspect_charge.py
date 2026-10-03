"""Inspect native right arm geometry and compare existing charging actions."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent;S=O.parent
(O/'Diagnosis').mkdir(exist_ok=True)
jobs=[('A762',S/'A762EmptySupport20260922/base/A_A762_reload_empty.blend',None,[280,300,310,320,340,350,370,395]),
      ('ASH12',S/'ASH12RightEdgeCharge20260919/ASH12_RightEdgeCharge_Editable.blend',None,[140.4,150]),
      ('M4',S/'M4WrapGrip20260910/M4_Hand_MAT_Editable.blend','M4_MAT_equip_charge',[12,18,26])]
report={}
for tag,path,action,frames in jobs:
    bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima']
    if action:
        a=bpy.data.actions[action];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
    rest={b.name:b.matrix_local.copy() for b in r.data.bones}
    fore=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
    rows={}
    for f in frames:
        s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
        p={b.name:b.matrix.copy() for b in r.pose.bones}
        wrist=(p['hand_r'].to_quaternion()@rest['hand_r'].to_quaternion().inverted())@fore
        arm=(p['hand_r'].translation-p['lowerarm_r'].translation).normalized()
        row={'wrist_bend':math.degrees(wrist.angle(arm)),
             'bones':{n:[list(x) for x in root.inverted()@m] for n,m in p.items()},
             'basis':{b.name:list(b.rotation_quaternion) for b in r.pose.bones}}
        rows[str(f)]=row
    report[tag]={'source':str(path),'action':r.animation_data.action.name,'fps':s.render.fps/s.render.fps_base,
                 'frames':list(r.animation_data.action.frame_range),'rest':{n:[list(x) for x in m] for n,m in rest.items()},
                 'parents':{b.name:b.parent.name if b.parent else None for b in r.data.bones},'samples':rows}
    for ob in s.objects:
        if ob.type=='MESH':
            if ob.hide_render:continue
            ob.color=(.26,.45,.65,1) if 'Arms' in ob.name else (.54,.42,.22,1)
    s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT'
    s.display.shading.show_shadows=True;s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH'
    s.render.resolution_x=900;s.render.resolution_y=650;s.render.resolution_percentage=100
    s.render.image_settings.file_format='JPEG';s.render.image_settings.quality=83
    cam=bpy.data.objects.new('RightChargeDiagnosisCamera',bpy.data.cameras.new('RightChargeDiagnosisCamera'));s.collection.objects.link(cam);s.camera=cam
    cam.data.type='ORTHO';cam.data.ortho_scale=.47
    for f in ([310,320,350] if tag=='A762' else frames[:2]):
        s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update();root=r.pose.bones['WPN_root'].matrix
        center=r.pose.bones['hand_r'].matrix.translation.copy();center+=root.to_3x3()@Vector((0,-.03,.04))
        cam.location=center+root.to_3x3()@Vector((-.70,.28,.30))
        cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
        s.render.filepath=str(O/'Diagnosis'/f'{tag}_{f}.jpg');bpy.ops.render.render(write_still=True)
    if tag=='A762':
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(O/'Working.blend'))
    (O/'reference_poses.json').write_text(json.dumps(report),encoding='utf-8')
    print('CHARGE_REFERENCE',tag,[(f,round(v['wrist_bend'],1)) for f,v in rows.items()],flush=True)
