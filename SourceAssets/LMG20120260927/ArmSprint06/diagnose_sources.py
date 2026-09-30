"""Focused source diagnosis requested for the 201 forearm and sprint."""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;S=O.parent.parent
report={'sources':{},'scope':'201 left forearm deformation and sprint withdrawal; source data only'}
def assign(r,a):
 r.animation_data.action=a
 if a.slots:r.animation_data.action_slot=a.slots[0]
def sample(r):
 p={b.name:b.matrix.copy() for b in r.pose.bones};rest={b.name:b.matrix_local.copy() for b in r.data.bones};R=p['WPN_root']
 def angle(a,b):
  value=math.degrees(a.to_quaternion().rotation_difference(b.to_quaternion()).angle)
  return min(value,360-value)
 def dr(n):return p[n]@rest[n].inverted()
 sh,el,wr=[p[n+'_l'].translation for n in ['upperarm','lowerarm','hand']]
 return {'root_hand':list((R.inverted()@p['hand_l']).translation),'hand':list(wr),'elbow':list(el),'shoulder':list(sh),'reach_ratio':(wr-sh).length/((el-sh).length+(wr-el).length),
 'wrist_rest_deviation_degrees':angle(rest['lowerarm_l'].inverted()@rest['hand_l'],p['lowerarm_l'].inverted()@p['hand_l']),
 'helper_segment_deviation_degrees':{n:angle(dr(n),dr(n.split('_twist')[0]+'_l')) for n in p if n.endswith('_l') and '_twist_' in n},
 'matrices':{n:[list(row) for row in p[n]] for n in p if n.endswith('_l') or n=='WPN_root'}}
sources=[('AKM_idle',S/'AKMSoviet20260911/AKM_Soviet_Editable.blend','AKM_Native_idle',[0]),
 ('AKM_sprint',S/'RifleTacticalSprint20260915/AKM/Base/AKM_TacticalSprint_Base_Editable.blend','AKM_TacticalSprint_Base_Loop',[0,9,18,27,36])]
for revision in ['Charging04','Support05']:
 for kind in ['idle','sprint_enter','sprint_loop','sprint_exit']:
  sources.append((revision+'_'+kind,O.parent/revision/'Motions'/f'A_LMG201_{kind}.blend',None,[0] if kind=='idle' else None))
for label,path,action,frames in sources:
 bpy.ops.wm.open_mainfile(filepath=str(path),use_scripts=False);r=bpy.data.objects['SK_M4_Infima'];sc=bpy.context.scene
 if action:assign(r,bpy.data.actions[action])
 if frames is None:
  a,b=r.animation_data.action.frame_range;frames=[float(a+(b-a)*i/4) for i in range(5)]
 data={}
 for f in frames:
  sc.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update();data[str(f)]=sample(r)
 report['sources'][label]={'path':str(path),'samples':data}
 first=next(iter(data.values()));last=list(data.values())[-1]
 print(label,'helper_degrees',first['helper_segment_deviation_degrees'],'wrist',round(first['wrist_rest_deviation_degrees'],2),'hand_start_end',first['hand'],last['hand'],flush=True)
 if label=='Support05_idle':
  report['reference_rest']={b.name:[list(row) for row in b.matrix_local] for b in r.data.bones}
  report['parents']={b.name:b.parent.name if b.parent else None for b in r.data.bones}
(O/'source_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('201_ARM_SPRINT_SOURCE_DIAGNOSIS_SAVED',flush=True)
