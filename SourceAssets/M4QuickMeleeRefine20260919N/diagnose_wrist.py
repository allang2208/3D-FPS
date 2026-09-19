import bpy, json, math
from pathlib import Path
from mathutils import Vector
P = Path(__file__).parent
S = P.parent
baseline = S.parent/'trash/quick-melee-retired-20260919/SourceAssets/M4QuickMeleeRefine20260919M/Base/M4_QuickCombat_Base_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(baseline))
rig=bpy.data.objects['SK_M4_Infima']; scene=bpy.context.scene
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
def angle(a,b): return math.degrees(a.angle(b))
records=[]
scene.frame_set(0)
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
restfore=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
idlefore=(idle['hand_r'].translation-idle['lowerarm_r'].translation).normalized()
for f in range(109):
    scene.frame_set(f); bpy.context.view_layer.update()
    pose={b.name:b.matrix.copy() for b in rig.pose.bones}
    sh,el,wr=[pose[n].translation for n in ('upperarm_r','lowerarm_r','hand_r')]
    upper=(el-sh).length; lower=(wr-el).length
    axis=(wr-sh).normalized(); d=(wr-sh).length
    desired=pose['hand_r'].to_quaternion() @ rest['hand_r'].to_quaternion().inverted() @ restfore
    desired_idle=pose['hand_r'].to_quaternion() @ idle['hand_r'].to_quaternion().inverted() @ idlefore
    along=(upper*upper-lower*lower+d*d)/(2*d)
    theta=math.acos(max(-1,min(1,(d-along)/lower)))
    minimum=abs(math.radians(angle(desired,axis))-theta)
    records.append({'frame':f,'bend_rest_deg':angle(wr-el,desired),'bend_idle_deg':angle(wr-el,desired_idle),
                    'best_fixed_shoulder_bend_deg':math.degrees(minimum),
                    'shoulder':list(sh),'elbow':list(el),'wrist':list(wr),'neutral_fore':list(desired),
                    'upper_m':upper,'lower_m':lower})
out={'samples':records,'objects':[{'name':o.name,'type':o.type,'hide_render':o.hide_render,'hidden':o.hide_get(),
     'armatures':[m.object.name for m in o.modifiers if m.type=='ARMATURE' and m.object]} for o in scene.objects],
     'rest':{n:{'position':list(rest[n].translation),'parent':rig.data.bones[n].parent.name if rig.data.bones[n].parent else None} for n in ('upperarm_r','lowerarm_r','hand_r','lowerarm_twist_01_r','lowerarm_twist_02_r')}}
(P/'diagnosis_M.json').write_text(json.dumps(out,indent=2))
for f in (0,8,12,16,20,24,32,48,72,88,104): print('WRIST_DIAG',records[f],flush=True)
print('SCENE_OBJECTS',out['objects'],flush=True)
