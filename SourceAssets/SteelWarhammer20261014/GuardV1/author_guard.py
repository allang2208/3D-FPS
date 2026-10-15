"""Five native two-hand guard clips, fixed shaft contacts and supported arm chains."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector

P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
SOURCE=P.parent/'NormalComboV4/Warhammer_Combo_Restored_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
rig.animation_data.action=bpy.data.actions['A_Warhammer_Slash1'];rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0)
FPS=300
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
idle={b.name:b.matrix.copy() for b in rig.pose.bones}
idle_local={n:idle[p].inverted()@m if p else m for n,m in idle.items() for p in [parents[n]]}
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'ease','apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
module=ast.parse((P.parent/'WhirlwindHandoffV5/author_whirlwind.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'rigid','frame','axial','solve_arm'}],type_ignores=[]),'<supported_native_arm>','exec'))
roll_state={}
ready=idle['WPN_root'];grips={s:ready.inverted()@idle['hand_'+s] for s in ('l','r')}
pivot=(grips['l'].translation+grips['r'].translation)*.5
axis0=ready.to_quaternion()@Vector((0,0,1))
direction=Vector((math.cos(math.radians(25)),.12,math.sin(math.radians(25)))).normalized()
hold_q=axis0.rotation_difference(direction)@ready.to_quaternion()
hold_center=Vector((0.,.42,-.26))
hold=rigid(hold_center-hold_q@pivot,hold_q)
drop_q=Quaternion((0,1,0),math.radians(17))@hold_q
drop_center=hold_center+Vector((.115,-.025,-.125))
drop=rigid(drop_center-drop_q@pivot,drop_q)

def mix(a,b,w):
    return rigid((a@pivot).lerp(b@pivot,w),a.to_quaternion().slerp(b.to_quaternion(),w))@Matrix.Translation(-pivot)

def displaced(base,shift,degrees):
    q=Quaternion((0,1,0),math.radians(degrees))@base.to_quaternion()
    return rigid(base@pivot+Vector(shift)-q@pivot,q)

def hermite(t,t0,t1,p0,p1,v0,v1):
    u=max(0.,min(1.,(t-t0)/(t1-t0)));d=t1-t0
    return (2*u**3-3*u*u+1)*p0+(u**3-2*u*u+u)*d*v0+(-2*u**3+3*u*u)*p1+(u**3-u*u)*d*v1

native={}
for side in ('l','r'):
    U,L,H,C=[n+'_'+side for n in ('upperarm','lowerarm','hand','clavicle')]
    u0=rest[L].translation-rest[U].translation;l0=rest[H].translation-rest[L].translation
    normal0=u0.cross(l0).normalized();upper=idle[L].translation-idle[U].translation;fore=idle[H].translation-idle[L].translation
    dh=idle[H].to_quaternion()@rest[H].to_quaternion().inverted()
    full=(dh@l0).rotation_difference(fore)@dh
    hinge=frame(fore,upper.cross(fore))@frame(l0,normal0).inverted()
    native[side]=(U,L,H,C,u0,l0,normal0,axial(full@hinge.inverted(),fore.normalized()))

def supported_arm(out,target,side,weight):
    # The idle chain supplies the elbow guide. The hand stays rigidly on the
    # shaft; the shoulder and elbow carry its orientation instead of the wrist.
    ref=copy.deepcopy(idle);solve_arm(ref,idle,target,side)
    U,L,H,C,u0,l0,n0,r0=native[side];L1=u0.length;L2=l0.length
    s0,e0,h=[ref[n].translation for n in (U,L,H)]
    fore0=(h-e0).normalized();dh=target.to_quaternion()@rest[H].to_quaternion().inverted()
    hand_axis=(dh@l0).normalized();bend=hand_axis.angle(fore0)
    fore=Quaternion().slerp(hand_axis.rotation_difference(fore0),min(1.,math.radians(18)/max(bend,1e-7)))@hand_axis
    full=hand_axis.rotation_difference(fore)@dh;target_e=h-fore*L2
    old_flex=(e0-s0).angle(h-e0)
    def candidate(r):
        normal=(Quaternion(fore,-r)@full@n0).normalized()
        desired=target_e-s0;desired-=normal*desired.dot(normal)
        a=-math.atan2(normal.dot(fore.cross(desired)),fore.dot(desired))
        a=max(math.radians(25),min(math.radians(125),a))
        upper=Quaternion(normal,-a)@fore;s=target_e-upper*L1;delta=s-s0
        visible=max(0.,s.z+max(0.,s.y)*.65+.065)
        score=delta.length_squared+4*max(0.,delta.length-.16)**2+10*visible*visible
        score+=.00012*(a-old_flex)**2+.00008*(r-r0)**2
        return score,s,target_e,r
    coarse=min((candidate(r0+math.radians(i)) for i in range(-180,181,5)),key=lambda x:x[0])
    lo,hi=coarse[3]-math.radians(5),coarse[3]+math.radians(5)
    # Continuous refinement avoids stepped elbow angles from quantized search.
    for _ in range(24):
        a=lo+(hi-lo)*.381966;b=lo+(hi-lo)*.618034
        if candidate(a)[0]<candidate(b)[0]:hi=b
        else:lo=a
    best=candidate((lo+hi)*.5)
    s=s0.lerp(best[1],weight);guide=e0.lerp(best[2],weight)
    reach=h-s;d=reach.length;axis=reach.normalized()
    along=(L1*L1-L2*L2+d*d)/(2*d);center=s+axis*along
    pole=guide-center;pole-=axis*pole.dot(axis)
    e=center+pole.normalized()*math.sqrt(max(0.,L1*L1-along*along))
    upper=e-s;fore=h-e;normal=upper.cross(fore).normalized()
    du=frame(upper,normal)@frame(u0,n0).inverted()
    hinge=frame(fore,normal)@frame(l0,n0).inverted()
    full=(dh@l0).rotation_difference(fore)@dh
    roll=axial(full@hinge.inverted(),fore.normalized());roll=r0+(roll-r0+math.pi)%(2*math.pi)-math.pi
    uq=ref[U].to_quaternion().slerp(du@rest[U].to_quaternion(),weight)
    uq=((uq@rest[U].to_quaternion().inverted()@u0).rotation_difference(upper)@uq).normalized()
    lq=ref[L].to_quaternion().slerp(full@rest[L].to_quaternion(),weight)
    lq=((lq@rest[L].to_quaternion().inverted()@l0).rotation_difference(fore)@lq).normalized()
    out[C]=ref[C].copy();out[C].translation+=s-s0
    out[U]=rigid(s,uq);out[L]=rigid(e,lq);out[H]=target
    for stem,origin,segment,deform in (('upperarm',s,upper,du),('lowerarm',e,fore,hinge)):
        base=U if stem=='upperarm' else L;old_segment=u0 if stem=='upperarm' else l0
        ref_segment=ref[L].translation-ref[U].translation if stem=='upperarm' else ref[H].translation-ref[L].translation
        carry=ref_segment.rotation_difference(segment)
        for index in ('01','02'):
            n=stem+'_twist_'+index+'_'+side;goal=deform
            if stem=='lowerarm':goal=Quaternion(fore.normalized(),roll*STATIONS[side][n])@hinge
            q=(carry@ref[n].to_quaternion()).slerp(goal@rest[n].to_quaternion(),weight)
            fraction=(rest[n].translation-rest[base].translation).dot(old_segment.normalized())/old_segment.length
            out[n]=rigid(origin+segment*fraction,q)

explicit={'root','WPN_root','clavicle_l','clavicle_r','upperarm_l','upperarm_r','lowerarm_l','lowerarm_r','hand_l','hand_r'}
explicit.update(n for n in idle if n.startswith(('upperarm_twist','lowerarm_twist')))
def pose_at(w,weight):
    if weight<=1e-8 and (w.translation-ready.translation).length<1e-7:return copy.deepcopy(idle)
    out=copy.deepcopy(idle);out['WPN_root']=w
    for side in ('l','r'):supported_arm(out,w@grips[side],side,weight)
    done=set(explicit)
    def resolve(n):
        if n in done:return out[n]
        parent=parents[n];out[n]=resolve(parent)@idle_local[n] if parent else idle[n].copy();done.add(n);return out[n]
    for n in out:resolve(n)
    for side in ('l','r'):
        n='ik_hand_'+side
        if n in out:out[n]=out['hand_'+side]@idle['hand_'+side].inverted()@idle[n]
    return out

def motion(clip,t):
    if clip=='GuardEnter':
        w=hermite(t,0,.08,0,.65,0,6) if t<=.08 else hermite(t,.08,.22,.65,1,6,0)
        return mix(ready,hold,w),ease(t/.22)
    if clip=='GuardHold':
        breath=math.sin(math.pi*t/1.6)**2
        return displaced(hold,(0,.001*breath,.0015*breath),.12*breath),1.
    if clip=='GuardHit':
        pulse=ease(t/.055) if t<.055 else 1-ease((t-.055)/.245)
        return displaced(hold,(.008*pulse,-.025*pulse,-.020*pulse),-3*pulse),1.
    if clip=='GuardBreak':
        if t<=.22:return mix(hold,drop,ease(t/.22)),1.
        if t<=.95:
            drift=ease((t-.22)/.73)
            return displaced(drop,(.008*drift,0,-.012*drift),1.2*drift),1.
        end_drop=displaced(drop,(.008,0,-.012),1.2);w=ease((t-.95)/.55)
        return mix(end_drop,ready,w),1-w
    w=ease(t/.25);return mix(hold,ready,w),1-w

durations={'GuardEnter':.22,'GuardHold':1.6,'GuardHit':.30,'GuardBreak':1.5,'GuardExit':.25}
actions={}
for clip,duration in durations.items():
    print('AUTHOR_GUARD',clip,duration,flush=True)
    poses=[pose_at(*motion(clip,i/FPS)) for i in range(round(duration*FPS)+1)]
    actions[clip]=bake('A_Warhammer_'+clip,poses,FPS)
rig.animation_data.action=actions['GuardEnter'];rig.animation_data.action_slot=actions['GuardEnter'].slots[0];scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_GuardV1_Editable.blend'))
receipt={'revision':'DiagonalTwoHandGuardV1_20261015','clips':['A_Warhammer_'+x for x in durations],
    'fps':FPS,'durations_seconds':durations,'source':str(SOURCE),'grip':'Original native idle shaft contacts and finger poses retained throughout',
    'hold_shaft_degrees_above_screen_horizontal':25,'hold_hand_center_m':list(hold_center),'hold_shaft_axis':list(direction),
    'arm_method':'Full supported native chains, fixed segment lengths, continuous hinge solve, palm-aligned forearms, native skin twist stations',
    'phase_design':'Fast raise and settle; subtle loop; 55 ms impact compression and relaxed return; right-down break and recovery',
    'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_GUARD_AUTHORED',json.dumps(receipt),flush=True)
