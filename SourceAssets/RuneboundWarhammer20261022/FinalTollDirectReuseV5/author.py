"""Splice COMPLETE existing native performances; never rotate their roots.

FPS: current Slash1 release -> brief pose-matched bridge -> current Uppercut.
Bodies: their own current native Slash1/Uppercut, plus matching charge takes.
Source extraction and transition matching are authoring, not runtime tests.
"""
from pathlib import Path
import json,math
import unreal as u
P=Path(__file__).resolve().parent
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
DEST='/Game/Weapons/RuneboundWarhammer20261022/FinalTollDirectReuseV5'
spec=json.loads((P/'inputs.json').read_text('utf-8'))
opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.SOURCE
receipt={'complete':False,'policy':'Full source local transforms; no root transport, IK, mirroring or wrist edits',
    'tested':False,'rendered':False,'contacts':[.10,.42],'saved':[],'sources':spec,
    'author_project':str(Path(u.Paths.project_dir()).resolve())}
def pose(a,t):return u.AnimPoseExtensions.get_anim_pose_at_time(a,max(0.,min(t,a.get_play_length())),opts)
def local(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.LOCAL)
def world(p,n):return u.AnimPoseExtensions.get_bone_pose(p,n,u.AnimPoseSpaces.WORLD)
def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)
def qmix(a,b,w):
    av=[a.x,a.y,a.z,a.w];bv=[b.x,b.y,b.z,b.w];dot=sum(x*y for x,y in zip(av,bv))
    if dot<0:bv=[-x for x in bv];dot=-dot
    if dot>.9995:v=[x+(y-x)*w for x,y in zip(av,bv)]
    else:
        angle=math.acos(max(-1.,min(1.,dot)));den=math.sin(angle)
        v=[(x*math.sin((1-w)*angle)+y*math.sin(w*angle))/den for x,y in zip(av,bv)]
    norm=math.sqrt(sum(x*x for x in v));return u.Quat(*[x/norm for x in v])
def vmix(a,b,w):return u.Vector(a.x+(b.x-a.x)*w,a.y+(b.y-a.y)*w,a.z+(b.z-a.z)*w)
def mix(a,b,w):return (vmix(a.translation,b.translation,w),qmix(a.rotation,b.rotation,w),vmix(a.scale3d,b.scale3d,w))
def marker(a,key,fallback):
    return next((m.time for m in u.AnimationLibrary.get_animation_sync_markers(a) if str(m.marker_name)==key),fallback)
def hermite(t,a,b,x,y,vx,vy):
    d=b-a;w=max(0.,min(1.,(t-a)/d))
    return (2*w**3-3*w*w+1)*x+(w**3-2*w*w+w)*d*vx+(-2*w**3+3*w*w)*y+(w**3-w*w)*d*vy
def upper_source(t):
    # Reuse the existing uppercut's actual skill clock, compressed to the two
    # combo contacts. Its source contact is 1.05, NOT the follow pose at 1.125.
    if t<=.42:
        p=1.+(t-.24)*.28/.18
        if p<1.225:return hermite(p,1.,1.225,1.,1.008,0.,.10)
        return hermite(p,1.225,1.28,1.008,1.05,.10,1.5)
    if t<=.54:return hermite(t,.42,.54,1.05,1.125,.075/.12,.075/.12)
    return 1.125+(2.05-1.125)*smooth((t-.54)/(.71))
def match_follow(normal,upper,nstart,nend,utime,names):
    # Choose the closest existing post-contact posture, retaining both donors'
    # absolute orientation. Never align either stroke by rotating the rig.
    p=pose(upper,utime);best=None
    for i in range(21):
        t=nstart+(nend-nstart)*i/20;q=pose(normal,t);cost=0.
        for n in names:
            a,b=world(p,n),world(q,n)
            dp=a.translation-b.translation
            dot=abs(a.rotation.x*b.rotation.x+a.rotation.y*b.rotation.y+a.rotation.z*b.rotation.z+a.rotation.w*b.rotation.w)
            cost+=dp.x*dp.x+dp.y*dp.y+dp.z*dp.z+100.*(1.-min(1.,dot))
        if best is None or cost<best[0]:best=(cost,t)
    return best[1]
