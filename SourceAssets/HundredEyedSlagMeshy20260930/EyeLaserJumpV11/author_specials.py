"""Body-specific eye casting and jump slam from the actual Epic Rampage jumps.

Retain the V8 skin and V9 accepted-action source. Capsule elevation is supplied
by CharacterMovement; animation only supplies preparation, tuck and absorption.
"""
from pathlib import Path
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
bootstrap_file = ROOT/'RampageRecoverV9/author_recovery.py'
bootstrap = bootstrap_file.read_text().split("original = bpy.data.actions[")[0]
bootstrap = bootstrap.replace("str(V8 / 'HundredEyedSlag_RampageV8.blend')",
    "str(ROOT / 'RampageRecoverV9/HundredEyedSlag_RampageRecoverV9.blend')")
exec(compile(bootstrap,str(bootstrap_file),'exec'),globals())
scene.render.fps = 60
a = bpy.data.actions['A_HundredEyedSlag_AttackSlam_R_RampageRecoverV9']
rig.animation_data.action=a; rig.animation_data.action_slot=a.slots[0]
scene.frame_set(55); bpy.context.view_layer.update()
ready={p.name:p.matrix.copy() for p in rig.pose.bones}
for retained in bpy.data.actions:
    if not retained.slots or not retained.layers: continue
    bag=retained.layers[0].strips[0].channelbag(retained.slots[0])
    if bag is None: continue
    for curve in bag.fcurves:
        for point in curve.keyframe_points:
            for coordinate in (point.co,point.handle_left,point.handle_right): coordinate.x=(coordinate.x-1)*2+1
        curve.update()
for name in ('Jump_Start','Jump_Mid','Jump_Fall','Jump_End'):
    raw=json.loads((OUT/'SourceMotion'/(name+'.json')).read_text())
    frames=[]
    for row in raw['frames']:
        frame={}
        for bone,tr in row['component'].items():
            x,y,z,w=tr['rotation_xyzw']
            frame[bone]=(C@Vector(tr['translation_cm'])*.01,(C@Quaternion((w,x,y,z)).to_matrix()@C.transposed()).to_quaternion())
        frames.append(frame)
    sources[name]=dict(frames=frames,seconds=raw['seconds'])

ready_pads={k:ready[l['bones'][2]]@inv[l['bones'][2]]@l['pad'] for k,l in limbs.items()}
limb_frames={}
for k,l in limbs.items():
    s,e,w=[ready[n].translation for n in l['bones']]
    u,lo=(e-s).normalized(),(w-e).normalized(); normal=u.cross(lo).normalized()
    limb_frames[k]=(frame_basis(u,normal),frame_basis(lo,normal))
offsets={}
for k,l in limbs.items():
    uf,lf=limb_frames[k]
    for name,frame in zip(l['bones'],(uf,lf,lf)): offsets[name]=frame.inverted()@ready[name].to_quaternion()
for name,frame in [('front_upper_twist.R',limb_frames['front.R'][0]),
                   ('front_lower_twist_01.R',limb_frames['front.R'][1]),
                   ('front_lower_twist_02.R',limb_frames['front.R'][1])]:
    offsets[name]=frame.inverted()@ready[name].to_quaternion()
contracts=[dict(name='EyeLaserWindup',seconds=1.2,loop=False),
    dict(name='EyeLaserFire',seconds=.65,loop=False),dict(name='EyeLaserRecover',seconds=.5,loop=False),
    dict(name='JumpWindup',seconds=.7,loop=False),dict(name='JumpRise',seconds=.65,loop=False),
    dict(name='JumpFall',seconds=.4,loop=True),dict(name='JumpImpact',seconds=.4,loop=False),
    dict(name='JumpRecover',seconds=.65,loop=False)]
neutral=sources['Idle']['frames'][0]

