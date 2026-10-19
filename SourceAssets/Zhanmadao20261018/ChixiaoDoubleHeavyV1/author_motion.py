"""Keep the heavy cut, then author a supported upward-right return cut."""
import bisect,importlib.util,json,math,re
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
source=ROOT/'SourceAssets/SwordUppercut20261003/GripRecoveryV15/arm_support.py'
spec=importlib.util.spec_from_file_location('chixiao_arm_support',source)
A=importlib.util.module_from_spec(spec);spec.loader.exec_module(A)
data=json.loads((P/'motion_sources.json').read_text('utf-8'))
header=(ROOT/'Source/FPSGAME/Weapons/RuneSwordChixiaoRhythm.h').read_text('utf-8')
R={k:float(v) for k,v in re.findall(r'constexpr float (\w+)\s*=\s*([\d.]+)f',header)}
FPS=240;END=R['End']
def blend(a,b,t):
    p,q,s=a.decompose();v,r,z=b.decompose()
    if q.dot(r)<0:r=-r
    return A.mat(p.lerp(v,t),q.slerp(r,t),s.lerp(z,t))
def rows_at(clip,t):
    samples=clip['samples'];times=[s['seconds'] for s in samples]
    i=max(0,min(len(samples)-1,bisect.bisect_right(times,t)-1));j=min(len(samples)-1,i+1)
    u=(t-times[i])/(times[j]-times[i]) if j!=i else 0.
    return {n:blend(A.native(k),A.native(samples[j]['bones'][n]),u) for n,k in samples[i]['bones'].items()}
def pose_at(clip,t):return {n:A.canonical(m) for n,m in A.globalize(rows_at(clip,t)).items()}
def blend_pose(a,b,t):return {n:blend(a[n],b[n],t) for n in a}
def pack_local(local,previous):
    rows={}
    for n,m in local.items():
        p,q,s=m.decompose()
        if n in previous and q.dot(previous[n])<0:q=-q
        previous[n]=q.copy();rows[n]={'p':list(p),'q':list(q),'s':list(s)}
    return rows
def serialize(pose,previous):
    ue={n:A.mat(A.C@m.translation*100,(A.C@m.to_quaternion().to_matrix()@A.C).to_quaternion(),m.to_scale()) for n,m in pose.items()}
    return pack_local(A.localize(ue),previous)
