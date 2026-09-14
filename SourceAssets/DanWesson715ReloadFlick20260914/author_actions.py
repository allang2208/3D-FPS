"""Author left-opening 715 reloads, right-hand wrist flicks and stable grips.

Replace only reload clips. Keep the current skeleton, mesh, action lengths,
ammunition contacts and authored firing-axis correction. No test or rendering.
"""
import bpy,math,json
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion,Euler
OUT=Path(__file__).parent
SRC=OUT.parent/'DanWesson715Upgrade20260914'
library=(SRC/'author_actions.py').read_text(encoding='utf-8').split("events={'open':",1)[0]
library=library.replace('DanWesson715_Hero_Editable.blend','DanWesson715_Upgrade_Editable.blend')
saved_file=__file__;__file__=str(SRC/'author_actions.py')
exec(compile(library,__file__,'exec'),globals())
__file__=saved_file;O=OUT
(O/'Animations').mkdir(exist_ok=True)
inputs=json.loads((O/'authoring-inputs.json').read_text(encoding='utf-8'))
geometry=json.loads((SRC/'author_inputs.json').read_text(encoding='utf-8'))
BEGIN=.55;STEP=1.15;VISIBLE=.56;SEAT=.91;TAIL=.70
finger_names=[n for n in names if n.endswith('_l') and n.startswith(('thumb','index','middle','ring','pinky'))]
rest_hand={n:rest['hand_l'].inverted()@rest[n] for n in finger_names}
idle_hand={n:idle['hand_l'].inverted()@idle[n] for n in finger_names}
tip_local={f:Vector(inputs['bones'][f+'_03_l']['skin_tip_local']) for f in ['thumb','index','middle','ring','pinky']}
forward=rest_hand['middle_01_l'].translation.normalized()
side=(rest_hand['index_01_l'].translation-rest_hand['pinky_01_l'].translation).normalized()
# Skin/palm side in this Manny hand: curl toward +hand-Y, not a display bone tail.
palm=-side.cross(forward).normalized()
axes={}
for family in ['thumb','index','middle','ring','pinky']:
    for j in range(1,4):
        n=f'{family}_{j:02}_l'
        start=rest_hand[n].translation
        end=rest_hand[f'{family}_{j+1:02}_l'].translation if j<3 else rest_hand[n]@tip_local[family]
        flex=(end-start).normalized().cross(palm).normalized()
        q=rest_hand[n].to_quaternion().inverted()
        axes[n]=(q@flex,q@palm,q@forward)

def finger_pose(family,angles):
    result={}
    for j in range(1,4):
        n=f'{family}_{j:02}_l'
        local=rest_hand[n] if j==1 else rest_hand[parent[n]].inverted()@rest_hand[n]
        flex,splay,oppose=axes[n]
        q=Quaternion(flex,angles[j-1])
        if j==1:
            q=Quaternion(splay,angles[3])@q
            if family=='thumb':q=Quaternion(oppose,angles[4])@q
        result[n]=(result[parent[n]]@local if j>1 else local)@q.to_matrix().to_4x4()
    return result

def fit_finger(family,target,initial):
    # Author one fixed hand pose with anatomical DOFs; never run unconstrained
    # per-frame FABRIK on arbitrary Blender display tails.
    bounds=[(.15,1.10),(.20,1.50),(.10,.95),(-.25,.25)]
    if family=='thumb':bounds=[(-.15,.65),(-.10,1.05),(.05,.90),(-.65,.65),(-.25,1.25)]
    angles=list(initial)
    def cost(a):
        p=finger_pose(family,a);tip=p[family+'_03_l']@tip_local[family]
        return (tip-target).length_squared*1e6+sum((x-y)**2 for x,y in zip(a,initial))*.08
    for step in [.18,.08,.035,.014,.005,.0015]:
        for _ in range(14):
            changed=False
            for i,(lo,hi) in enumerate(bounds):
                best=cost(angles);value=angles[i]
                for direction in [-1,1]:
                    trial=angles.copy();trial[i]=max(lo,min(hi,angles[i]+direction*step))
                    score=cost(trial)
                    if score<best:best=score;value=trial[i]
                if value!=angles[i]:angles[i]=value;changed=True
            if not changed:break
    return finger_pose(family,angles),angles

