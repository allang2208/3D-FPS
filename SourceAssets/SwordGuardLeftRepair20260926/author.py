"""Camera-plane guard; supported wrists/elbows on the installed V7 hand rig."""
import sys,json,math
from pathlib import Path
P=Path(__file__).parent;sys.path.insert(0,str(P))
from guard_source import *
ONE=Vector((1,1,1))
def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(t*(t*6-15)+10)
def blend(a,b,t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,t),a.to_quaternion().slerp(b.to_quaternion(),t),ONE)
def frame(d,n):
    z=d.normalized();y=(n-z*n.dot(z)).normalized();return Matrix((y.cross(z),y,z)).transposed()
def fingers(p,side,local):
    for n in rest:
        if n.endswith('_'+side) and n.startswith(('index','middle','ring','pinky','thumb')):
            p[n]=p[parents[n]]@local[n]

# Retain the original deliberate fist design, evaluated on this retained rig.
# Its installed guard tracks had near-straight fingers rather than this profile.
finger_source=ROOT/'SourceAssets/RuneSword20260913/FistBraceGuardV20'
ftree=ast.parse((finger_source/'author_guard.py').read_text())
fg={'REST':rest,'PARENT':parents,'LOCAL':local_rest,'Vector':Vector,'Matrix':Matrix,'Quaternion':Quaternion,'ONE':ONE,'math':math,
    'FINGER_NAMES':[n for n in rest if n.endswith('_l') and n.startswith(('index','middle','ring','pinky','thumb'))]}
exec(compile(ast.Module(body=[n for n in ftree.body if isinstance(n,ast.FunctionDef) and n.name in ('frame','finger_profile')],type_ignores=[]),'guard_fist_profile','exec'),fg)
wr=rest['hand_l'].translation
fg['REF_NORMAL']=(rest['pinky_01_l'].translation-wr).cross(rest['index_01_l'].translation-wr).normalized()
fg['REF_PALM']=fg['frame'](rest['middle_01_l'].translation-wr,fg['REF_NORMAL'])
FIST=fg['finger_profile'](json.loads((finger_source/'pose_config.json').read_text())['fist'])
def arm(p,side,hand,idle,w):
    U,F,H=['upperarm_'+side,'lowerarm_'+side,'hand_'+side]
    ru=rest[F].translation-rest[U].translation;rf=rest[H].translation-rest[F].translation
    hd=hand.to_quaternion()@rest[H].to_quaternion().inverted();neutral=(hd@rf).normalized()
    # Leave a small supported wrist bend; solve elbow/shoulder from the wrist.
    preferred=idle[U].translation.lerp(Vector((-.225 if side=='l' else .245,.055,-.225)),w)
    toward=(hand.translation-preferred).normalized()
    angle_now=neutral.angle(toward);turn=neutral.rotation_difference(toward)
    direction=(Quaternion().slerp(turn,min(1.,math.radians(14)/max(angle_now,1e-6)))@neutral).normalized()
    entry_fd=(idle[H].translation-idle[F].translation).normalized()
    entry_hand=idle[H].to_quaternion()@rest[H].to_quaternion().inverted()
    transported=hd@entry_hand.inverted()@entry_fd
    fd=transported.lerp(direction,ease(w/.45)).normalized()
    h=hand.translation;e=h-fd*rf.length
    a=e+(preferred-e).normalized()*ru.length;ud=(e-a).normalized()
    fq=neutral.rotation_difference(fd)@hd@rest[F].to_quaternion()
    fdef=fq@rest[F].to_quaternion().inverted()
    uq=(fdef@ru.normalized()).rotation_difference(ud)@fdef@rest[U].to_quaternion()
    # Remove axial mismatch at the elbow, measured after shortest-swing alignment.
    def seam(q):
        udm=q@rest[U].to_quaternion().inverted()
        aligned=(udm@rf.normalized()).rotation_difference(fd)@udm
        delta=fdef@aligned.inverted()
        return (2*math.atan2(Vector((delta.x,delta.y,delta.z)).dot(fd),delta.w)+math.pi)%(2*math.pi)-math.pi
    for _ in range(4):
        err=seam(uq)
        if abs(err)<1e-5:break
        eps=.001;der=(seam(Quaternion(ud,eps)@uq)-err)/eps
        if abs(der)>.01:uq=Quaternion(ud,-err/der)@uq
    iq=idle[U].to_quaternion();ifq=idle[F].to_quaternion()
    iu=(idle[F].translation-idle[U].translation).normalized()
    iq=iu.rotation_difference(ud)@iq
    ifq=entry_fd.rotation_difference(fd)@ifq
    uq=iq.slerp(uq,ease(w/.5));fq=ifq.slerp(fq,ease(w/.5))
    # Blending two individually supported frames can reintroduce elbow roll.
    # Re-solve that axial degree of freedom after the blend, including recovery.
    fdef=fq@rest[F].to_quaternion().inverted()
    idleud=idle[U].to_quaternion()@rest[U].to_quaternion().inverted()
    idlefd=idle[F].to_quaternion()@rest[F].to_quaternion().inverted()
    ia=(idleud@rf.normalized()).rotation_difference(entry_fd)@idleud
    idelta=idlefd@ia.inverted()
    idle_seam=(2*math.atan2(Vector((idelta.x,idelta.y,idelta.z)).dot(entry_fd),idelta.w)+math.pi)%(2*math.pi)-math.pi
    goal_seam=idle_seam*(1-ease(w/.5))
    for _ in range(5):
        err=(seam(uq)-goal_seam+math.pi)%(2*math.pi)-math.pi
        if abs(err)<1e-5:break
        eps=.001;der=(seam(Quaternion(ud,eps)@uq)-seam(uq))/eps
        if abs(der)>.01:uq=Quaternion(ud,-err/der)@uq
    p[U]=Matrix.LocRotScale(a,uq,ONE);p[F]=Matrix.LocRotScale(e,fq,ONE);p[H]=hand
    # Shoulder-cap weights follow the same supported segment, with idle kept exact.
    oldrel=idle[U].inverted()@idle['clavicle_'+side]
    neutralrel=rest[U].inverted()@rest['clavicle_'+side]
    p['clavicle_'+side]=p[U]@blend(oldrel,neutralrel,ease(w/.65))
    for n in (U,F):
        for i in ('01','02'):
            helper=n[:-2]+'_twist_'+i+'_'+side
            old=idle[n].inverted()@idle[helper];new=rest[n].inverted()@rest[helper]
            p[helper]=p[n]@blend(old,new,ease(w/.5))

