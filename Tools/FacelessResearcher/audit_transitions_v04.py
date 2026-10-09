"""Measure existing clip-end to clip-start pose changes, without saving assets."""
import bpy,json
import numpy as np
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V04')
source=json.loads((ROOT/'waist_source.json').read_text(encoding='utf-8'))
bones=['head','pelvis','hand_l','hand_r','foot_l','foot_r']
poses={}
for role,entry in source['clips'].items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=entry['file'],use_anim=True)
    donor=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    first=int(donor.animation_data.action.frame_range[0]);fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    poses[role]={}
    for label,frame in [('first',first),('last',first+round(entry['duration']*fps))]:
        bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
        poses[role][label]={n:np.array((donor.matrix_world@donor.pose.bones[n].matrix).translation) for n in bones}
report={}
for old,new in [('attack','idle'),('attack','walk'),('hit','idle'),('walk','walk'),('idle','idle')]:
    report[old+'_to_'+new]={n:float(np.linalg.norm(poses[old]['last'][n]-poses[new]['first'][n])*100) for n in bones}
(ROOT/'Review20261009/transitions_cm.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M05_CLIP_BOUNDARY_REVIEW '+json.dumps(report),flush=True)