def grip_frame(m):return A.mat(m.translation,m.to_quaternion())
receipt={'timing':R,'sources':{k:{n:v[n] for n in ('path','seconds','markers')} for k,v in data.items()},'clips':{},'runtime_tested':False}
for variant in ('Standard','LongGrip'):
    heavy,upper=data[variant+'Heavy'],data[variant+'Upper']
    idle=pose_at(heavy,heavy['seconds']);land=pose_at(heavy,R['FirstFollowEnd'])
    low=pose_at(upper,1.0);high=pose_at(upper,1.125)
    bpy.ops.wm.open_mainfile(filepath=str(A.SOURCE))
    bpy.context.preferences.filepaths.save_version=0
    scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE');rig.animation_data_clear()
    rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
    local_rest={n:rest[A.PARENTS[n]].inverted()@m if A.PARENTS[n] in rest else m for n,m in rest.items()}
    reference={n:A.canonical(A.native(row)) for n,row in A.DATA['reference'].items()}
    correction={n:reference[n].inverted()@rest[n] for n in rest}
    skin={s:A.fit_skin_stations([o for o in scene.objects if o.type=='MESH'],reference,s) for s in ('l','r')}
    state={s:{'pole':0.,'roll':0.} for s in ('l','r')}
    weapon_start=land['WPN_root'].copy();weapon_finish=high['WPN_root'].copy()
    weapon_finish.translation+=Vector((.20,0.,0.))
    # Tilt the accepted uppercut's up-facing tip toward camera-right as a whole shaft.
    weapon_finish=A.mat(weapon_finish.translation,
        Quaternion(Vector((0,1,0)),math.radians(28))@weapon_finish.to_quaternion(),weapon_finish.to_scale())
    grip_land={s:grip_frame(weapon_start).inverted()@grip_frame(land['hand_'+s]) for s in ('l','r')}
    grip_high={s:grip_frame(high['WPN_root']).inverted()@grip_frame(high['hand_'+s]) for s in ('l','r')}
    grip_idle={s:grip_frame(idle['WPN_root']).inverted()@grip_frame(idle['hand_'+s]) for s in ('l','r')}
    rig.animation_data_create();action=bpy.data.actions.new('Chixiao_DoubleHeavy_'+variant);action.use_fake_user=True;rig.animation_data.action=action
    samples=[];previous={};blend_previous={}
    for frame in range(round(END*FPS)+1):
        t=frame/FPS
        if t<=R['FirstFollowEnd']:pose=pose_at(heavy,t)
        else:
            if t<R['SecondStart']:
                u=A.smooth((t-R['FirstFollowEnd'])/(R['SecondStart']-R['FirstFollowEnd']))
                base=land;weapon=weapon_start.copy();grips={s:blend(grip_land[s],grip_high[s],u) for s in ('l','r')};support=u
            elif t<=R['SecondEnd']:
                u=(t-R['SecondStart'])/(R['SecondEnd']-R['SecondStart']);travel=A.smooth(u)
                base=blend_pose(land,high,travel);weapon=blend(weapon_start,weapon_finish,travel)
                weapon.translation+=Vector((0,.07*math.sin(math.pi*u),0));grips=grip_high;support=1.
            elif t<R['FollowEnd']:base=high;weapon=weapon_finish;grips=grip_high;support=1.
            else:
                u=A.smooth((t-R['FollowEnd'])/(END-R['FollowEnd']))
                base=blend_pose(high,idle,u);weapon=blend(weapon_finish,idle['WPN_root'],u)
                grips={s:blend(grip_high[s],grip_idle[s],u) for s in ('l','r')};support=1.-A.smooth((t-(END-.16))/.16)
            pose={n:m.copy() for n,m in base.items()};carry=weapon@base['WPN_root'].inverted()
            for n in A.descendants('WPN_root')|{'ik_hand_gun'}:pose[n]=carry@base[n]
            for s in ('l','r'):
                hand='hand_'+s;target=grip_frame(weapon)@grips[s]
                target=A.mat(target.translation,target.to_quaternion(),base[hand].to_scale());delta=target@base[hand].inverted()
                for n in A.HANDS[s]:pose[n]=delta@base[n]
                A.solve_supported_arm(pose,idle,base,s,support,state[s],skin[s])
                pose['ik_hand_'+s]=pose[hand]@idle[hand].inverted()@idle['ik_hand_'+s]
            if frame==round(END*FPS):pose={n:m.copy() for n,m in idle.items()}
        samples.append({'seconds':t,'bones':serialize(pose,previous)})
        scene.frame_set(frame);world={n:pose[n]@correction[n] for n in rest}
        for b in rig.pose.bones:
            parent=world[b.parent.name] if b.parent else Matrix.Identity(4)
            b.matrix_basis=local_rest[b.name].inverted()@parent.inverted()@world[b.name]
            b.rotation_mode='QUATERNION';q=b.rotation_quaternion.copy()
            if b.name in blend_previous and q.dot(blend_previous[b.name])<0:q=-q
            b.rotation_quaternion=q;blend_previous[b.name]=q.copy()
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=frame,group=b.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.render.fps=FPS;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=round(END*FPS);scene.frame_set(0)
    out=P/variant;out.mkdir(exist_ok=True);keys=out/'editable_keys.json'
    keys.write_text(json.dumps({'fps':FPS,'skeleton':heavy['skeleton'],'samples':samples},separators=(',',':')),encoding='utf-8')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'Chixiao_DoubleHeavy_Editable.blend'))
    receipt['clips'][variant]={'keys':str(keys),'seconds':END,'fps':FPS,'base':heavy['path'],'uppercut_reference':upper['path']}
    print('CHIXIAO_FPS_MOTION_AUTHORED',variant,flush=True)
# Separate world-body take; the same two contacts, without the uppercut skill's stride.
heavy,upper=data['BodyHeavy'],data['BodyUpper']
hm={m['name']:m['time'] for m in heavy['markers']};um={m['name']:m['time'] for m in upper['markers']}
hc=hm.get('Contact',heavy['seconds']*.35);hr=hm.get('Release',heavy['seconds']*.55)
uc=um.get('Contact',upper['seconds']*.35);ur=um.get('Release',upper['seconds']*.55)
body_samples=[];previous={};first_land=rows_at(heavy,hr);rise_start=rows_at(upper,uc*.55)
for frame in range(round(END*FPS)+1):
    t=frame/FPS
    if t<=R['FirstEnd']:rows=rows_at(heavy,hc*.7+(hr-hc*.7)*t/R['FirstEnd'])
    elif t<R['SecondStart']:
        u=A.smooth((t-R['FirstEnd'])/(R['SecondStart']-R['FirstEnd']));rows=blend_pose(first_land,rise_start,u)
    elif t<=R['SecondEnd']:
        u=(t-R['SecondStart'])/(R['SecondEnd']-R['SecondStart']);rows=rows_at(upper,uc*.55+(ur-uc*.55)*u)
    else:
        u=A.smooth((t-R['SecondEnd'])/(END-R['SecondEnd']));rows=rows_at(upper,ur+(upper['seconds']-ur)*u)
    body_samples.append({'seconds':t,'bones':pack_local(rows,previous)})
out=P/'Body';out.mkdir(exist_ok=True);keys=out/'editable_keys.json'
keys.write_text(json.dumps({'fps':FPS,'skeleton':heavy['skeleton'],'samples':body_samples},separators=(',',':')),encoding='utf-8')
receipt['clips']['Body']={'keys':str(keys),'seconds':END,'fps':FPS,'base':heavy['path']}
(P/'authoring.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('CHIXIAO_DOUBLE_HEAVY_AUTHORED',flush=True)
