"""Author an original right-shoulder back draw on the accepted V22 Manny rig.

Right hand reaches behind, closes on the hilt, draws over the right shoulder;
left hand joins only after the sword arrives in front. No mesh/weight changes.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

P=Path(__file__).parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
FPS=480;DURATION=1.20;ONE=Vector((1,1,1))
inputs=json.loads((P/'authoring_inputs.json').read_text(encoding='utf-8'))
end={n:Matrix(m) for n,m in inputs['end_pose'].items()}
SOURCE=P.parent/inputs['source']
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
s=bpy.context.scene;r=bpy.data.objects['SK_RuneSword_Rig']
rest={b.name:b.matrix_local.copy() for b in r.data.bones}
parent={b.name:b.parent.name if b.parent else None for b in r.data.bones}
local={n:rest[parent[n]].inverted()@m if parent[n] else m for n,m in rest.items()}
grips={side:end['WPN_root'].inverted()@end['hand_'+side] for side in ('l','r')}
finger_names={side:[n for n in rest if n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky'))] for side in ('l','r')}
finger_local={n:end[parent[n]].inverted()@end[n] for names in finger_names.values() for n in names}

def ease(t):
    t=max(0.,min(1.,t));return t*t*t*(t*(t*6.-15.)+10.)

def mix(a,b,t):
    loc=a.translation.lerp(b.translation,t)
    return Matrix.LocRotScale(loc,a.to_quaternion().slerp(b.to_quaternion(),t),ONE)

def rot(x,y,z):
    return (Matrix.Rotation(math.radians(x),4,'X')@Matrix.Rotation(math.radians(y),4,'Y')@Matrix.Rotation(math.radians(z),4,'Z')).to_quaternion()

def sword_at_hand(position,q):
    # Keep the accepted right-hand contact rigid after the grasp. Position the
    # wrist first, then recover the guard pivot from its existing hilt offset.
    return Matrix.LocRotScale(Vector(position)-q@grips['r'].translation,q,ONE)

BACK=sword_at_hand((.245,-.115,.070),rot(160,16,95))
LIFT=sword_at_hand((.35,-.045,.220),rot(148,25,95))
IDLE=end['WPN_root']
READY_HAND=end['hand_r'].translation
FREE_R=Matrix.LocRotScale(Vector((.28,.12,-.43)),end['hand_r'].to_quaternion(),ONE)
FREE_L=Matrix.LocRotScale(Vector((-.265,.16,-.41)),end['hand_l'].to_quaternion(),ONE)
REACH_R=Matrix.LocRotScale(Vector((.38,.035,-.055)),(BACK@grips['r']).to_quaternion(),ONE)

def cubic(a,b,c,d,u):
    return a*(1-u)**3+b*(3*(1-u)**2*u)+c*(3*(1-u)*u*u)+d*u**3

def q_cubic(a,b,c,d,u):
    ab=a.slerp(b,u);bc=b.slerp(c,u);cd=c.slerp(d,u)
    return ab.slerp(bc,u).slerp(bc.slerp(cd,u),u)

def weapon(t):
    if t<=.32:return BACK.copy()
    if t<.54:return mix(BACK,LIFT,ease((t-.32)/.22))
    if t<1.08:
        u=ease((t-.54)/.54)
        h=cubic(Vector((.35,-.045,.220)),Vector((.435,.105,.25)),Vector((.355,.44,-.015)),READY_HAND,u)
        q=q_cubic(LIFT.to_quaternion(),rot(70,34,110),rot(-24,18,140),IDLE.to_quaternion(),u)
        return sword_at_hand(h,q)
    return IDLE.copy()

def hand_targets(t,W):
    right_grip=W@grips['r'];left_grip=W@grips['l']
    if t<.15:right=mix(FREE_R,REACH_R,ease(t/.15))
    elif t<.29:right=mix(REACH_R,BACK@grips['r'],ease((t-.15)/.14))
    else:right=right_grip
    left_approach=left_grip.copy()
    left_approach.translation+=Vector((-.07,-.025,-.035))*(1.-ease((t-.88)/.15))
    left=mix(FREE_L,left_approach,ease((t-.68)/.35))
    return {'r':right,'l':left}

def segment_frame(side,H,t):
    un,fn,hn=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
    A=end[un].translation.copy();T=H.translation
    lift=ease(t/.22)*(1.-ease((t-.63)/.40)) if side=='r' else .0
    A+=Vector((.015*lift,.012*lift,.040*lift))
    ru=rest[fn].translation-rest[un].translation
    rf=rest[hn].translation-rest[fn].translation
    l1,l2=ru.length,rf.length
    to_hand=T-A;dist=to_hand.length;axis=to_hand.normalized()
    # Move the shoulder only when the authored wrist exceeds reach; never
    # stretch either arm segment to manufacture a long sword extraction.
    if dist>l1+l2-.015:A+=axis*(dist-(l1+l2-.015));dist=(T-A).length
    hand_deform=H.to_quaternion()@rest[hn].to_quaternion().inverted()
    ideal_elbow=T-(hand_deform@rf.normalized())*l2
    wanted=ideal_elbow-A;wanted-=axis*wanted.dot(axis)
    outward=Vector((-.75 if side=='l' else .75,.08,-1.))
    outward-=axis*outward.dot(axis);outward.normalize()
    pole=(wanted/l2+outward*.32).normalized()
    # Meet the actual accepted idle elbow, not an independently refit idle.
    final_pole=end[fn].translation-A;final_pole-=axis*final_pole.dot(axis)
    if final_pole.length>.0001:pole=pole.lerp(final_pole.normalized(),ease((t-.88)/.20)).normalized()
    along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    E=A+axis*along+pole*math.sqrt(max(0.,l1*l1-along*along))
    fore_axis=(T-E).normalized();upper_axis=(E-A).normalized()
    fore_deform=(hand_deform@rf.normalized()).rotation_difference(fore_axis)@hand_deform
    fq=fore_deform@rest[fn].to_quaternion()
    # V21/V22 complete-segment transport: no independent upper-arm roll frame.
    uq=(fore_deform@ru.normalized()).rotation_difference(upper_axis)@fore_deform@rest[un].to_quaternion()
    settle=ease((t-.99)/.21)
    end_upper_axis=(end[fn].translation-end[un].translation).normalized()
    end_fore_axis=(end[hn].translation-end[fn].translation).normalized()
    end_uq=end_upper_axis.rotation_difference(upper_axis)@end[un].to_quaternion()
    end_fq=end_fore_axis.rotation_difference(fore_axis)@end[fn].to_quaternion()
    uq=uq.slerp(end_uq,settle)
    fq=fq.slerp(end_fq,settle)
    return Matrix.LocRotScale(A,uq,ONE),Matrix.LocRotScale(E,fq,ONE)

def pose_at(t):
    if t>=DURATION:return {n:m.copy() for n,m in end.items()}
    p={n:m.copy() for n,m in end.items()};W=weapon(t);hands=hand_targets(t,W)
    p['WPN_root']=W
    for n in ('Blade_Base','Blade_Tip'):p[n]=W@end['WPN_root'].inverted()@end[n]
    for side,H in hands.items():
        un,fn,hn=[n+'_'+side for n in ('upperarm','lowerarm','hand')]
        p[un],p[fn]=segment_frame(side,H,t)
        upper_delta=p[un]@end[un].inverted();fore_delta=p[fn]@end[fn].inverted()
        p['clavicle_'+side]=upper_delta@end['clavicle_'+side]
        for prefix,delta in (('upperarm',upper_delta),('lowerarm',fore_delta)):
            for i in ('01','02'):
                n=prefix+'_twist_'+i+'_'+side
                p[n]=delta@end[n]
        p[hn]=H
        close=ease((t-.21)/.10) if side=='r' else ease((t-.92)/.14)
        for n in finger_names[side]:
            loc,q,scale=finger_local[n].decompose()
            relaxed=local[n].to_quaternion().slerp(q,.42)
            p[n]=p[parent[n]]@Matrix.LocRotScale(loc,relaxed.slerp(q,close),scale)
    return p

s.render.fps=FPS;s.render.fps_base=1.
name='A_RuneSword_Equip'
if name in bpy.data.actions:
    bpy.data.actions[name].name='REF_PRE_V23_'+name
action=bpy.data.actions.new(name);action.use_fake_user=True
r.animation_data.action=action;s.frame_start=0;s.frame_end=round(DURATION*FPS)
previous={}
for f in range(s.frame_end+1):
    s.frame_set(f);p=pose_at(f/FPS)
    for b in r.pose.bones:
        m=p[parent[b.name]].inverted()@p[b.name] if parent[b.name] else p[b.name]
        loc,q,scale=(local[b.name].inverted()@m).decompose()
        if b.name in previous and q.dot(previous[b.name])<0:q.negate()
        previous[b.name]=q.copy()
        b.rotation_mode='QUATERNION';b.location=loc;b.rotation_quaternion=q;b.scale=scale
        for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f,group=b.name)
r.animation_data.action_slot=action.slots[0]
for layer in action.layers:
    for strip in layer.strips:
        for bag in strip.channelbags:
            for curve in bag.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
bpy.ops.export_scene.fbx(filepath=str(OUT/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0)
s.frame_set(0);bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'AzureRunesword_Manny_Editable.blend'))
(P/'authoring.json').write_text(json.dumps({'revision':'BackDrawEquipV23','source':str(SOURCE),
    'clip':name,'fps':FPS,'frames':[0,576],'duration':DURATION,'loop':False,
    'phases':{'reach_behind':[0,.29],'right_grasp':[.21,.31],'draw_up':[.32,.54],
              'bring_forward':[.54,1.08],'left_join':[.68,1.03],'left_close':[.92,1.06],'settle_end':1.20},
    'contact':'Right-hand hilt frame stays fixed after .29; left joins the accepted lower grip',
    'source_motion':'Original back-draw adaptation; no downloaded spin/flourish clip',
    'scope':'First-person shoulder-back draw illusion; no third-person back scabbard or sheath collision asset',
    'verification':'Not rendered or play-tested; per user default no-tests rule'},indent=2),encoding='utf-8')
print('RUNESWORD_V23_EQUIP_AUTHORED',flush=True)
