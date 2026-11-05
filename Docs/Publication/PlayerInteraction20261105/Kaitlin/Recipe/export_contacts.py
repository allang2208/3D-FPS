import gzip,json,time
from pathlib import Path
import unreal as u
W=Path(__file__).resolve().parent
plan=json.loads((W/'plan.json').read_text())
diagnosis=json.loads((W/'contact_diagnosis.json').read_text())
selected={}
for row in diagnosis['clips']:
    roles=row['roles'];markers=row.get('markers',[])
    if roles[0].startswith('Warhammer.') or 'NativeSwordGrip' in markers or roles[0].startswith('Bow.'):
        selected[row['key']]=dict(plan[row['key']],kind='bow' if roles[0].startswith('Bow.') else 'pair')
(W/'selected.json').write_text(json.dumps(selected,indent=2))
names=['root','pelvis','spine_01','spine_02','spine_03','spine_04','spine_05']
for side in ('l','r'):
    names += [f'{n}_{side}' for n in ('clavicle','upperarm','lowerarm','hand','upperarm_twist_01','upperarm_twist_02','lowerarm_twist_01','lowerarm_twist_02')]
started=time.monotonic();written=0
for key,spec in selected.items():
    out=W/'Tracks'/(key+'.json.gz')
    if out.exists():continue
    result=dict(spec,names=names)
    target=u.load_asset(spec['target']);model=target.get_editor_property('data_model_interface')
    rate=model.get_frame_rate();count=model.get_number_of_keys()
    result.update(rate=[rate.numerator,rate.denominator],keys=count)
    if spec['kind']=='pair':
        for variant in ('source','target'):
            clip=u.load_asset(spec[variant]);frames=[]
            for i in range(count):
                poses=u.AnimationLibrary.get_bone_poses_for_time(clip,names,i*rate.denominator/rate.numerator,False)
                frames.append([[t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,t.scale3d.x,t.scale3d.y,t.scale3d.z] for t in poses])
            result[variant+'_frames']=frames
    else:
        curves=u.AnimationLibrary.get_animation_curve_names(target,u.RawCurveTrackTypes.RCT_FLOAT)
        result['curves']={str(n):[list(v) for v in u.AnimationLibrary.get_float_keys(target,n)] for n in curves if str(n).startswith('SparrowBow')}
    out.parent.mkdir(exist_ok=True)
    with gzip.open(out,'wt',encoding='utf-8') as f:json.dump(result,f,separators=(',',':'))
    written+=1
    if time.monotonic()-started>75:break
print('CONTACT_TRACKS',written,'remaining',sum(not (W/'Tracks'/(k+'.json.gz')).exists() for k in selected))
