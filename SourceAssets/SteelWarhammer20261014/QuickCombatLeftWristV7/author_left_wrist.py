"""Repair only the V6 left arm, retaining the complete hand/weapon contact."""
import ast,copy,json,math
from pathlib import Path
import bpy
from mathutils import Matrix,Quaternion,Vector
P=Path(__file__).resolve().parent;ROOT=P.parents[2];OUT=P/'Export';OUT.mkdir(exist_ok=True)
SOURCE=P.parent/'QuickCombatReachV6/Warhammer_QuickCombat_ReachV6_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE));bpy.context.preferences.filepaths.save_version=0
scene=bpy.context.scene;rig=bpy.data.objects['SK_RusticPickaxe_Rig'];rig.data.pose_position='POSE'
FPS=300;DURATION=.5
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
local_rest={n:rest[p].inverted()@m if p else m for n,m in rest.items() for p in [parents[n]]}
source=[]
for i in range(round(DURATION*FPS)+1):
    scene.frame_set(i);source.append({b.name:b.matrix.copy() for b in rig.pose.bones})
STATIONS=json.loads((ROOT/'SourceAssets/AxeTwoHandAttack20260919/V5/authoring.json').read_text())['skin_stations']['l']
module=ast.parse((P.parent/'SprintDragV1/author_sprint.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in module.body if isinstance(n,ast.FunctionDef) and n.name in {'apply_pose','new_action','bake'}],type_ignores=[]),'<native_baker>','exec'))
def ease(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))
def frame(axis,normal):
    x=axis.normalized();z=(normal-x*normal.dot(x)).normalized()
    return Matrix((x,z.cross(x).normalized(),z)).transposed().to_quaternion()
def rigid(p,q):return Matrix.LocRotScale(p,q,Vector((1,1,1)))
def angle(q):return 2*math.acos(min(1.,abs(q.normalized().w)))
def twist(q,axis):
    a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(axis),q.w)
    return (a+math.pi)%(2*math.pi)-math.pi
U,L,H,C='upperarm_l','lowerarm_l','hand_l','clavicle_l'
u0=rest[L].translation-rest[U].translation;l0=rest[H].translation-rest[L].translation
n0=u0.cross(l0).normalized();L1=u0.length;L2=l0.length
affected={C,U,L,'upperarm_twist_01_l','upperarm_twist_02_l','lowerarm_twist_01_l','lowerarm_twist_02_l'}
raw=[]
for ref in source:
    s0,e0,h=[ref[n].translation for n in (U,L,H)]
    fore0=(h-e0).normalized();dh=ref[H].to_quaternion()@rest[H].to_quaternion().inverted()
    hand_axis=(dh@l0).normalized();bend=hand_axis.angle(fore0)
    # Preserve the existing direction as far as a relaxed wrist allows.
    fore=Quaternion().slerp(hand_axis.rotation_difference(fore0),min(1.,math.radians(18)/max(1e-7,bend)))@hand_axis
    df=hand_axis.rotation_difference(fore)@dh;e=h-fore*L2
    old_flex=(e0-s0).angle(h-e0)
    best=None
    # These are native bind-frame angles, not anatomical neutral angles. The
    # accepted native idle already has substantial palm roll relative to its
    # hinge; do not impose a +/-85 medical limit on this different frame.
    for pronation in range(-180,181,5):
        r=math.radians(pronation);base=Quaternion(fore,-r)@df;normal=(base@n0).normalized()
        for flex in range(25,126,3):
            a=math.radians(flex);upper=Quaternion(normal,-a)@fore;s=e-upper*L1
            delta=s-s0
            # Shoulder follows the reach but stays below the view instead of
            # leaving all extra motion at the wrist or straightening the elbow.
            visible=max(0.,s.z+max(0.,s.y)*.65+.065)
            score=delta.length_squared+4*max(0.,delta.length-.16)**2+10*visible*visible
            score+=.00012*(a-old_flex)**2+.00002*r*r
            if best is None or score<best[0]:best=(score,s.copy(),e.copy(),r,a)
    raw.append(best)

