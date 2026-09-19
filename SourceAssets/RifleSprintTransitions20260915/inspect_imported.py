"""Read saved UE clips at 240 Hz: compression, reverse track, loop and hand contact."""
import unreal as u, json, math
from pathlib import Path
O=Path(__file__).resolve().parent
report={};failures=[]
bones=['WPN_root','WPN_SOCKET_Muzzle','hand_r','hand_l','lowerarm_l','upperarm_l','index_03_l','thumb_03_l']
for weapon in ('M4','AKM','QBZ191'):
    spec=json.loads((O.parent/'RifleTacticalSprint20260915/sources.json').read_text())
    mesh=u.load_asset('/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416' if weapon=='M4' else spec[weapon]['mesh'])
    opt=u.AnimPoseEvaluationOptions();opt.optional_skeletal_mesh=mesh
    profiles=('Base','Drum','Angled','Vertical','Canted','Prism') if weapon=='M4' else ('Base','Angled','Vertical','Canted','Prism')
    for profile in profiles:
        root=f'/Game/Weapons/M4TacticalSprint20260915/{profile}' if weapon=='M4' else f'/Game/Weapons/RifleTacticalSprint20260915/{weapon}/{profile}'
        clips={kind:u.load_asset(f'{root}/A_{weapon}_TacticalSprint_{profile}_{kind}') for kind in ('Enter','Loop','Exit')}
        def get(clip,time,mode=u.AnimDataEvalType.COMPRESSED):
            opt.evaluation_type=mode
            # Compare the authored source with the actual compressed runtime
            # pose. Raw+retarget applies QBZ's legacy reference correction again;
            # disabling retarget on compressed would silently force raw in UE.
            opt.should_retarget=mode==u.AnimDataEvalType.COMPRESSED
            p=u.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opt)
            return {n:u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD) for n in bones}
        item={'compression_cm':0.,'reverse_cm':0.,'loop_cm':0.,'right_contact_cm':0.,'durations':{k:c.get_play_length() for k,c in clips.items()}}
        for kind,clip in clips.items():
            u.AKMAnimationAuditLibrary.finish_animation_compression(clip)
            length=clip.get_play_length();base=None
            for i in range(round(length*240)+1):
                t=i/240.;p=get(clip,t);raw=get(clip,t,u.AnimDataEvalType.RAW)
                for n in bones:item['compression_cm']=max(item['compression_cm'],p[n].translation.distance(raw[n].translation))
                contact=p['WPN_root'].inverse_transform_location(p['hand_r'].translation)
                if base is None:base=contact
                # Account for any source scale on the receiver.
                item['right_contact_cm']=max(item['right_contact_cm'],p['WPN_root'].transform_location(contact).distance(p['WPN_root'].transform_location(base)))
                if kind=='Enter':
                    q=get(clips['Exit'],clips['Exit'].get_play_length()*(1-t/length))
                    for n in bones:item['reverse_cm']=max(item['reverse_cm'],p[n].translation.distance(q[n].translation))
            if kind=='Loop':
                p=get(clip,0);q=get(clip,length)
                item['loop_cm']=max(p[n].translation.distance(q[n].translation) for n in bones)
        for metric in ('compression_cm','reverse_cm','loop_cm','right_contact_cm'):
            if not math.isfinite(item[metric]) or item[metric]>.10:failures.append(f'{weapon}:{profile} {metric}={item[metric]}')
        report[weapon+':'+profile]=item
        u.log('RIFLE_SPRINT_ASSET '+weapon+' '+profile+' '+str(item))
(O/'imported-continuity.json').write_text(json.dumps({'sample_rate':240,
    'reference':'RAW without retargeting (authored tracks); COMPRESSED with retargeting (runtime)',
    'profiles':report,'failures':failures},indent=2))
if failures:raise RuntimeError('\n'.join(failures))
u.log('RIFLE_SPRINT_ASSETS_COMPLETE profiles=16 failures=0')
