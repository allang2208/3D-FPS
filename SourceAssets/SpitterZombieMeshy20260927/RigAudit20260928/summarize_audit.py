import json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'blender_read.json').read_text());ue=json.loads((ROOT/'ue_read.json').read_text())
def angle(a,b):
    dot=abs(sum(x*y for x,y in zip(a,b)))/math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return math.degrees(2*math.acos(min(1,dot)))
def dist(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def excursion(row,name):
    qs=[f['bones'][name]['q'] for f in row['frames']]
    return max(angle(qs[0],q) for q in qs)
summary={'metric_definition':'Maximum quaternion angular displacement from first sample; 61 phase samples; not Euler peak-to-peak. Local arm entries are relative to parent, others component-space.',
         'motion':{},'compression':{},'speed_ratios_at_configured_130cm_s':{},'loop':{},'local_arm_motion':{}}
for label,row in data['motion'].items():
    if label.startswith('authored_'):continue
    names=['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r'] if label.startswith('source_') else ['LeftArm','LeftForeArm','LeftHand','RightArm','RightForeArm','RightHand']
    summary['local_arm_motion'][label]={n:max(angle(row['frames'][0]['bones'][n]['local_q'],f['bones'][n]['local_q']) for f in row['frames']) for n in names}
for role,speed in zip(['Walk_A','Walk_B','Walk_C','Run_A'],ue['speeds_cm_s']):
    result={}
    for stage,hip,head,spine,arm in [('source','pelvis','head','spine_05','upperarm_l'),('native','Hips','Head','Spine','LeftArm'),('fbx','Hips','Head','Spine','LeftArm')]:
        row=data['motion'][stage+'_'+role]
        zs=[f['bones'][hip]['p'][2] for f in row['frames']]
        result[stage]=dict(pelvis_deg=excursion(row,hip),head_deg=excursion(row,head),
          upper_spine_deg=excursion(row,spine),left_upper_arm_deg=excursion(row,arm),hip_height_range_cm=(max(zs)-min(zs))*100)
    summary['motion'][role]=result
    summary['speed_ratios_at_configured_130cm_s'][role]=ue['walk_speed_cm_s']/speed
    rows=data['motion']['fbx_'+role]['frames'];names=rows[0]['bones'];duration=ue['poses']['A_Spitter_LibraryV7_'+role]['length'];dt=duration/(len(rows)-1)
    summary['loop'][role]={n:dict(first_last_deg=angle(rows[0]['bones'][n]['q'],rows[-1]['bones'][n]['q']),
        max_rotation_speed_deg_s=max(angle(a['bones'][n]['q'],b['bones'][n]['q'])/dt for a,b in zip(rows,rows[1:])),
        final_interval_rotation_speed_deg_s=angle(rows[-2]['bones'][n]['q'],rows[-1]['bones'][n]['q'])/dt) for n in ['Hips','Head','LeftArm','LeftForeArm','LeftLeg','RightLeg']}
for key,entry in ue['poses'].items():
    angles=[];positions=[]
    for a,b in zip(entry['modes']['SOURCE'],entry['modes']['COMPRESSED']):
        for n,x in a['bones'].items():
            y=b['bones'][n];angles.append(angle(x['local_q'],y['local_q']))
            positions.append(dist(x['component_pos_cm'],y['component_pos_cm']))
    summary['compression'][key]=dict(max_local_rotation_deg=max(angles),max_component_position_cm=max(positions))
(ROOT/'summary_metrics.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='loop'},indent=2))
