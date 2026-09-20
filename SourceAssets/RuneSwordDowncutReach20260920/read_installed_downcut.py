"""User-requested diagnosis of the saved overhead pose, including compression."""
import unreal as u,json,math
from pathlib import Path
P=Path(__file__).parent
def vec(v):return (v.x,v.y,v.z)
def quat(q):return (q.w,q.x,q.y,q.z)
def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def dist(a,b):return math.sqrt(dot(sub(a,b),sub(a,b)))
def angle(a,b):return math.degrees(math.acos(max(-1.,min(1.,dot(a,b)/math.sqrt(dot(a,a)*dot(b,b))))))
def qangle(a,b):return math.degrees(2.*math.acos(min(1.,abs(dot(a,b))/math.sqrt(dot(a,a)*dot(b,b)))))
def relative_point(w,p):
    q=w['q'];v=sub(p,w['p']);xyz=(-q[1],-q[2],-q[3])
    def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    t=tuple(2*x for x in cross(xyz,v));c=cross(xyz,t)
    return tuple(v[i]+q[0]*t[i]+c[i] for i in range(3))
def unpack(x):return {'p':vec(x.translation),'q':quat(x.rotation)}
report={'scope':'Two saved Overhead clips only; source/compressed bone poses','PIE_started':False,'variants':{}}
for variant in ('Standard','LongGrip'):
    original=json.loads((P/(variant+'_input.json')).read_text());patch=json.loads((P/variant/'Overhead_patch.json').read_text())
    asset=u.load_asset(patch['asset']);mesh=u.load_asset(original['mesh']);metrics={'revision':u.EditorAssetLibrary.get_metadata_tag(asset,'SwordElbow.Revision'),
        'seconds':asset.get_play_length(),'frames':u.AnimationLibrary.get_num_frames(asset),'source_local_position_error':0.,'source_local_rotation_error_deg':0.,
        'compressed_world_position_error_cm':0.,'max_grip_position_error_cm':0.,'max_hand_rotation_error_deg':0.,
        'max_segment_length_error_cm':0.,'endpoint_error_cm':0.,'min_downcut_angle_deg':{'l':180.,'r':180.},'samples':[]}
    fingers=[n for n in original['parents'] if n.startswith(('index','middle','ring','pinky','thumb'))]
    joints=['upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','WPN_root']
    for i,row in enumerate(original['samples']):
        t=row['seconds'];old=row['world'];expected=patch['samples'][i]['bones']
        opts=u.AnimPoseEvaluationOptions();opts.optional_skeletal_mesh=mesh;opts.evaluation_type=u.AnimDataEvalType.SOURCE
        source=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,opts)
        opts.evaluation_type=u.AnimDataEvalType.COMPRESSED
        compressed=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,opts)
        world={n:unpack(u.AnimPoseExtensions.get_bone_pose(source,n,u.AnimPoseSpaces.WORLD)) for n in joints+fingers}
        packed={n:unpack(u.AnimPoseExtensions.get_bone_pose(compressed,n,u.AnimPoseSpaces.WORLD)) for n in joints}
        for n in patch['edited_bones']:
            local=u.AnimPoseExtensions.get_bone_pose(source,n,u.AnimPoseSpaces.LOCAL)
            metrics['source_local_position_error']=max(metrics['source_local_position_error'],dist(vec(local.translation),expected[n]['p']))
            metrics['source_local_rotation_error_deg']=max(metrics['source_local_rotation_error_deg'],qangle(quat(local.rotation),expected[n]['q']))
        for n in joints:
            metrics['compressed_world_position_error_cm']=max(metrics['compressed_world_position_error_cm'],dist(world[n]['p'],packed[n]['p']))
            if i in (0,original['intervals']):metrics['endpoint_error_cm']=max(metrics['endpoint_error_cm'],dist(world[n]['p'],old[n]['p']))
        for n in ['hand_l','hand_r']+fingers:
            metrics['max_grip_position_error_cm']=max(metrics['max_grip_position_error_cm'],dist(relative_point(world['WPN_root'],world[n]['p']),relative_point(old['WPN_root'],old[n]['p'])))
        row_metric={'seconds':t,'sides':{}}
        for side in ('l','r'):
            a,e,h=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
            value=angle(sub(packed[a]['p'],packed[e]['p']),sub(packed[h]['p'],packed[e]['p']))
            row_metric['sides'][side]=value
            if 1.11<=t<=1.50:metrics['min_downcut_angle_deg'][side]=min(metrics['min_downcut_angle_deg'][side],value)
            metrics['max_hand_rotation_error_deg']=max(metrics['max_hand_rotation_error_deg'],qangle(world[h]['q'],old[h]['q']))
            for x,y in ((a,e),(e,h)):
                metrics['max_segment_length_error_cm']=max(metrics['max_segment_length_error_cm'],abs(dist(world[x]['p'],world[y]['p'])-dist(old[x]['p'],old[y]['p'])))
        if 1.10<=t<=1.51:metrics['samples'].append(row_metric)
    report['variants'][variant]=metrics
    u.log('DOWNCUT_SAVED_POSE '+variant+' '+str({k:v for k,v in metrics.items() if k!='samples'}))
(P/'installed_downcut_diagnosis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
