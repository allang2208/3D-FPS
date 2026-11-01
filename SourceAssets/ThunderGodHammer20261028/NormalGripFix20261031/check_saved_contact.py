"""User-requested focused check: saved sparse layer on compressed native poses."""
import ast,bisect,json,math
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
module=ast.parse((R/'SourceAssets/FrostSwordGrips20260919/author_long_grip_animation.py').read_text(encoding='utf-8'))
helpers={'add','sub','mul','dot','length','unit','cross','inverse','qmul','rotate','between','unpack','smooth'}
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'<grip_math>','exec'))
module=ast.parse((P/'author_contact.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'local','apply_point','inverse_point'}],type_ignores=[]),'<grip_transforms>','exec'))
def slerp(a,b,t):
    d=dot(a,b)
    if d<0:b=mul(b,-1);d=-d
    if d>.9995:return unit(add(mul(a,1-t),mul(b,t)))
    angle=math.acos(max(-1,min(1,d)));sn=math.sin(angle)
    return unit(add(mul(a,math.sin((1-t)*angle)/sn),mul(b,math.sin(t*angle)/sn)))
def key(v,i):
    o=i*10;return {'p':v[o:o+3],'q':unit(v[o+3:o+7]),'s':v[o+7:o+10]}
def sample(tr,t):
    times,values=tr;hi=bisect.bisect_right(times,t)
    if hi<=0:return key(values,0)
    if hi>=len(times):return key(values,len(times)-1)
    a,b=key(values,hi-1),key(values,hi);f=(t-times[hi-1])/(times[hi]-times[hi-1])
    return {'p':add(mul(a['p'],1-f),mul(b['p'],f)),'q':slerp(a['q'],b['q'],f),'s':add(mul(a['s'],1-f),mul(b['s'],f))}
def compose(a,b):return {'p':apply_point(b,a['p']),'q':unit(qmul(b['q'],a['q'])),'s':tuple(x*y for x,y in zip(a['s'],b['s']))}
mesh=u.load_asset('/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1')
c=u.SkeletalMeshComponent();c.set_skeletal_mesh_asset(mesh)
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.COMPRESSED;opt.optional_skeletal_mesh=mesh
asset=u.load_asset('/Game/Weapons/ThunderGodHammer20261028/NormalGripFix20261031/DA_ThunderHammer_ConductiveGrip')
anchor=json.loads((P/'contact_receipt.json').read_text())['anchor_hand_local'];centre=(-.00045,.00105)
report={'saved_asset':asset.get_path_name(),'clips':{},'gameplay_tested':False}
for clip in asset.get_editor_property('clips'):
    anim=clip.get_editor_property('base')
    if '/NormalComboV4/' not in anim.get_path_name():continue
    name=anim.get_name();duration=anim.get_play_length();frames=u.AnimationLibrary.get_num_frames(anim)
    tracks={str(tr.get_editor_property('bone')):(list(tr.get_editor_property('times')),list(tr.get_editor_property('values'))) for tr in clip.get_editor_property('tracks')}
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(u.AnimPoseExtensions.get_anim_pose_at_time(anim,0,opt))]
    parents={n:str(c.get_parent_bone(n)) for n in names}
    metrics={'samples':frames*4+1,'contact_before_mm':0.,'contact_after_mm':0.,'weapon_moved_cm':0.,'right_hand_moved_cm':0.,'bone_length_error_mm':0.,'free_hand_changed_mm':0.}
    for i in range(frames*4+1):
        t=duration*i/(frames*4);p=u.AnimPoseExtensions.get_anim_pose_at_time(anim,t,opt)
        src={n:unpack(u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)) for n in names}
        loc={n:local(src[n],src[parents[n]]) if parents[n] in src else src[n] for n in names}
        for n,tr in tracks.items():
            delta=sample(tr,t);a=loc[n];loc[n]={'p':add(a['p'],delta['p']),'q':unit(qmul(delta['q'],a['q'])),'s':add(a['s'],delta['s'])}
        out={}
        def rebuild(n):
            if n not in out:out[n]=compose(loc[n],rebuild(parents[n])) if parents[n] in src else loc[n]
            return out[n]
        for n in names:rebuild(n)
        before=inverse_point(src['WPN_root'],apply_point(src['hand_l'],anchor))
        after=inverse_point(out['WPN_root'],apply_point(out['hand_l'],anchor))
        wp=inverse_point(src['WPN_root'],src['hand_l']['p']);rad=math.hypot(wp[0]-centre[0],wp[1]-centre[1])
        swap=name=='A_Warhammer_Slash2' and t<.6
        if not swap or rad<=.071:
            metrics['contact_before_mm']=max(metrics['contact_before_mm'],math.hypot(before[0]-centre[0],before[1]-centre[1])*1000)
            metrics['contact_after_mm']=max(metrics['contact_after_mm'],math.hypot(after[0]-centre[0],after[1]-centre[1])*1000)
        elif rad>=.087:metrics['free_hand_changed_mm']=max(metrics['free_hand_changed_mm'],length(sub(src['hand_l']['p'],out['hand_l']['p']))*10)
        for n,k in [('WPN_root','weapon_moved_cm'),('hand_r','right_hand_moved_cm')]:metrics[k]=max(metrics[k],length(sub(src[n]['p'],out[n]['p'])))
        for a,b in [('upperarm_l','lowerarm_l'),('lowerarm_l','hand_l')]:
            metrics['bone_length_error_mm']=max(metrics['bone_length_error_mm'],abs(length(sub(src[b]['p'],src[a]['p']))-length(sub(out[b]['p'],out[a]['p'])))*10)
    report['clips'][name]=metrics
    print('SAVED_CONTACT_CHECK '+name+' '+json.dumps(metrics))
report['passed']=len(report['clips'])==6 and all(m['contact_after_mm']<.5 and m['weapon_moved_cm']<.0001 and m['right_hand_moved_cm']<.0001 and m['bone_length_error_mm']<.01 and m['free_hand_changed_mm']<.01 for m in report['clips'].values())
(P/'saved_contact_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
if not report['passed']:raise RuntimeError('Saved contact check outside tolerance; read report')