templates={};grip_frames={};grip_centers={};grip_parameters={}
for kind,width in [('cartridge',.0104),('loader',.040)]:
    center=Vector((.112,.059,-.037))
    span=Vector((0,-.84,-.54)).normalized()
    template={n:m.copy() for n,m in rest_hand.items()};params={}
    for family,sign,initial in [('index',-1,[.63,1.0,.55,.02]),('thumb',1,[.12,.3,.25,-.1,.60])]:
        pose,angles=fit_finger(family,center+span*(width*.5*sign),initial)
        template.update(pose);params[family]=angles
    for family,values in [('middle',[.58,.88,.48,.03]),('ring',[.65,1.02,.58,.01]),('pinky',[.70,1.04,.58,-.03])]:
        # Remaining fingers fold softly into the palm and do not chase the round.
        template.update(finger_pose(family,values))
    a=template['thumb_03_l']@tip_local['thumb'];b=template['index_03_l']@tip_local['index']
    contact=(a+b)*.5;span=(a-b).normalized()
    approach=contact.normalized();approach=(approach-span*approach.dot(span)).normalized()
    normal=span.cross(approach).normalized()
    templates[kind]=template;grip_centers[kind]=contact
    grip_frames[kind]=Matrix((span,approach,normal)).transposed().to_quaternion()
    grip_parameters[kind]={'angles':params,'skin_contact_hand':list(contact),'aperture_m':(a-b).length}

relaxed={n:m.copy() for n,m in rest_hand.items()}
for family,values in [('thumb',[.06,.15,.15,-.06,.20]),('index',[.18,.32,.18,.03]),('middle',[.30,.48,.26,.01]),('ring',[.40,.58,.30,.01]),('pinky',[.45,.62,.34,-.02])]:
    relaxed.update(finger_pose(family,values))

def apply_hand_shape(p,shape,weight):
    # Blend local FK rotations so bone offsets/lengths remain the source values.
    H=p['hand_l']
    for n in finger_names:
        pn=parent[n]
        A=idle_hand[pn].inverted()@idle_hand[n] if pn in idle_hand else idle_hand[n]
        B=shape[pn].inverted()@shape[n] if pn in shape else shape[n]
        loc,qa,scale=A.decompose();qb=B.to_quaternion()
        local=Matrix.LocRotScale(loc,qa.slerp(qb,weight),scale)
        p[n]=(p[pn] if pn in finger_names else H)@local

def blend_shapes(a,b,w):
    result={}
    for n in finger_names:
        pn=parent[n]
        A=a[pn].inverted()@a[n] if pn in a else a[n]
        B=b[pn].inverted()@b[n] if pn in b else b[n]
        local=mix(A,B,w)
        result[n]=(result[pn]@local if pn in result else local)
    return result

def grasp(point,axis=Vector((0,-1,0)),kind='cartridge',reach=Vector((-.50,-.80,.32))):
    approach=reach.normalized()
    span=approach.cross(axis).normalized()
    approach=(approach-span*approach.dot(span)).normalized()
    normal=span.cross(approach).normalized()
    q=Matrix((span,approach,normal)).transposed().to_quaternion()@grip_frames[kind].inverted()
    return Matrix.LocRotScale(Vector(point)-q@grip_centers[kind],q,Vector((1,1,1)))

def hand_path(a,b,w):
    # Source curves retain timing intent; a bounded, explicitly leftward arc
    # supplies clearance without donor wrist/finger rotations at contact.
    H=mix(a,b,smooth(w));H.translation+=Vector((.012,0,-.010))*math.sin(math.pi*max(0,min(1,w)))
    return H

