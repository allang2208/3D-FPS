"""Video-directed PKM equip and an overhand empty-reload charge contact.

Author only the requested clips on Reload16, retaining its mechanical clock.
No mesh export, gameplay tests or rendering. Source units are meters.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion, Euler

O=Path(__file__).parent;R=O.parent;FPS=120;EQUIP=.90
fit=Matrix(json.loads((R/'Animation03/animation_manifest.json').read_text())['fit_matrix'])
donor=json.loads((R/'Reload16/sources.json').read_text())['donor']
grips=json.loads((R/'Melee24/grips.json').read_text())
bpy.context.preferences.filepaths.save_version=0

def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(x*(x*6-15)+10)
def ramp(t,a,b):return smooth((t-a)/(b-a))
def mix(a,b,t):
    p,q,s=a.decompose();p2,q2,s2=b.decompose()
    return Matrix.LocRotScale(p.lerp(p2,t),q.slerp(q2,t),s.lerp(s2,t))
def frame(axis,normal):
    x=Vector(axis).normalized();z=Vector(normal);z-=x*z.dot(x)
    if z.length<1e-8:z=x.orthogonal()
    z.normalize();return Matrix((x,z.cross(x).normalized(),z)).transposed()
def interpolate(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for i,((a,p),(b,q)) in enumerate(zip(keys,keys[1:])):
        if t<=b:
            # Continuous velocities across lifting keys, not repeated ease-to-stop.
            k=(t-a)/(b-a);span=b-a
            before=keys[i-1] if i else (a,p)
            after=keys[i+2] if i+2<len(keys) else (b,q)
            v0=(q-before[1])/(b-before[0]) if i else p*0
            v1=(after[1]-p)/(after[0]-a) if i+2<len(keys) else q*0
            return p*(2*k**3-3*k*k+1)+v0*span*(k**3-2*k*k+k)+q*(-2*k**3+3*k*k)+v1*span*(k**3-k*k)
    return keys[-1][1]
def action(a):
    r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
def sample(a,t,fps=FPS):
    action(a);f=t*fps;s.frame_set(int(f),subframe=f%1);bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in r.pose.bones}
def finger_q(pose,side):
    return {n:(localrest[n].inverted()@pose[parents[n]].inverted()@pose[n]).to_quaternion() for n in fingers[side]}
def finger_pose(pose,side,H,qs):
    pose['hand_'+side]=H
    for n in fingers[side]:pose[n]=pose[parents[n]]@localrest[n]@qs[n].to_matrix().to_4x4()

def solve_arm(pose,reference,side,H,coherence,shoulder_shift=None):
    """One reach solution for shoulder/elbow/wrist; helpers follow whole segments."""
    un,ln,hn,cn=[v+'_'+side for v in ('upperarm','lowerarm','hand','clavicle')]
    S0,E0,P0=[reference[n].translation.copy() for n in (un,ln,hn)]
    U0,L0=E0-S0,P0-E0;a,b=U0.length,L0.length
    S=S0+(shoulder_shift if shoulder_shift is not None else Vector())
    P=H.translation;v=P-S;d=v.length
    if d>(a+b)*.965:S+=v.normalized()*(d-(a+b)*.965)
    v=P-S;d=max(v.length,1e-6);axis=v.normalized()
    along=(a*a-b*b+d*d)/(2*d);radius=math.sqrt(max(0,a*a-along*along));center=S+axis*along
    refpole=E0-center;refpole-=axis*refpole.dot(axis)
    if refpole.length<1e-7:refpole=axis.orthogonal()
    refpole.normalize()
    handdelta=H.to_quaternion()@rest[hn].to_quaternion().inverted()
    restaxis=(rest[hn].translation-rest[ln].translation).normalized()
    foreaxis=handdelta@restaxis
    natural=-foreaxis+axis*foreaxis.dot(axis)
    if natural.length<1e-7:natural=refpole.copy()
    natural.normalize()
    angle=math.atan2(axis.dot(refpole.cross(natural)),refpole.dot(natural))
    # A continuous bounded elbow swivel; no winding around the shoulder/wrist.
    swivel=max(-math.radians(75),min(math.radians(75),angle))*.85*coherence
    E=center+(Quaternion(axis,swivel)@refpole)*radius
    U,L=E-S,P-E
    oldnormal=U0.cross(L0);normal=U.cross(L)
    uq=(frame(U,normal)@frame(U0,oldnormal).transposed()).to_quaternion()@reference[un].to_quaternion()
    carry=L0.rotation_difference(L)@reference[ln].to_quaternion()
    natural_q=foreaxis.rotation_difference(L.normalized())@handdelta@rest[ln].to_quaternion()
    fq=carry.slerp(natural_q,coherence)
    pose[cn]=reference[cn].copy();pose[cn].translation+=S-S0
    for main,origin,q in [(un,S,uq),(ln,E,fq)]:
        pose[main]=Matrix.LocRotScale(origin,q,reference[main].to_scale())
        for suffix in ('01','02'):
            n=main[:-2]+'_twist_'+suffix+'_'+side
            if n in rest:
                old=reference[main].inverted()@reference[n]
                complete=rest[main].inverted()@rest[n]
                pose[n]=pose[main]@mix(old,complete,coherence)
    pose[hn]=H
    if 'ik_hand_'+side in pose:pose['ik_hand_'+side]=H.copy()

def skin_pad_anchor(qs):
    """Fit to actual glove pad vertices on the two hook fingers, not bone centers."""
    fk={'hand_r':Matrix.Identity(4)}
    for n in fingers['r']:fk[n]=fk[parents[n]]@localrest[n]@qs[n].to_matrix().to_4x4()
    ob=bpy.data.objects['SK_Manny_Arms_Export'];mesh_to_rig=r.matrix_world.inverted()@ob.matrix_world
    names={g.index:g.name for g in ob.vertex_groups};pads=[]
    for digit in ('index','middle'):
        bone=digit+'_02_r';nextbone=digit+'_03_r'
        normal_local=rest[bone].to_3x3().inverted()@rest['hand_r'].to_3x3()@palm_normal
        toward=(fk[bone].to_3x3()@normal_local).normalized()
        target=fk[bone].translation.lerp(fk[nextbone].translation,.5)+toward*.006
        candidates=[]
        for vertex in ob.data.vertices:
            if not any(names[g.group]==bone and g.weight>.5 for g in vertex.groups):continue
            point=mesh_to_rig@vertex.co;posed=Vector();total=0.
            for group in vertex.groups:
                n=names[group.group]
                if n in fk:
                    posed+=(fk[n]@rest[n].inverted()@point)*group.weight;total+=group.weight
            if total>.95:candidates.append(posed/total)
        chosen=sorted(candidates,key=lambda p:(p-target).length_squared)[:8]
        if not chosen:raise RuntimeError('No charging-finger glove pad vertices: '+bone)
        pads.append(sum(chosen,Vector())/len(chosen))
    return sum(pads,Vector())/len(pads)

def bake(clip,poses,duration):
    name='A_PKM_'+('' if family=='base' else family+'_')+clip
    out=bpy.data.actions.new('PKM31_'+family+'_'+clip);out.use_fake_user=True;r.animation_data.action=out
    for bone in r.pose.bones:
        bone.rotation_mode='QUATERNION'
        for prop in ('location','rotation_quaternion','scale'):bone.keyframe_insert(prop,frame=0)
    curves={(c.data_path,c.array_index):c for layer in out.layers for strip in layer.strips for bag in strip.channelbags for c in bag.fcurves}
    for n in rest:
        values=[];previous=None
        for pose in poses:
            basis=localrest[n].inverted()@(pose[parents[n]].inverted()@pose[n] if parents[n] else pose[n])
            loc,q,scale=basis.decompose()
            if previous is not None and previous.dot(q)<0:q.negate()
            previous=q.copy();values.append((loc,q,scale))
        for prop,field,count in [('location',0,3),('rotation_quaternion',1,4),('scale',2,3)]:
            for axis in range(count):
                curve=curves[(f'pose.bones["{n}"].{prop}',axis)]
                curve.keyframe_points.clear();curve.keyframe_points.add(len(values))
                curve.keyframe_points.foreach_set('co',[v for i,row in enumerate(values) for v in (i,row[field][axis])])
                for k in curve.keyframe_points:k.interpolation='LINEAR'
                curve.update()
    action(out);s.render.fps=FPS;s.render.fps_base=1;s.frame_start=0;s.frame_end=len(poses)-1;s.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');r.hide_set(False);r.select_set(True);bpy.context.view_layer.objects.active=r
    dest=O/'Animations'/family;dest.mkdir(parents=True,exist_ok=True)
    bpy.ops.export_scene.fbx(filepath=str(dest/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_force_startend_keying=True,bake_anim_step=1,bake_anim_simplify_factor=0)
    records[family+'/'+clip]={'name':name,'action':out.name,'fps':FPS,'duration':duration,'frames':len(poses)}
    (O/'animations.json').write_text(json.dumps(records,indent=2))
    print('PKM31_EXPORTED',family,clip,flush=True)

records={};authoring={}
for family in ('base','vertical','canted','prism','angled'):
    source=R/'Reload16'/f'PKM_{family}_Reload_Editable.blend'
    bpy.ops.wm.open_mainfile(filepath=str(source),use_scripts=False)
    r=bpy.data.objects['PKM_Manny_Rig'];s=bpy.context.scene;r.data.pose_position='POSE'
    rest={b.name:b.matrix_local.copy() for b in r.data.bones};parents={b.name:b.parent.name if b.parent else None for b in r.data.bones}
    localrest={n:rest[parents[n]].inverted()@m if parents[n] else m.copy() for n,m in rest.items()}
    fingers={side:[n for n in rest if n.endswith('_'+side) and n.startswith(('thumb_','index_','middle_','ring_','pinky_'))] for side in ('l','r')}
    idle={n:Matrix(m) for n,m in grips[family]['idle'].items()}
    idle_q={side:finger_q(idle,side) for side in ('l','r')}
    W0=idle['WPN_root'];B=rest['WPN_root']@fit
    weapon={n for n in rest if n.startswith(('WPN_','PKM_','New_PKM_'))}
    # The actual right-hand donor retains its native metacarpals and thumb.
    dr={n:Matrix(m) for n,m in donor['rest'].items()};closed={n:Matrix(m) for n,m in donor['poses']['75'].items()};opened={n:Matrix(m) for n,m in donor['poses']['54'].items()}
    hook={};opening={}
    for n in fingers['r']:
        p=parents[n];lr=dr[p].inverted()@dr[n]
        hook[n]=(lr.inverted()@closed[p].inverted()@closed[n]).to_quaternion()
        opening[n]=(lr.inverted()@opened[p].inverted()@opened[n]).to_quaternion()
    Hi=rest['hand_r'].inverted();forward=(Hi@rest['middle_01_r'].translation).normalized()
    width=(Hi.to_3x3()@(rest['index_01_r'].translation-rest['pinky_01_r'].translation)).normalized()
    palm_normal=-forward.cross(width).normalized()
    semantic=frame(forward,palm_normal)
    # Overhand approach on PKM's right: fingers forward/down, palm toward receiver.
    hand_rotation=(frame((0,-.88,-.48),(1,0,0))@semantic.transposed()).to_quaternion()
    anchor=skin_pad_anchor(hook)
    # Outer working lug, not the long receiver-side slide rail.
    lug=Vector((-.060,.115,.0215))

    equip=[]
    grip=W0.inverted()@idle['hand_r'].translation
    for f in range(round(EQUIP*FPS)+1):
        t=f/FPS;p={n:m.copy() for n,m in idle.items()}
        pitch=interpolate(t,[(0,-72),(.16,-68),(.30,-48),(.51,-11),(.64,1.8),(.77,-.5),(.86,0),(.9,0)])
        roll=interpolate(t,[(0,12),(.2,8),(.43,-4),(.65,1),(.86,0)])
        yaw=interpolate(t,[(0,-6),(.26,-3),(.56,1.0),(.86,0)])
        shift=interpolate(t,[(0,Vector((-.025,.08,-.40))),(.15,Vector((-.025,.038,-.17))),(.30,Vector((-.012,.012,-.065))),(.51,Vector((.004,-.006,.009))),(.67,Vector((0,.002,-.003))),(.86,Vector())])
        local=Matrix.Translation(shift)@Matrix.Translation(grip)@Euler(tuple(math.radians(v) for v in (pitch,roll,yaw)),'XYZ').to_matrix().to_4x4()@Matrix.Translation(-grip)
        D=W0@local@W0.inverted()
        for n in weapon:p[n]=D@idle[n]
        for side in ('r','l'):
            H=D@idle['hand_'+side]
            reach=(1-ramp(t,.19,.39)) if side=='l' else 0.
            if side=='l':H.translation+=(D@W0).to_3x3()@Vector((.070,.050,-.035))*reach
            support=1-ramp(t,.67,.86)
            shoulder=(D@idle['upperarm_'+side]).translation-idle['upperarm_'+side].translation
            solve_arm(p,idle,side,H,support,shoulder*.25*support)
            qs={n:Quaternion().slerp(q,1-.68*reach) for n,q in idle_q[side].items()}
            finger_pose(p,side,H,qs)
        if t>=.86:p={n:m.copy() for n,m in idle.items()}
        equip.append(p)
    bake('equip',equip,EQUIP)

    source_action=bpy.data.actions[f'PKM16_{family}_reload_empty']
    frames=[sample(source_action,f/FPS) for f in range(round(6.6*FPS)+1)]
    rear=frames[round(5.515*FPS)]
    rear_lug=(rear['WPN_root']@fit).inverted()@rear['PKM_Charge']@rest['PKM_Charge'].inverted()@B@lug
    reload=[]
    for f,original in enumerate(frames):
        t=f/FPS;p={n:m.copy() for n,m in original.items()}
        if 4.82<t<6.30:
            W=original['WPN_root']@fit
            Rhand=W.to_quaternion()@hand_rotation
            contact=original['PKM_Charge']@rest['PKM_Charge'].inverted()@B@lug
            locked=Rhand.to_matrix().to_4x4();locked.translation=contact-Rhand@anchor
            hover=locked.copy();hover.translation+=W.to_3x3()@Vector((-.065,-.020,.055))
            released=locked.copy();released.translation=W@rear_lug-Rhand@anchor
            away=released.copy();away.translation+=W.to_3x3()@Vector((-.065,.010,.045))
            returning=original['WPN_root']@W0.inverted()@idle['hand_r']
            back=returning.copy();back.translation+=W.to_3x3()@Vector((-.045,-.025,.018))
            if t<5.13:
                H=mix(hover,locked,ramp(t,5.005,5.13))
                closed_amount=ramp(t,5.015,5.13)
            elif t<5.515:
                H=locked;closed_amount=1.
            elif t<5.69:
                H=mix(released,away,ramp(t,5.535,5.69))
                closed_amount=1-ramp(t,5.515,5.595)
            elif t<5.94:
                H=mix(away,back,ramp(t,5.69,5.94));closed_amount=0.
            else:
                H=mix(back,returning,ramp(t,5.94,6.18));closed_amount=0.
            weight=ramp(t,4.82,5.015)*(1-ramp(t,6.18,6.30))
            H=mix(original['hand_r'],H,weight)
            solve_arm(p,original,'r',H,weight)
            oldq=finger_q(original,'r');back_grip=ramp(t,5.83,6.18)
            qs={n:oldq[n].slerp(opening[n].slerp(hook[n],closed_amount).slerp(idle_q['r'][n],back_grip),weight) for n in fingers['r']}
            finger_pose(p,'r',H,qs)
        reload.append(p)
    bake('reload_empty',reload,6.6)
    authoring[family]={'source':str(source),'equip_reference_seconds':[0,.85],
        'empty_reference_seconds':[23.85,25.4],'pad_anchor_hand_local_m':list(anchor),
        'handle_lug_model_m':list(lug),'contact_seconds':[5.13,5.515],
        'release_seconds':5.55,'reload_duration_preserved':6.6,'normal_reload_changed':False}
    (O/'authoring.json').write_text(json.dumps(authoring,indent=2))
    action(bpy.data.actions['PKM31_'+family+'_equip']);s.frame_end=round(EQUIP*FPS);s.frame_set(s.frame_end)
    bpy.ops.wm.save_as_mainfile(filepath=str(O/f'PKM_{family}_EquipCharge_Editable.blend'))
print('PKM31_AUTHOR_COMPLETE',flush=True)