poses=[];rows=[];previous_roll=None
for i,ref in enumerate(source):
    t=i/FPS;weight=max(0.,min(1.,ease(t/.045)*(1-ease((t-.42)/.08))));pose=copy.deepcopy(ref)
    if weight>1e-8:
        # Symmetric five-frame smoothing keeps the bounded search from adding
        # discrete elbow changes; the constrained chain is reconstructed after.
        indices=range(max(0,i-2),min(len(raw),i+3))
        goals=[raw[j] for j in indices]
        target_s=sum((g[1] for g in goals),Vector())/len(goals)
        target_e=sum((g[2] for g in goals),Vector())/len(goals)
        s0,e0,h=[ref[n].translation for n in (U,L,H)]
        s=s0.lerp(target_s,weight);guide=e0.lerp(target_e,weight)
        reach=h-s;d=reach.length;axis=reach.normalized()
        along=(L1*L1-L2*L2+d*d)/(2*d);center=s+axis*along
        pole=guide-center;pole-=axis*pole.dot(axis)
        if pole.length<1e-7:pole=(e0-center)-axis*(e0-center).dot(axis)
        e=center+pole.normalized()*math.sqrt(max(0.,L1*L1-along*along))
        upper=e-s;fore=h-e
        dh=ref[H].to_quaternion()@rest[H].to_quaternion().inverted()
        hand_axis=dh@l0;full=hand_axis.rotation_difference(fore)@dh
        normal=upper.cross(fore).normalized()
        du=frame(upper,normal)@frame(u0,n0).inverted()
        # Derive the true hinge roll after smoothing; both endpoints use the
        # same actual forearm direction, so the wrist has no residual axial kink.
        hinge=frame(fore,normal)@frame(l0,n0).inverted()
        roll=twist(full@hinge.inverted(),fore.normalized())
        if previous_roll is not None:roll=previous_roll+(roll-previous_roll+math.pi)%(2*math.pi)-math.pi
        previous_roll=roll
        uq=ref[U].to_quaternion().slerp(du@rest[U].to_quaternion(),weight)
        old_u=rest[L].translation-rest[U].translation
        uq=((uq@rest[U].to_quaternion().inverted()@old_u).rotation_difference(upper)@uq).normalized()
        lq=ref[L].to_quaternion().slerp(full@rest[L].to_quaternion(),weight)
        lq=((lq@rest[L].to_quaternion().inverted()@l0).rotation_difference(fore)@lq).normalized()
        pose[C]=ref[C].copy();pose[C].translation+=s-s0
        pose[U]=rigid(s,uq);pose[L]=rigid(e,lq)
        for stem,origin,old_origin,segment,deform in (('upperarm',s,s0,upper,du),('lowerarm',e,e0,fore,hinge)):
            native=U if stem=='upperarm' else L
            source_segment=ref[L].translation-ref[U].translation if stem=='upperarm' else ref[H].translation-ref[L].translation
            carry=source_segment.rotation_difference(segment)
            for index in ('01','02'):
                n=stem+'_twist_'+index+'_l'
                goal=deform
                if stem=='lowerarm':goal=Quaternion(fore.normalized(),roll*STATIONS[n])@hinge
                target_q=goal@rest[n].to_quaternion()
                q=(carry@ref[n].to_quaternion()).slerp(target_q,weight)
                fraction=(rest[n].translation-rest[native].translation).dot((u0 if stem=='upperarm' else l0).normalized())/(L1 if stem=='upperarm' else L2)
                pose[n]=rigid(origin+segment*fraction,q)
    # Every hand/finger, right-arm, weapon and helper track is the original V6.
    fore=pose[H].translation-pose[L].translation
    dq=pose[H].to_quaternion()@rest[H].to_quaternion().inverted()
    dl=pose[L].to_quaternion()@rest[L].to_quaternion().inverted()
    if i%15==0 or i in (45,52,53):rows.append({'source_seconds':t,'weight':weight,
        'wrist_bend_deg':math.degrees(fore.angle(dq@l0)),
        'wrist_twist_deg':math.degrees(twist(dq@dl.inverted(),fore.normalized())),
        'shoulder_shift_cm':100*(pose[U].translation-ref[U].translation).length})
    poses.append(pose)
poses[0]=copy.deepcopy(source[0]);poses[-1]=copy.deepcopy(source[-1])
name='A_Warhammer_QuickCombat';bake(name,poses,FPS)
scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(P/'Warhammer_QuickCombat_LeftWristV7_Editable.blend'))
receipt={'revision':'HeadThrustLeftWristV7_20261015','clips':[name],'fps':FPS,'seconds':DURATION,
    'source':str(SOURCE),'runtime_seconds':.72,'contact_seconds':.28,'forward_stroke_m':.34,
    'changed_bones':sorted(affected),'hand_weapon_right_arm':'original V6 component-space transforms retained',
    'method':'native hinge, continuous forearm roll distributed along skin stations, shoulder support, fixed hand and bone lengths',
    'source_chain_samples':rows,'runtime_tested':False,'preview_rendered':False}
(P/'authored.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('LEFT_WRIST_AUTHORED',json.dumps(rows))
