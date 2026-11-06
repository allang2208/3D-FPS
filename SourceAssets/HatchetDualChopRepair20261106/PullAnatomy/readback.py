"""Read the four saved third-person pull clips, no asset writes."""
import json,math,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;TASK=P.parent;ROOT=TASK.parents[1]
saved=json.loads((P/'saved-assets.json').read_text());A=u.AnimPoseExtensions
def pack(t):return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z]
def angle(a,b):
    dot=abs(sum(x*y for x,y in zip(a,b)))/math.sqrt(sum(x*x for x in a)*sum(x*x for x in b))
    return math.degrees(2*math.acos(min(1.,dot)))
def expected(frames,seconds,bone):
    f=min(seconds*60,len(frames)-1);i=int(f);alpha=f-i;a=frames[i][bone];b=frames[min(i+1,len(frames)-1)][bone]
    out=[x*(1-alpha)+y*alpha for x,y in zip(a,b)]
    sign=-1 if sum(x*y for x,y in zip(a[3:7],b[3:7]))<0 else 1
    q=[x*(1-alpha)+sign*y*alpha for x,y in zip(a[3:7],b[3:7])];norm=math.sqrt(sum(x*x for x in q))
    out[3:7]=[x/norm for x in q];return out
result={};render={}
for label in ('Jason','Kaitlin'):
    data=json.loads((P/(label+'-moves.json')).read_text());mesh=u.load_asset(data['mesh']);result[label]={}
    options=u.AnimPoseEvaluationOptions();options.optional_skeletal_mesh=mesh;options.evaluation_type=u.AnimDataEvalType.COMPRESSED
    render[label]=dict(names=data['names'],frames=[],labels=[])
    for role,info in saved[label].items():
        clip=u.load_asset(info['asset']);frames=data['clips'][role]
        # PostLoad can leave compression in flight; the first compressed pose
        # then contains placeholder/reference translations. Wait through the
        # engine's read-only completion command before sampling this asset.
        u.SystemLibrary.execute_console_command(None,'Editor.AsyncAssetCompilationFinishAll')
        bones=info['changed_tracks']+[k+'_'+s for s in ('r','l') for k in ('upperarm','lowerarm','hand')]
        ids={n:data['names'].index(n) for n in bones};maxpos=maxrot=step=0.;last={};worst={}
        for i in range(round(clip.get_play_length()*120)+1):
            t=min(i/120,clip.get_play_length());pose=A.get_anim_pose_at_time(clip,t,options)
            for n in bones:
                value=pack(A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL));goal=expected(frames,t,ids[n])
                distance=math.dist(value[:3],goal[:3])
                if distance>maxpos:worst=dict(bone=n,time=t,actual=value[:3],expected=goal[:3])
                maxpos=max(maxpos,distance);maxrot=max(maxrot,angle(value[3:7],goal[3:7]))
                if n in last:step=max(step,angle(value[3:7],last[n][3:7]))
                last[n]=value
        result[label][role]=dict(samples=round(clip.get_play_length()*120)+1,max_compression_translation_cm=maxpos,max_compression_rotation_deg=maxrot,max_120hz_rotation_step_deg=step,worst_translation=worst)
        times=[.65,.70,.75,.82,1.,1.13,1.30,1.48]
        for t in times:
            pose=A.get_anim_pose_at_time(clip,min(t,clip.get_play_length()),options)
            render[label]['frames'].append([pack(A.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)) for n in data['names']])
            render[label]['labels'].append(role+'_'+f'{t:.2f}')
fp=json.loads((TASK/'RollbackFirstPerson/asset-restoration.json').read_text('utf-8-sig'))
result['first_person_original_files_unchanged']=all(hashlib.sha256((ROOT/'Content'/(r['asset'].removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest().upper()==r['restored_sha256'].upper() for r in fp['restored'])
(P/'saved-readback.json').write_text(json.dumps(result,indent=2),'utf8')
(P/'saved-render-poses.json').write_text(json.dumps(render,separators=(',',':')),'utf8')
if not result['first_person_original_files_unchanged']:raise RuntimeError('First-person original files differ')
if any(v['max_compression_translation_cm']>.1 or v['max_compression_rotation_deg']>1. for who in ('Jason','Kaitlin') for v in result[who].values()):raise RuntimeError('Saved motion differs excessively from authored helper motion')
u.log('THIRD_PERSON_PULL_READBACK_COMPLETE assets=4 first_person_originals_unchanged')