def wrist_motion(t,close_begin,finish,empty=False,speed=False):
    # +model-X is player LEFT (Blender -Y -> UE +Y -> camera yaw -90).
    # Left flick: preload, rapid throw, settle. Right flick: clear support hand,
    # throw the wrist back, snap the crane shut, settle into the original grip.
    load_weight=smooth(t/.50)*(1-smooth((t-close_begin)/(finish-close_begin)))
    opening_bank=key_sample([(0,0),(.12,-5),(.21,-5),(.32,27),(.42,17),(.55,0)],t)
    opening_yaw=key_sample([(0,0),(.20,-2),(.32,13),(.48,0)],t)
    opening_shift=key_sample([(0,0),(.20,-.005),(.32,.028),(.50,0)],t)
    q=t-close_begin
    closing_bank=key_sample([(0,0),(.10,7),(.25,-28),(.37,-9),(.55,0)],q)
    closing_yaw=key_sample([(0,0),(.11,2),(.25,-11),(.40,-3),(.61,0)],q)
    closing_shift=key_sample([(0,0),(.10,.006),(.25,-.026),(.42,-.006),(.63,0)],q)
    pitch=18*load_weight
    if speed:
        pitch+=key_sample([(0,0),(.50,0),(.82,-71),(1.10,-71),(1.43,0),(finish,0)],t)
    return idle['WPN_root']@Matrix.LocRotScale(Vector((.016*load_weight+opening_shift+closing_shift,.048*load_weight,.020*load_weight)),Euler((math.radians(pitch),math.radians(8*load_weight+opening_bank+closing_bank),math.radians(7*load_weight+opening_yaw+closing_yaw)),'XYZ').to_quaternion(),Vector((1,1,1)))

hidden=Matrix.Diagonal((.0001,.0001,.0001,1))
moving=['WPN_Crane','WPN_Cylinder','WPN_Extractor','WPN_SOCKET_Magazine','WPN_SOCKET_Eject']+[f'WPN_Case_{i}' for i in range(6)]+[f'WPN_Round_{i}' for i in range(6)]
rear_points={}
for i in range(6):
    part=next(row for row in geometry['parts'] if f'WPN_Case_{i}' in row['bones'])
    lo,hi=part['min'],part['max']
    rear_points[i]=Vector(((lo[0]+hi[0])*.5,hi[1]-.003,(lo[2]+hi[2])*.5))

def begin_pose(t,close_begin,finish,speed=False):
    old={n:m.copy() for n,m in idle.items()};p={n:old.get(n,rest[n]).copy() for n in names}
    G=wrist_motion(t,close_begin,finish,speed=speed)
    hand_at(p,old,'r',G@rightlocal)
    p['WPN_root']=G
    for n,L in gunlocal.items():
        if n!='WPN_root':p[n]=G@L
    p['WPN_Loader']=G@gunlocal['WPN_Loader']@hidden
    amount=smooth((t-.25)/.23)*(1-smooth((t-close_begin-.12)/.25))
    D=mech('WPN_Crane','Y',math.radians(78)*amount)
    for n in moving:p[n]=G@D@gunlocal[n]
    return p,old,G,D

def clearance(D):
    C=(D@gunlocal['WPN_Cylinder']).translation
    return grasp(C+Vector((.100,.120,-.070)))

def open_hand(t,D):
    clear=clearance(D)
    return hand_path(leftlocal,clear,t/.27) if t<.27 else clear

def close_hand(q,D,start=None):
    clear=clearance(D)
    if q<.12:return hand_path(start if start is not None else clear,clear,q/.12)
    if q<.40:return clear
    return hand_path(clear,leftlocal,(q-.40)/.30)