def controls(role,u):
    if role.startswith('EyeLaser'):
        strength=ease(u) if role=='EyeLaserWindup' else (1-ease(u) if role=='EyeLaserRecover' else 1.)
        return .035*strength,-.035*strength,0.,neutral,strength
    if role=='JumpWindup':
        if u<=.55: return -.16*ease(u/.55),.12*ease(u/.55),0.,sample('Jump_Start',0.),ease(u/.55)
        launch=ease((u-.55)/.45)
        return -.16+.195*launch,.12*(1-launch),0.,sample('Jump_Start',sources['Jump_Start']['seconds']*launch),1.
    if role in ('JumpRise','JumpFall'):
        name='Jump_Mid' if role=='JumpRise' else 'Jump_Fall'
        src=sample(name,sources[name]['seconds']*u)
        return .035*(1-ease(u)) if role=='JumpRise' else 0.,-.035,1.,src,1.
    if role=='JumpImpact':
        src=sample('Jump_End',sources['Jump_End']['seconds']*u)
        pelvis_z=src['pelvis'][0].z-src['root'][0].z
        first=sources['Jump_End']['frames'][0]
        initial=first['pelvis'][0].z-first['root'][0].z
        return max(-.15,min(0.,(pelvis_z-initial)*.22)),.12*math.sin(math.pi*u),0.,src,1.
    last=sources['Jump_End']['frames'][-1]; first=sources['Jump_End']['frames'][0]
    compression=(last['pelvis'][0].z-last['root'][0].z)-(first['pelvis'][0].z-first['root'][0].z)
    return compression*.22*(1-ease(u)),0.,0.,mix(last,neutral,ease(u)),1-ease(u)

def special_pose(role,u):
    if (role in ('EyeLaserWindup','JumpWindup') and u==0) or (role in ('EyeLaserRecover','JumpRecover') and u==1):
        return {n:m.copy() for n,m in ready.items()}
    z,pitch,air,src,strength=controls(role,u)
    G=around((-.05,0,.64),(0,0,z),rotation(ry=pitch))
    target={'root':ready['root'].copy()}
    for name in ('death_pivot','pelvis','spine','chest','carapace','front_plate','shell.L','shell.R'):
        b=arm.bones[name]
        base=G@ready[name] if name=='death_pivot' else target[b.parent.name]@ready[b.parent.name].inverted()@ready[name]
        donor={'pelvis':'pelvis','spine':'spine_02','chest':'spine_03'}.get(name)
        if donor and role.startswith('Jump'):
            q=shortest(Quaternion(),src[donor][1]@neutral[donor][1].inverted(),.06*strength)
            base=Matrix.LocRotScale(base.translation,q@base.to_quaternion(),Vector((1,1,1)))
        target[name]=base
    pads={k:p.copy() for k,p in ready_pads.items()}
    if air:
        for key,bone in [('front.L','hand_l'),('front.R','hand_r'),('rear.L','foot_l'),('rear.R','foot_r')]:
            delta=((src[bone][0]-src['pelvis'][0])-(neutral[bone][0]-neutral['pelvis'][0]))*.22
            delta.x=max(-.14,min(.18,delta.x));delta.y=max(-.045,min(.045,delta.y))
            delta.z=max(.06,min(.24,.10+delta.z))
            pads[key]+=delta
    else:
        # Preserve all four planted pads when the source compression exceeds
        # this target's shorter limbs, rather than forcing overbent knees.
        lo,hi=-.3,.3
        for key,l in limbs.items():
            parent=target[l['parent']]@inv[l['parent']]
            sh=parent@l['shoulder'];wr=pads[key]+l['wrist']-l['pad']
            horizontal,vertical=(sh-wr).to_2d().length,sh.z-wr.z
            lo=max(lo,math.sqrt(max(0.,l['min_reach']**2-horizontal**2))-vertical)
            hi=min(hi,math.sqrt(max(0.,l['max_reach']**2-horizontal**2))-vertical)
        dz=max(lo,min(0.,hi)) if lo<=hi else min(0.,hi)
        for name in target:
            if name!='root':target[name].translation.z+=dz
    for key,l in limbs.items():
        parent=target[l['parent']]@inv[l['parent']]
        s,e,w,_=solve(l,parent,pads[key],Quaternion())
        uvec,lower=(e-s).normalized(),(w-e).normalized();normal=uvec.cross(lower).normalized()
        uf,lf=frame_basis(uvec,normal),frame_basis(lower,normal)
        for name,position,frame in zip(l['bones'],(s,e,w),(uf,lf,lf)):
            target[name]=Matrix.LocRotScale(position,frame@offsets[name],Vector((1,1,1)))
        palm=l['bones'][2]
        for toe in l['toes']: target[toe]=target[palm]@ready[palm].inverted()@ready[toe]
        if key=='front.R':
            for name,parent_name,frame in [('front_upper_twist.R','front_upper.R',uf),
                ('front_lower_twist_01.R','front_lower.R',lf),('front_lower_twist_02.R','front_lower.R',lf)]:
                position=(target[parent_name]@ready[parent_name].inverted()@ready[name]).translation
                target[name]=Matrix.LocRotScale(position,frame@offsets[name],Vector((1,1,1)))
            for helper,a,b,anchor in [('front_elbow_support.R','front_upper.R','front_lower.R','front_lower.R'),
                ('front_wrist_support.R','front_lower.R','front_palm.R','front_palm.R')]:
                q=shortest((target[a]@ready[a].inverted()).to_quaternion(),(target[b]@ready[b].inverted()).to_quaternion(),.5)
                target[helper]=Matrix.LocRotScale(target[anchor].translation,q@ready[helper].to_quaternion(),Vector((1,1,1)))
            q=shortest((target['chest']@ready['chest'].inverted()).to_quaternion(),(target['front_upper.R']@ready['front_upper.R'].inverted()).to_quaternion(),.45)
            target['front_shoulder.R']=Matrix.LocRotScale(s,q@ready['front_shoulder.R'].to_quaternion(),Vector((1,1,1)))
    for name in ('neck','head','eyes.L','eyes.R'):
        if name not in ready: continue
        p=arm.bones[name].parent.name
        target[name]=target[p]@ready[p].inverted()@ready[name]
        if name=='neck' and role.startswith('EyeLaser'):
            target[name]=target[name]@rotation(ry=-.09*strength).to_matrix().to_4x4()
    for name in ('ash_origin','attack_origin'):
        p=arm.bones[name].parent.name;target[name]=target[p]@ready[p].inverted()@ready[name]
    return target

