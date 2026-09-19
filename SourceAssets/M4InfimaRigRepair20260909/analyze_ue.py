import json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
OUT=Path(__file__).resolve().parent
data=json.loads((OUT/'ue_pose_validation.json').read_text())
def matrix(t):return Matrix.LocRotScale(Vector(t['p']),Quaternion(t['q']),Vector(t['s']))
report={}
for folder,item in data.items():
    report[folder]={}
    for clip,record in item['clips'].items():
        samples=record['compressed'];start=samples[0]
        rigid=['WPN_Trigger','WPN_RearSight','WPN_FrontSight','WPN_bolt']
        baseline={n:matrix(start['WPN_root']).inverted()@matrix(start[n]) for n in rigid}
        drifts={n:0 for n in rigid};compression={n:0 for n in start}
        max_trigger_angle=0
        for raw,d in zip(record['raw'],samples):
            for n in rigid:
                rel=matrix(d['WPN_root']).inverted()@matrix(d[n])
                # Relative coordinates inherit the FBX root's 100x scale.
                # Convert the delta back to component space before reporting cm.
                delta_cm=matrix(d['WPN_root']).to_3x3()@(rel.translation-baseline[n].translation)
                drifts[n]=max(drifts[n],delta_cm.length)
                if n=='WPN_Trigger':
                    angle=baseline[n].to_quaternion().rotation_difference(rel.to_quaternion()).angle
                    max_trigger_angle=max(max_trigger_angle,math.degrees(min(angle,2*math.pi-angle)))
            for n in d:compression[n]=max(compression[n],(Vector(d[n]['p'])-Vector(raw[n]['p'])).length)
        report[folder][clip]={'samples':len(samples),'rigid_bone_drift_cm':drifts,'raw_vs_compressed_max_position_error_cm':compression,'trigger_rotation_degrees':max_trigger_angle}
(OUT/'ue_validation_summary.json').write_text(json.dumps(report,indent=2))
for folder,clips in report.items():
    print(folder,json.dumps({key:{'drift_cm':r['rigid_bone_drift_cm'],'compression_error_cm':max(r['raw_vs_compressed_max_position_error_cm'].values())} for key,r in clips.items()}))
fixed=report['M4InfimaRigV4']
for key,item in fixed.items():
    for bone in ['WPN_Trigger','WPN_RearSight','WPN_FrontSight']:
        assert item['rigid_bone_drift_cm'][bone]<.002,(key,bone,item)
    assert max(item['raw_vs_compressed_max_position_error_cm'].values())<.05,(key,item)
assert fixed['fire']['trigger_rotation_degrees']>20,fixed['fire']
print('M4_RIG_COMPRESSED_VALIDATION_PASS')