def pose_single(start,count,t):
    close_begin=BEGIN+STEP*count;finish=close_begin+TAIL
    p,old,G,D=begin_pose(t,close_begin,finish)
    clear=clearance(D);shape=relaxed;shape_weight=smooth(t/.22)*(1-smooth((t-close_begin-.40)/.30))
    approach_point=D@(rear_points[start]+Vector((0,.058,0)))
    approach=grasp(approach_point)
    if t<.40:H=open_hand(t,D)
    elif t<BEGIN:H=hand_path(clear,approach,(t-.40)/.15)
    elif t<close_begin:
        cycle=min(count-1,int((t-BEGIN)/STEP));phase=t-BEGIN-cycle*STEP;index=start+cycle
        rear=rear_points[index];bn=f'WPN_Case_{index}'
        pull=.057*smooth((phase-.07)/.16)
        mouth=D@rear;extract=D@(rear+Vector((0,pull,0)))
        # Model-positive-X fetch goes to the player's left and below the view.
        incoming=Vector((key_sample([(.56,.125),(.73,.025),(.82,0)],phase),key_sample([(.56,.205),(.73,.080),(.91,0)],phase),key_sample([(.56,-.235),(.73,-.045),(.82,0)],phase)))
        round_point=D@rear+incoming
        pouch=D@rear+Vector((.125,.205,-.235))
        pre=grasp(D@(rear+Vector((0,.058,0))))
        if phase<.07:
            H=hand_path(pre,grasp(mouth),phase/.07);shape=blend_shapes(relaxed,templates['cartridge'],smooth(phase/.07))
        elif phase<.23:H=grasp(extract);shape=templates['cartridge']
        elif phase<.41:
            H=hand_path(grasp(D@(rear+Vector((0,.057,0)))),grasp(pouch),(phase-.23)/.18)
            shape=blend_shapes(templates['cartridge'],relaxed,smooth((phase-.23)/.10))
        elif phase<.56:
            H=grasp(pouch);shape=blend_shapes(relaxed,templates['cartridge'],smooth((phase-.44)/.10))
        elif phase<.94:H=grasp(round_point);shape=templates['cartridge']
        else:
            # Release and withdraw along the chamber axis before changing holes.
            next_index=min(start+count-1,index+1)
            next_rear=rear_points[next_index]
            next_pre=grasp(D@(next_rear+Vector((0,.058,0))))
            retreat=grasp(D@(rear+Vector((0,.058,0))))
            if phase<1.05:H=hand_path(grasp(mouth),retreat,(phase-.94)/.11)
            else:H=hand_path(retreat,next_pre,(phase-1.05)/.10)
            shape=blend_shapes(templates['cartridge'],relaxed,smooth((phase-.94)/.09))
        Cpose=G@D@gunlocal[bn]
        if phase<.23:Cpose=G@D@Matrix.Translation((0,pull,0))@gunlocal[bn]
        elif phase<.40:
            fall=phase-.23;Cpose=G@D@Matrix.Translation((0,.057+.18*fall,0))@gunlocal[bn]
            Cpose.translation+=Vector((0,0,-3.5*fall*fall))
        elif phase<VISIBLE:Cpose=Cpose@hidden
        elif phase<SEAT:Cpose=G@Matrix.Translation(incoming)@D@gunlocal[bn]
        p[bn]=Cpose;p[f'WPN_Round_{index}']=Cpose@gunlocal[bn].inverted()@gunlocal[f'WPN_Round_{index}']
    else:
        last_pre=grasp(D@(rear_points[start+count-1]+Vector((0,.058,0))))
        H=close_hand(t-close_begin,D,last_pre)
    hand_at(p,old,'l',G@H);apply_hand_shape(p,shape,shape_weight)
    return p

def pose_speed(kind,t):
    # Reuse the accepted speedloader contact seconds and distinct empty duration.
    duration=3.85 if kind=='reload_empty' else 3.6;u=t*3.6/duration
    p,old,G,D=begin_pose(u,2.68,3.6,speed=True)
    # Closure is 3.05: close_begin + .37, matching the existing cue contract.
    lift=smooth((u-.85)/.18)*(1-smooth((u-1.07)/.16))
    p['WPN_Extractor']=G@D@Matrix.Translation((0,.028*lift,0))@gunlocal['WPN_Extractor']
    travel=key_sample([(1.28,.19),(1.70,.095),(2.20,.017),(2.42,0),(2.53,.012),(2.78,.20)],u)
    down=key_sample([(1.28,-.22),(1.72,-.075),(2.12,0),(2.53,0),(2.78,-.22)],u)
    sideways=key_sample([(1.28,.10),(1.90,.020),(2.12,0),(2.53,0),(2.78,.10)],u)
    load_offset=Vector((sideways,travel-.0135,down))
    if 1.40<=u<=2.76:p['WPN_Loader']=G@Matrix.Translation(load_offset)@D@gunlocal['WPN_Loader']
    loader_point=D@Vector((0,0,.03092))+load_offset
    load=grasp(loader_point,kind='loader')
    eject_point=D@Vector((0,-.1195+.028*lift,.03092))
    eject=hand_goal(eject_point,(0,1,0),(0,0,1),'thumb')
    eject.translation=eject_point-eject.to_quaternion()@(relaxed['thumb_03_l']@tip_local['thumb'])
    shape=relaxed
    if u<.48:H=open_hand(u,D)
    elif u<.85:H=hand_path(clearance(D),eject,(u-.48)/.37)
    elif u<1.10:H=eject
    elif u<1.40:H=hand_path(eject,load,(u-1.10)/.30);shape=blend_shapes(relaxed,templates['loader'],smooth((u-1.27)/.13))
    elif u<2.68:H=load;shape=templates['loader']
    elif u<2.80:
        H=hand_path(load,clearance(D),(u-2.68)/.12);shape=blend_shapes(templates['loader'],relaxed,smooth((u-2.68)/.12))
    elif u<3.10:H=clearance(D)
    else:H=hand_path(clearance(D),leftlocal,(u-3.10)/.50)
    hand_at(p,old,'l',G@H)
    apply_hand_shape(p,shape,smooth(u/.22)*(1-smooth((u-3.10)/.50)))
    for i in range(6):
        bn=f'WPN_Case_{i}';Cpose=G@D@gunlocal[bn]
        if .85<=u<1.30:
            fall=max(0,u-1.03);Cpose=G@D@Matrix.Translation((0,.036*smooth((u-.85)/.18)+fall*.16,0))@gunlocal[bn];Cpose.translation+=Vector((0,0,-1.2*fall*fall))
        elif 1.30<=u<1.44:Cpose=Cpose@hidden
        elif 1.44<=u<2.42:Cpose=G@Matrix.Translation((sideways,travel,down))@D@gunlocal[bn]
        p[bn]=Cpose;p[f'WPN_Round_{i}']=Cpose@gunlocal[bn].inverted()@gunlocal[f'WPN_Round_{i}']
    return p

