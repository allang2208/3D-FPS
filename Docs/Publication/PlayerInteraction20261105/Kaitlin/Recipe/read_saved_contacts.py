"""Read back the saved revisions for this requested weapon-contact investigation."""
import gzip,json
from pathlib import Path
import unreal as u
W=Path(__file__).resolve().parent
saved=json.loads((W/'saved_assets.json').read_text())
plan=json.loads((W/'selected.json').read_text())
result={}
opt=u.AnimPoseEvaluationOptions()
opt.evaluation_type=u.AnimDataEvalType.COMPRESSED
opt.should_retarget=True
for key,row in saved.items():
    clip=u.load_asset(row['asset'])
    source=u.load_asset(row['male'])
    model=clip.get_editor_property('data_model_interface')
    rate=model.get_frame_rate()
    old=u.load_asset(row['previous'])
    markers=lambda a:sorted((str(m.marker_name),round(m.time,6)) for m in u.AnimationLibrary.get_animation_sync_markers(a))
    entry={'keys':model.get_number_of_keys(),'rate':[rate.numerator,rate.denominator],
           'markers_preserved':markers(clip)==markers(old),'samples':[]}
    if plan[key]['kind']=='pair':
        for fraction in (0.,.125,.25,.375,.5,.625,.75,.875,1.):
            at=fraction*clip.get_play_length()
            pose=u.AnimPoseExtensions.get_anim_pose_at_time(clip,at,opt)
            joints=[]
            for side in ('r','l'):
                t=u.AnimPoseExtensions.get_bone_pose(pose,'hand_'+side,u.AnimPoseSpaces.WORLD)
                joints.append([t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w])
            entry['samples'].append({'time':at,'hands':joints})
    else:
        with gzip.open(W/'Authored'/(key+'.json.gz'),'rt',encoding='utf-8') as f:authored=json.load(f)
        entry['curves']={n:[list(x) for x in u.AnimationLibrary.get_float_keys(clip,n)] for n in authored['curves']}
    result[key]=entry
(W/'saved_readback.json').write_text(json.dumps(result),encoding='utf-8')
print('SAVED_CONTACT_READBACK',len(result))
