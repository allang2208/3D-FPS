"""Read joint frames and full source motion for authoring the new candidate."""
import bpy,json,math
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchFoundation20260920')
report={}
names=['root','pelvis','spine_01','spine_02','spine_03','spine_04','spine_05','neck_01','head','clavicle_l','upperarm_l','lowerarm_l','hand_l','index_01_l','index_02_l','middle_01_l','thumb_01_l','thigh_l','calf_l','foot_l','ball_l','foot_r','ball_r']
for role in ['Quinn','Walk','Idle']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/'Sources'/(role+'.fbx')))
    rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    bones={n:{'head':list(rig.matrix_world@rig.data.bones[n].head_local),'tail':list(rig.matrix_world@rig.data.bones[n].tail_local),
              'matrix':[list(row) for row in rig.matrix_world@rig.data.bones[n].matrix_local]} for n in names if n in rig.data.bones}
    scene=bpy.context.scene
    item={'bones':len(rig.data.bones),'names':list(rig.data.bones.keys()),'rest':bones,'rig_matrix':[list(row) for row in rig.matrix_world],
          'frame_start':scene.frame_start,'frame_end':scene.frame_end,'fps':scene.render.fps,'objects':[(o.name,o.type) for o in scene.objects]}
    if role!='Quinn':
        samples=[]
        for f in range(scene.frame_start,scene.frame_end+1):
            scene.frame_set(f)
            samples.append({'frame':f,'bones':{n:list((rig.matrix_world@rig.pose.bones[n].matrix).translation) for n in names if n in rig.pose.bones}})
        item['motion']=samples
    report[role]=item
(ROOT/'source_frames.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({role:{'bones':v['bones'],'fps':v['fps'],'start':v['frame_start'],'end':v['frame_end'],'objects':v['objects'],
    'positions':{n:d['head'] for n,d in v['rest'].items()}} for role,v in report.items()}),flush=True)
