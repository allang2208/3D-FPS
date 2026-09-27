"""Requested guard inspection only: native saved curves and pose boundaries."""
import unreal as u,json,math
from pathlib import Path
P=Path(__file__).parent
mesh=u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE;options.optional_skeletal_mesh=mesh
def pack(t):
    p=t.translation;q=t.rotation;s=t.scale3d
    return {'p':[p.x,p.y,p.z],'q':[q.w,q.x,q.y,q.z],'s':[s.x,s.y,s.z]}
def errors(a,b):
    pos=math.sqrt(sum((x-y)**2 for x,y in zip(a['p'],b['p'])))
    dot=abs(sum(x*y for x,y in zip(a['q'],b['q'])))
    lengths=math.sqrt(sum(x*x for x in a['q'])*sum(x*x for x in b['q']))
    return pos,math.degrees(2*math.acos(min(1,dot/lengths)))
report={'runtime_tested':False,'assets':[],'boundaries':{}}
for variant in ('Standard','LongGrip'):
    data=json.loads((P/'Before'/variant/'installed.json').read_text());result={'variant':variant,'parents':data['parents'],'clips':{}}
    for clip in ('Idle','Guard','GuardHit','GuardBreak'):
        info=data['clips'][clip];asset=u.load_asset(info['asset']);count=asset.get_editor_property('data_model_interface').get_number_of_frames();duration=asset.get_play_length()
        patch=json.loads((P/'Final'/variant/(clip+'_patch.json')).read_text()) if clip!='Idle' else None
        samples=[];maxp=maxq=0.
        for i in range(count+1 if patch else 1):
            t=i*duration/count;pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,t,options)
            world={n:pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in data['parents']}
            samples.append({'seconds':t,'world':world})
            if patch:
                for n in patch['edited_bones']:
                    actual=pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL))
                    pe,qe=errors(actual,patch['samples'][i]['bones'][n]);maxp=max(maxp,pe);maxq=max(maxq,qe)
        result['clips'][clip]={'asset':info['asset'],'intervals':count,'seconds':duration,'samples':samples}
        if patch:
            report['assets'].append({'variant':variant,'clip':clip,'max_native_local_position_error_cm':maxp,'max_native_local_rotation_error_deg':maxq,'intervals':count,'seconds':duration})
            if maxp>.01 or maxq>.05:raise RuntimeError('Saved native curve mismatch '+variant+'/'+clip)
    c=result['clips'];links=[('raise_from_idle',c['Idle']['samples'][0],c['Guard']['samples'][0]),
        ('hit_entry',c['Guard']['samples'][-1],c['GuardHit']['samples'][0]),('hit_recover',c['Guard']['samples'][-1],c['GuardHit']['samples'][-1]),
        ('break_entry',c['Guard']['samples'][-1],c['GuardBreak']['samples'][0]),('break_to_idle',c['Idle']['samples'][0],c['GuardBreak']['samples'][-1])]
    report['boundaries'][variant]={}
    for label,a,b in links:
        es=[errors(a['world'][n],b['world'][n]) for n in data['parents']]
        report['boundaries'][variant][label]={'max_position_cm':max(e[0] for e in es),'max_rotation_deg':max(e[1] for e in es)}
    out=P/'After'/variant;out.mkdir(parents=True,exist_ok=True);(out/'installed.json').write_text(json.dumps(result,separators=(',',':')))
(P/'native_inspection.json').write_text(json.dumps(report,indent=2))
print('GUARD_NATIVE_INSPECTION_SAVED',flush=True)
