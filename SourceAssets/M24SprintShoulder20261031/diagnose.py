from pathlib import Path
exec(compile((Path(__file__).parent/'setup.py').read_text(),'setup','exec'))
def mixed(a,b,w):
    out={}
    for n in names:
        p,q,sc=a[n].decompose();pp,qq,ss=b[n].decompose();out[n]=Matrix.LocRotScale(p.lerp(pp,w),q.slerp(qq,w),sc.lerp(ss,w))
    return out
def component(loc):
    out={}
    for n in names:out[n]=out[parents[n]]@loc[n] if parents[n] else loc[n]
    return out
def runtime(progress,phase,family='base',profiles=None):
    profiles=ue['profiles'] if profiles is None else profiles
    def local(role,t):
        clip,old=entry_for(family,role);entry=next(c for c in profiles[family] if c['base']==old['base'])
        return local_pose(clip,entry,t)[1]
    enter,_=entry_for(family,'sprint_enter');loop,_=entry_for(family,'sprint_loop')
    a=local('sprint_enter',progress*(enter['keys']-1)/30);b=local('sprint_loop',phase*(loop['keys']-1)/30)
    result=mixed(a,b,smooth(.65,1,progress));result=mixed(local('idle',0),result,smooth(0,.15,progress));return component(result)
def detailed(row):
    v=measures(row)['chain'];S,E,H=[row[n].translation for n in ('upperarm_l','lowerarm_l','hand_l')]
    v['reach_ratio']=(H-S).length/((E-S).length+(H-E).length)
    v['camera_cm']={n:list(C@row[n].translation) for n in ('upperarm_l','lowerarm_l','hand_l')}
    v['twist_degrees']={}
    for j in (1,2):
        n=f'lowerarm_twist_{j:02d}_l';q=(row['lowerarm_l'].inverted()@row[n]).to_quaternion()@local_rest[n].to_quaternion().inverted();v['twist_degrees'][n]=math.degrees(q.angle)
    return v
if __name__=='__main__':
    out={};folder=O/'BeforeViews';folder.mkdir(exist_ok=True)
    for family in ('base','mag10'):
        out[family]={}
        for p,phase in ((0,0),(.15,0),(.3,0),(.5,0),(.65,0),(1,0),(1,.25),(1,.5),(1,.75),(1,1)):
            row=runtime(p,phase,family);key=f'{p:.2f}_{phase:.2f}';out[family][key]=detailed(row)
            if family=='base' and (p in (0,.3,.65) or p==1 and phase in (0,.5)):view(row,folder/(key+'.png'))
    (O/'diagnosis.json').write_text(json.dumps(out,indent=2));print('SPRINT_DIAGNOSIS',json.dumps({k:{kk:{n:vv[n] for n in ('reach_ratio','elbow_bend','wrist_axis_bend','upper_len_cm','fore_len_cm','twist_degrees')} for kk,vv in v.items()} for k,v in out.items()}),flush=True)
