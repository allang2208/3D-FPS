import unreal as u,json,math,os
from pathlib import Path
P=Path(__file__).resolve().parent;phase=os.environ.get('THUNDER_REVIEW_PHASE','before')
mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
names=['WPN_root','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r','thumb_01_r','index_01_r','index_02_r','middle_02_r']
rows={};errors=[]
def xyz(v):return [v.x,v.y,v.z]
def angle(a,b):return math.degrees(2*math.acos(min(1.,abs(sum(x*y for x,y in zip(a,b))))))
for name in ('A_ThunderHammer_RecallReady_V2','A_ThunderHammer_Catch_V2','A_ThunderHammer_ThrowCharge','A_ThunderHammer_ThrowRelease'):
    folder='ThunderThrowV1' if 'Throw' in name else 'RecallCatchV2'
    clip=u.load_asset('/Game/Weapons/ThunderGodHammer20261028/'+folder+'/'+name)
    if not clip:raise RuntimeError('Missing '+name)
    length=clip.get_play_length();sets={}
    for label,mode in [('source',u.AnimDataEvalType.SOURCE),('compressed',u.AnimDataEvalType.COMPRESSED)]:
        opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=mode;opt.optional_skeletal_mesh=mesh;frames=[]
        for i in range(round(length*240)+1):
            t=min(length,i/240);pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,t,opt);bones={}
            for bone in names:
                v=u.AnimPoseExtensions.get_bone_pose(pose,bone,u.AnimPoseSpaces.WORLD)
                q=v.rotation;bones[bone]={'p':xyz(v.translation),'q':[q.x,q.y,q.z,q.w]}
            frames.append(bones)
        sets[label]=frames
    drift=0.;rotation=0.;steps={bone:0. for bone in names}
    for i,(a,b) in enumerate(zip(sets['source'],sets['compressed'])):
        for bone in names:
            drift=max(drift,math.dist(a[bone]['p'],b[bone]['p']));rotation=max(rotation,angle(a[bone]['q'],b[bone]['q']))
            if i:steps[bone]=max(steps[bone],math.dist(b[bone]['p'],sets['compressed'][i-1][bone]['p']))
    rows[name]={'seconds':length,'same_skeleton':clip.get_editor_property('skeleton')==mesh.get_editor_property('skeleton'),'compression_position_cm':drift,'compression_angle_deg':rotation,'max_frame_step_cm':steps,'samples':sets}
    print('RECALL_NATIVE '+name+' '+json.dumps({k:v for k,v in rows[name].items() if k!='samples'}))
(P/(phase+'-native.json')).write_text(json.dumps(rows),encoding='utf-8')
