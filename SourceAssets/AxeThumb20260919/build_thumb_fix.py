"""Replace only right-thumb rotation tracks in the current four axe clips."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Euler

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OUT=HERE/'Fixed'
(OUT/'Export').mkdir(parents=True,exist_ok=True)
FIT=json.loads((HERE/'thumb_fit.json').read_text(encoding='utf-8'))
x=FIT['rotation_parameters_deg']
rotations={'thumb_01_r':x[:3],'thumb_02_r':[0,0,x[3]],'thumb_03_r':[0,0,x[4]]}
quats={n:Euler([math.radians(a) for a in degrees],'XYZ').to_quaternion() for n,degrees in rotations.items()}
sources=[(ROOT/'SourceAssets/AxeTwoHandPose20260919/H4/Axe_TwoHand_H4_Idle_Equip_Editable.blend',
          [('Idle',3.,150),('Equip',.48,150)],'Axe_ThumbFix_Idle_Equip_Editable.blend'),
         (ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/Axe_TwoHand_Attack_V5_Editable.blend',
          [('Swing',.68,300),('HitRecover',.44,300)],'Axe_ThumbFix_Attack_Editable.blend')]
report={'revision':'H4_V5_ThumbFix1','runtime_tested':False,'thumb_fit':FIT,'clips':{},'blends':[]}
for source,clips,blend_name in sources:
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version=0
    rig=bpy.data.objects['SK_Harvest_Axe_Rig'];scene=bpy.context.scene
    for clip,duration,fps in clips:
        name='A_Harvest_Axe_'+clip
        original=bpy.data.actions[name]
        original.name='REF_PreThumbFix_'+name;original.use_fake_user=True
        action=original.copy();action.name=name;action.use_fake_user=True
        rig.animation_data.action=action;rig.animation_data.action_slot=action.slots[0]
        scene.render.fps=fps;scene.render.fps_base=1
        scene.frame_start=0;scene.frame_end=round(duration*fps)
        for f in range(scene.frame_end+1):
            scene.frame_set(f)
            for n,q in quats.items():
                bone=rig.pose.bones[n]
                bone.rotation_mode='QUATERNION';bone.rotation_quaternion=q
                bone.keyframe_insert('rotation_quaternion',frame=f,group=n)
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        if any(n in curve.data_path for n in quats):
                            for key in curve.keyframe_points:key.interpolation='LINEAR'
        bpy.ops.object.select_all(action='DESELECT')
        rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
        path=OUT/'Export'/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},
                                axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,
                                bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
        report['clips'][clip]={'fbx':str(path),'fps':fps,'seconds':duration,'source':str(source)}
        print('AXE_THUMB_EXPORTED '+clip,flush=True)
    first,duration,fps=clips[0]
    rig.animation_data.action=bpy.data.actions['A_Harvest_Axe_'+first]
    rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    scene.render.fps=fps;scene.frame_end=round(duration*fps);scene.frame_set(0)
    bpy.ops.file.pack_all()
    blend=OUT/blend_name
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    report['blends'].append(str(blend))
(OUT/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
motion=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/motion.json').read_text(encoding='utf-8'))
motion['revision']=report['revision'];motion['thumb_rotation_parameters_deg']=x
(OUT/'motion.json').write_text(json.dumps(motion,indent=2),encoding='utf-8')
