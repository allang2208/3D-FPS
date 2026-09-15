"""Read-only UE pose sampling for the user-requested sprint smoothness diagnosis.

Run as a Python commandlet with -DualSprintRevision=SprintReferenceV4 or SprintSmoothV5.
Samples all six sprint clips at 240 Hz, including between the imported 120 Hz keys.
"""
import json, math, re
from pathlib import Path
import unreal as u

O=Path(__file__).parent
match=re.search(r'-DualSprintRevision=(\w+)',u.SystemLibrary.get_command_line())
revision=match.group(1) if match else 'SprintSmoothV5'
hz=240
report={'revision':revision,'sample_rate':hz,'clips':{}}

def xyz(v):return [v.x,v.y,v.z]
def quat(q):return [q.x,q.y,q.z,q.w]
def distance(a,b):return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def angle(a,b):
    dot=abs(sum(x*y for x,y in zip(a,b)))/math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return math.degrees(2*math.acos(min(1.,dot)))
def movement_metrics(points):
    # Periodic finite differences include the loop boundary exactly once.
    loop=points[:-1];n=len(loop)
    velocity=[[hz*(loop[(i+1)%n][j]-loop[i][j]) for j in range(3)] for i in range(n)]
    acceleration=[[hz*(velocity[(i+1)%n][j]-velocity[i][j]) for j in range(3)] for i in range(n)]
    speeds=[math.sqrt(sum(v*v for v in row)) for row in velocity]
    accels=[math.sqrt(sum(v*v for v in row)) for row in acceleration]
    return {'loop_gap_cm':distance(points[0],points[-1]),'max_speed_cm_per_source_second':max(speeds),
            'rms_acceleration_cm_per_source_second2':math.sqrt(sum(a*a for a in accels)/n),
            'max_acceleration_cm_per_source_second2':max(accels),
            'near_stationary_fraction':sum(s<max(speeds)*.05 for s in speeds)/n,
            'identical_adjacent_samples':sum(s<1.e-5 for s in speeds)}

for family in ('M1911','DW715'):
    for side in ('r','l'):
        base=f'/Game/Weapons/PistolDualWield20260914/{family}/{side}'
        mesh=u.load_asset(base+f'/SK_Dual_{family}_{side}')
        options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh
        bones=['WPN_root','WPN_SOCKET_Muzzle','WPN_FrontSight','WPN_RearSight',
               'upperarm_'+side,'lowerarm_'+side,'hand_'+side,'index_03_'+side,'lowerarm_twist_01_'+side]
        for kind in (('sprint','sprint_empty') if family=='M1911' else ('sprint',)):
            path=base+f'/{revision}/Animations/A_Dual_{family}_{side}_{kind}'
            clip=u.load_asset(path)
            if not clip:raise RuntimeError('Missing sprint clip '+path)
            length=clip.get_play_length();samples=[];error=0.;angular_error=0.;contact=[];lengths=[]
            for i in range(round(length*hz)+1):
                t=i/hz;poses=[]
                for mode in (u.AnimDataEvalType.RAW,u.AnimDataEvalType.COMPRESSED):
                    options.evaluation_type=mode
                    pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,options)
                    poses.append({n:u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD) for n in bones})
                raw,compressed=poses
                for n in bones:
                    error=max(error,raw[n].translation.distance(compressed[n].translation))
                    angular_error=max(angular_error,angle(quat(raw[n].rotation),quat(compressed[n].rotation)))
                samples.append({n:{'p':xyz(v.translation),'q':quat(v.rotation)} for n,v in compressed.items()})
                contact.append(xyz(compressed['WPN_root'].inverse_transform_location(compressed['hand_'+side].translation)))
                lengths.append([compressed['upperarm_'+side].translation.distance(compressed['lowerarm_'+side].translation),
                                compressed['lowerarm_'+side].translation.distance(compressed['hand_'+side].translation)])
            item={'asset':path,'duration':length,'interpolation':str(clip.get_editor_property('interpolation')),
                  'sampled_keys':clip.get_editor_property('number_of_sampled_keys'),
                  'compression_error_cm':error,'compression_error_degrees':angular_error,
                  'hand_to_gun_drift_local_cm':max(distance(contact[0],p) for p in contact),
                  'arm_length_range_cm':[max(row[j] for row in lengths)-min(row[j] for row in lengths) for j in range(2)],
                  'motion':{n:movement_metrics([row[n]['p'] for row in samples]) for n in bones},
                  'max_frame_rotation_degrees':{n:max(angle(samples[i][n]['q'],samples[i+1][n]['q']) for i in range(len(samples)-1)) for n in bones},
                  'samples':samples}
            report['clips'][f'{family}_{side}_{kind}']=item
            u.log('SPRINT_POSE_SAMPLE '+family+' '+side+' '+kind+' '+str(item['motion']['WPN_SOCKET_Muzzle']))
(O/f'pose-samples-{revision}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('SPRINT_POSE_SAMPLE_COMPLETE '+revision)