def make(template,name,length,fps,sampler,body=False,charge=False):
    skeleton=template.get_editor_property('skeleton')
    names=[str(n) for n in u.AnimPoseExtensions.get_bone_names(u.AnimPoseExtensions.get_reference_pose(skeleton))]
    count=round(length*fps);tracks={n:[] for n in names}
    for i in range(count+1):
        a,b,w=sampler(i/fps)
        for n in names:
            k=local(a,n)
            tracks[n].append(mix(k,local(b,n),w) if b is not None else (k.translation,k.rotation,k.scale3d))
    factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',skeleton)
    if E.does_asset_exist(DEST+'/'+name):raise RuntimeError('Preserve existing candidate '+name)
    out=A.create_asset(name,DEST,u.AnimSequence,factory)
    out.set_editor_property('bone_compression_settings',template.get_editor_property('bone_compression_settings'))
    out.set_editor_property('enable_root_motion',False);out.set_editor_property('force_root_lock',body)
    out.get_editor_property('platform_target_frame_rate').set_editor_property('default',u.FrameRate(fps,1))
    ctrl=out.get_editor_property('controller');ctrl.open_bracket('Reuse complete native hammer strokes',False)
    try:
        ctrl.set_frame_rate(u.FrameRate(fps,1),False);ctrl.set_number_of_frames(u.FrameNumber(count),False)
        for n,keys in tracks.items():
            ctrl.add_bone_curve(n,False)
            if not ctrl.set_bone_track_keys(n,[v[0] for v in keys],[v[1] for v in keys],[v[2] for v in keys],False):raise RuntimeError('Cannot write '+n)
    finally:ctrl.close_bracket(False)
    u.AnimationLibrary.add_animation_notify_track(out,'FinalTollTiming')
    beats=[] if charge else [('Contact',.10),('SecondContact',.42),('Release',.54)]
    if body:beats += [('NativeWarhammerGrip',0.),('NativeWarhammerContinuousGrip',0.)]
    for key,t in beats:u.AnimationLibrary.add_animation_sync_marker(out,key,t,'FinalTollTiming')
    E.set_metadata_tag(out,'FinalToll.Revision','DirectReuseV5')
    E.set_metadata_tag(out,'FinalToll.JointPolicy',receipt['policy'])
    if not E.save_loaded_asset(out,False):raise RuntimeError('Cannot save '+name)
    receipt['saved'].append({'asset':out.get_path_name(),'fps':fps,'seconds':length})
    (P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print('Saved '+out.get_path_name(),flush=True)

normal=u.load_asset(spec['fps_normal']);upper=u.load_asset(spec['fps_upper'])
join=match_follow(normal,upper,.99,1.035,1.,['WPN_root','hand_l','hand_r','lowerarm_l','lowerarm_r'])
receipt['fps_bridge']={'start':.15,'end':.24,'slash1_source':join,'uppercut_source':1.}
def fps_sample(t):
    if t<=.10:return pose(normal,.84+.13*t/.10),None,0.
    if t<=.15:return pose(normal,.97+(join-.97)*(t-.10)/.05),None,0.
    if t<.24:return pose(normal,join),pose(upper,1.),smooth((t-.15)/.09)
    return pose(upper,upper_source(t)),None,0.
make(normal,'A_FinalToll_DirectReuseV5',1.25,240,fps_sample)

for row in spec['bodies']:
    n=u.load_asset(row['normal']);up=u.load_asset(row['upper'])
    nc=marker(n,'Contact',n.get_play_length()*.4);nr=marker(n,'Release',n.get_play_length()*.65)
    uc=marker(up,'Contact',up.get_play_length()*.4);ur=marker(up,'Release',up.get_play_length()*.65)
    loaded=nc*.5;uload=uc*.5
    join=match_follow(n,up,nc,min(nr,nc+.16),uload,['hand_l','hand_r','lowerarm_l','lowerarm_r'])
    def body_sample(t):
        if t<=.1:return pose(n,loaded+(nc-loaded)*(.35*(t/.1)+.65*(t/.1)**2)),None,0.
        if t<=.15:return pose(n,nc+(join-nc)*(t-.1)/.05),None,0.
        if t<.24:return pose(n,join),pose(up,uload),smooth((t-.15)/.09)
        if t<=.42:
            v=(t-.24)/.18;return pose(up,uload+(uc-uload)*(.35*v+.65*v*v)),None,0.
        if t<=.54:return pose(up,uc+(ur-uc)*smooth((t-.42)/.12)),None,0.
        return pose(up,ur+(up.get_play_length()-ur)*smooth((t-.54)/.71)),None,0.
    make(n,'A_FinalToll_DirectReuseBodyV5_'+row['variant'],1.25,120,body_sample,True)
    make(n,'A_FinalToll_ChargeBodyV5_'+row['variant'],2.,120,lambda t:(pose(n,loaded*smooth(t/2.)),None,0.),True,True)
receipt['complete']=True
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('DIRECT_REUSE_AUTHORING_COMPLETE',flush=True)