def make_held(old,idle):
    bd=(rest['Blade_Tip'].translation-rest['Blade_Base'].translation).normalized()
    # Blade axis lies exactly in camera XZ: dot(player_forward, blade_axis)=0.
    d=Vector((-math.cos(math.radians(25)),0,math.sin(math.radians(25))))
    q=(frame(d,Vector((0,1,0)))@frame(bd,Vector((0,1,0))).inverted()@rest['WPN_root'].to_quaternion().to_matrix()).to_quaternion()
    sword=Matrix.LocRotScale(Vector((.18,.48,-.10)),q,ONE)
    delta=sword@old['WPN_root'].inverted()
    lh=delta@old['hand_l'];rh=sword@idle['WPN_root'].inverted()@idle['hand_r']
    # Roll the right grip around the handle, keeping its palm contact fixed.
    # This places the right elbow below the hand instead of above the guard.
    rr=(rest['hand_r'].translation-rest['lowerarm_r'].translation).normalized()
    ra=rh.to_quaternion()@rest['hand_r'].to_quaternion().inverted()@rr
    wanted=Vector((-.12,.52,.85)).normalized()
    ap=(ra-d*ra.dot(d)).normalized();bp=(wanted-d*wanted.dot(d)).normalized()
    roll=math.atan2(d.dot(ap.cross(bp)),ap.dot(bp))
    rh=Matrix.Translation(sword.translation)@Quaternion(d,roll).to_matrix().to_4x4()@Matrix.Translation(-sword.translation)@rh
    # Preserve the dorsal brace point while turning the palm/forearm together.
    oldaxis=lh.to_quaternion()@rest['hand_l'].to_quaternion().inverted()@(rest['hand_l'].translation-rest['lowerarm_l'].translation).normalized()
    newaxis=Vector((.40,.48,.78)).normalized()
    palmref=rest['middle_01_l'].translation-rest['hand_l'].translation
    qh=(frame(newaxis,Vector((0,-1,.15)))@frame(palmref,fg['REF_NORMAL']).inverted()@rest['hand_l'].to_quaternion().to_matrix()).to_quaternion()
    pad=rest['hand_l'].inverted()@((rest['index_01_l'].translation+rest['pinky_01_l'].translation)*.5)
    anchor=lh@pad+Vector((0,-.022,.008))
    lh=Matrix.LocRotScale(anchor-qh@pad,qh,ONE)
    return sword,lh,rh