for c in contracts:
    c.update(fps=60,start_frame=1,end_frame_inclusive=round(c['seconds']*60)+1,
        action='A_HundredEyedSlag_'+c['name']+'_V11',file='Animations/A_HundredEyedSlag_'+c['name']+'_V11.fbx',root_motion=False)
    a=bpy.data.actions.new(c['action']);a.use_fake_user=True;rig.animation_data.action=a
    previous={}
    for frame in range(1,c['end_frame_inclusive']+1):
        target=special_pose(c['name'],(frame-1)/(c['end_frame_inclusive']-1))
        for b in arm.bones:
            n=b.name
            if n not in target:target[n]=target[b.parent.name]@ready[b.parent.name].inverted()@ready[n] if b.parent else ready[n].copy()
            basis=inv[n]@rest[b.parent.name]@target[b.parent.name].inverted()@target[n] if b.parent else inv[n]@target[n]
            pb=rig.pose.bones[n];pb.rotation_mode='QUATERNION';pb.matrix_basis=basis
            if n in previous:pb.rotation_quaternion.make_compatible(previous[n])
            previous[n]=pb.rotation_quaternion.copy();pb.scale=(1,1,1)
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame)
        if not rig.animation_data.action_slot:rig.animation_data.action_slot=a.slots[0]
    for curve in a.layers[0].strips[0].channelbag(a.slots[0]).fcurves:
        for p in curve.keyframe_points:p.interpolation='LINEAR'
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_EyeLaserJumpV11.blend'))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
(OUT/'Delivery/Animations').mkdir(parents=True,exist_ok=True)
for c in contracts:
    a=bpy.data.actions[c['action']];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    scene.frame_start=1;scene.frame_end=c['end_frame_inclusive'];scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'Delivery'/c['file']),object_types={'ARMATURE'},bake_anim=True,
        use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,
        bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
(OUT/'animation_contract.json').write_text(json.dumps(dict(actions=contracts,
    jump_reference='Actual imported Epic Rampage Jump_Start/Mid/Fall/End, target body adaptation',
    laser_reference='Existing V9 ready stance with planted four-limb supports and casting torso/front-plate motion',
    body_elevation='Native CharacterMovement only; no animation root elevation',
    mesh_weights_changed=False,accepted_sweep_and_slam_changed=False,
    preview_rendered=False,runtime_tested=False),indent=2),encoding='utf-8')
print('SLAG_V11_EIGHT_SPECIAL_ANIMATIONS_EXPORTED',flush=True)