def bake(kind,duration,sampler):
    frames=[i*.5 for i in range(round(duration*120)+1)];rows=[];previous={}
    for f in frames:
        p=sampler(f/60);row={}
        for n in names:
            basis=lr[n].inverted()@(p[parent[n]].inverted_safe()@p[n] if parent[n] else p[n]);loc,q,scale=basis.decompose()
            if n in previous and previous[n].dot(q)<0:q.negate()
            previous[n]=q.copy();row[n]=(loc,q,scale)
        rows.append(row)
    a=bpy.data.actions.new('DW715_Flick_'+kind);a.use_fake_user=True;rig.animation_data_create();rig.animation_data.action=a
    for n in names:
        rig.pose.bones[n].rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):rig.pose.bones[n].keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for c in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves}
    for n in names:
        for prop,field,size in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(size):
                c=curves[(f'pose.bones["{n}"].{prop}',axis)];c.keyframe_points.clear();c.keyframe_points.add(len(frames))
                c.keyframe_points.foreach_set('co',[v for f,row in zip(frames,rows) for v in (f,row[n][field][axis])])
                for k in c.keyframe_points:k.interpolation='LINEAR'
                c.update()
    rig.animation_data.action_slot=a.slots[0];s.frame_start=0;s.frame_end=round(duration*60);s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.hide_set(False);rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(O/'Animations'/f'A_DW715_{kind}.fbx'),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_step=.5,bake_anim_simplify_factor=0)
    print('DW715_FLICK_EXPORTED',kind,flush=True)
    return a

actions={};manifest={'player_left_axis':'+model-X','crane_degrees':78,'sample_rate':120,'grip_templates':grip_parameters,'chamber_contact_points':{str(i):list(v) for i,v in rear_points.items()},'clips':{},'testing':'Not performed; source authoring/export/import only'}
for start in range(6):
    for count in range(1,7-start):
        kind=f'single_{start}_{count}';duration=BEGIN+count*STEP+TAIL
        actions[kind]=bake(kind,duration,lambda t,a=start,b=count:pose_single(a,b,t))
        manifest['clips'][kind]={'duration':duration,'destination':'/Game/Weapons/DanWesson715/SingleLoad20260914/Animations','open':.48,'seats':[BEGIN+i*STEP+SEAT for i in range(count)],'close':BEGIN+count*STEP+.37}
for kind,duration in [('reload',3.6),('reload_empty',3.85)]:
    actions[kind]=bake(kind,duration,lambda t,k=kind:pose_speed(k,t))
    manifest['clips'][kind]={'duration':duration,'destination':'/Game/Weapons/DanWesson715/Upgrade20260914/Animations','events_normal_source':{'open':.48,'eject':1.03,'insert':2.20,'seat':2.42,'close':3.05}}
rig.animation_data.action=actions['single_0_6'];rig.animation_data.action_slot=actions['single_0_6'].slots[0];s.frame_start=0;s.frame_end=489;s.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'DanWesson715_ReloadFlick_Editable.blend'))
(O/'animation.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('DW715_FLICK_AUTHORING_COMPLETE',flush=True)