setup_render();out=P/'Review';out.mkdir(exist_ok=True)
report={}
for variant in ('Standard','LongGrip'):
    data=json.loads((P/'Before'/variant/'installed.json').read_text())
    idle=from_ue(data['clips']['Idle']['samples'][0]['world'])
    old=from_ue(data['clips']['Guard']['samples'][-1]['world'])
    sword,lh,rh=make_held(old,idle)
    rightrel=sword.inverted()@rh;leftrel=sword.inverted()@lh
    idlegrip=idle['WPN_root'].inverted()@idle['hand_r'];griproll=rightrel@idlegrip.inverted()
    ilocal={n:idle[parents[n]].inverted()@m if parents[n] else m for n,m in idle.items()}
    oldlocal={n:old[parents[n]].inverted()@m if parents[n] else m for n,m in old.items()}
    fist={n:m.copy() for n,m in ilocal.items()}
    fist.update(FIST)
    def assemble(sw,left,w,close):
        if w<=1e-8:return {n:m.copy() for n,m in idle.items()}
        p={n:m.copy() for n,m in idle.items()}
        right=sw@blend(Matrix.Identity(4),griproll,ease(w))@idlegrip
        # At the raised end the full original hilt/hand relation is preserved.
        arm(p,'r',right,idle,w);arm(p,'l',left,idle,w)
        lf={n:blend(ilocal[n],blend(oldlocal[n],fist[n],close),ease(w/.7)) for n in ilocal}
        fingers(p,'l',lf);fingers(p,'r',ilocal)
        for n in ('WPN_root','Blade_Base','Blade_Tip'):
            p[n]=sw@idle['WPN_root'].inverted()@idle[n]
        return p
    # Fit the actual V7 dorsal surface to the near broad face, not a glove pad.
    apply_pose(assemble(sword,lh,1.,1.))
    deps=bpy.context.evaluated_depsgraph_get();ev=arms.evaluated_get(deps);sk=ev.to_mesh()
    group=arms.vertex_groups.get('hand_l').index
    candidates=[]
    for vertex in arms.data.vertices:
        palm=fg['REF_PALM'].inverted()@(vertex.co-rest['hand_l'].translation)
        if .025<palm.x<.075 and abs(palm.y)<.028 and any(g.group==group and g.weight>.5 for g in vertex.groups):
            candidates.append((ev.matrix_world@sk.vertices[vertex.index].co).y)
    be=blade.evaluated_get(deps);bm=be.to_mesh();bv=[]
    for v in bm.vertices:
        p=be.matrix_world@v.co;along=(p-sword.translation).dot((helddir:=Vector((-math.cos(math.radians(25)),0,math.sin(math.radians(25))))))
        if .20<along<.45:bv.append(p.y)
    contact_shift=min(bv)-.001-max(candidates)
    ev.to_mesh_clear();be.to_mesh_clear()
    lh.translation.y+=contact_shift;leftrel=sword.inverted()@lh
    clips={}
    for clip,info in data['clips'].items():
        if clip=='Idle':continue
        frames=[]
        for row in info['samples']:
            t=row['seconds'];duration=info['seconds']
            if clip=='Guard':
                w=ease(t/duration);sw=blend(idle['WPN_root'],sword,w)
                sw.translation+=Vector((0,-.014,.012))*math.sin(math.pi*t/duration)**2
                left=blend(idle['hand_l'],lh,w);left.translation+=Vector((-.035,-.035,.015))*math.sin(math.pi*t/duration)**2
                close=1.
            elif clip=='GuardHit':
                w=1.;f=ease(t/.045) if t<.045 else 1-ease((t-.045)/(duration-.045))
                recoil=Matrix.Translation(Vector((0,-.026,-.008))*f)
                sw=recoil@sword;left=sw@leftrel;close=1.
            else:
                peak=.105;u=ease(min(1,t/peak));recovery=ease((t-peak)/(duration-peak))
                drop=Matrix.Translation(sword.translation+Vector((.045,-.025,-.105)))@Matrix.Rotation(math.radians(-10),4,'Y')@sword.to_quaternion().to_matrix().to_4x4()
                sw=blend(blend(sword,drop,u),idle['WPN_root'],recovery)
                loose=drop@leftrel;loose.translation+=Vector((-.05,-.035,-.015))
                left=blend(blend(lh,loose,u),idle['hand_l'],recovery)
                left.translation+=Vector((-.035,-.025,-.018))*math.sin(math.pi*recovery)**2
                w=1-recovery;close=1-.65*math.sin(math.pi*min(1,t/duration))**2
            p=assemble(sw,left,w,close)
            frames.append(p)
        clips[clip]=frames
    held=clips['Guard'][-1]
    clips['GuardHit'][0]={n:m.copy() for n,m in held.items()};clips['GuardHit'][-1]={n:m.copy() for n,m in held.items()}
    clips['GuardBreak'][0]={n:m.copy() for n,m in held.items()}
    render_pose(held,out/(variant+'_after_fp.jpg'))
    render_pose(held,out/(variant+'_after_close.jpg'),True)
    render_pose(clips['GuardBreak'][round(.105*480)],out/(variant+'_break_after.jpg'),True)
    report[variant]={'dorsal_surface_forward_fit_m':contact_shift}
    dest=P/'Final'/variant;dest.mkdir(parents=True,exist_ok=True)
    for clip,frames in clips.items():
        info=data['clips'][clip];samples=[];previous={}
        # Include every rig track; unchanged roots and endpoint scales retain native data.
        edited=[n for n in rest if n.startswith(('upperarm','lowerarm','clavicle','hand','index','middle','ring','pinky','thumb')) or n in ('WPN_root','Blade_Base','Blade_Tip')]
        for i,p in enumerate(frames):
            world=info['samples'][i]['world'];native=to_ue(p,world);keys={}
            for n in edited:
                par=data['parents'][n];m=native[par].inverted()@native[n] if par in native else native[n]
                pos,q,scale=m.decompose()
                original=ue_matrix(world[par]).inverted()@ue_matrix(world[n]) if par in world else ue_matrix(world[n])
                scale=original.to_scale()
                if n in previous and q.dot(previous[n])<0:q.negate()
                previous[n]=q.copy();keys[n]={'p':list(pos),'q':list(q),'s':list(scale)}
            samples.append({'seconds':info['samples'][i]['seconds'],'bones':keys})
        patch={'revision':'GuardCameraPlaneV22','asset':info['asset'],'source_sha256':info['sha256'],'intervals':info['intervals'],'seconds':info['seconds'],'edited_bones':edited,'samples':samples}
        (dest/(clip+'_patch.json')).write_text(json.dumps(patch,separators=(',',':')))
        values=[metrics(p) for p in frames]
        report[variant][clip]={'start':values[0],'end':values[-1],'max_wrist_bend_deg':max(x['wrist_bend_deg'] for x in values),'max_elbow_seam_deg':max(abs(x['elbow_seam_deg']) for x in values)}
        action=bpy.data.actions.new('GuardV22_'+variant+'_'+clip);action.use_fake_user=True
        rig.animation_data_create();rig.animation_data.action=action
        scene.render.fps=480;scene.render.fps_base=1
        previous_q={}
        for f,p in enumerate(frames):
            scene.frame_set(f);apply_pose(p)
            for b in rig.pose.bones:
                b.rotation_mode='QUATERNION'
                if b.name in previous_q and b.rotation_quaternion.dot(previous_q[b.name])<0:b.rotation_quaternion.negate()
                previous_q[b.name]=b.rotation_quaternion.copy()
                for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f,group=b.name)
        rig.animation_data.action_slot=action.slots[0]
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for k in curve.keyframe_points:k.interpolation='LINEAR'
        rig.animation_data_clear()
    report[variant]['held_blade_forward_dot']=(held['Blade_Tip'].translation-held['Blade_Base'].translation).normalized().y
(P/'authoring.json').write_text(json.dumps(report,indent=2))
rig.animation_data_create();rig.animation_data.action=bpy.data.actions['GuardV22_Standard_Guard']
rig.animation_data.action_slot=rig.animation_data.action.slots[0];scene.frame_start=0;scene.frame_end=96;scene.frame_set(96)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuardCameraPlaneV22_Editable.blend'))
print('GUARD_V22_AUTHORED',flush=True)
