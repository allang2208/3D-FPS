"""Support-chain skin and source-driven jump articulation; no render or tests.

Actual Epic Rampage Start/Mid/Fall/End drive the timing and joint-plane changes.
The target has three short support limbs and one giant arm, so foot contact,
bone length and reachable knee flexion are authored for this body explicitly.
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
# The actual accepted Rampage-derived lift provides the casting arm reference.
scene.frame_set(21); bpy.context.view_layer.update()
raised={p.name:p.matrix.copy() for p in rig.pose.bones}
ready_pads={k:ready[l['bones'][2]]@inv[l['bones'][2]]@l['pad'] for k,l in limbs.items()}
raised_pad=raised['front_palm.R']@inv['front_palm.R']@limbs['front.R']['pad']
raised_normal=(raised['front_lower.R'].translation-raised['front_upper.R'].translation).cross(
    raised['front_palm.R'].translation-raised['front_lower.R'].translation).normalized()

for retained in bpy.data.actions:
    if not retained.slots or not retained.layers: continue
    bag=retained.layers[0].strips[0].channelbag(retained.slots[0])
    if bag is None: continue
    for curve in bag.fcurves:
        for point in curve.keyframe_points:
            for coordinate in (point.co,point.handle_left,point.handle_right): coordinate.x=(coordinate.x-1)*2+1
        curve.update()
for name in ('Jump_Start','Jump_Mid','Jump_Fall','Jump_End'):
    raw=json.loads((ROOT/'EyeLaserJumpV11/SourceMotion'/(name+'.json')).read_text())
    frames=[]
    for row in raw['frames']:
        frame={}
        for bone,tr in row['component'].items():
            x,y,z,w=tr['rotation_xyzw']
            frame[bone]=(C@Vector(tr['translation_cm'])*.01,
                (C@Quaternion((w,x,y,z)).to_matrix()@C.transposed()).to_quaternion())
        frames.append(frame)
    sources[name]=dict(frames=frames,seconds=raw['seconds'])
neutral=sources['Idle']['frames'][0]

# Reweight only the support limbs. In V3 their body blend depended on height;
# upper thighs and knee collars retained too much rigid torso influence.
# Use anatomical shoulder-to-pad arclength, keeping attachment at the hip only.
skin=np.load(ROOT/'RampageV8/skin_weights.npz')
names=[str(n) for n in skin['bone_names']]; col={n:i for i,n in enumerate(names)}
indices=skin['indices'].copy(); values=skin['weights'].copy()
old=np.zeros((len(v),len(names)),np.float32)
old[np.arange(len(v))[:,None],indices]=values
all_chain_names={k:l['bones']+l['toes'] for k,l in limbs.items()}
all_chain_names['front.R']+=helper_names
masses={k:old[:,[col[n] for n in ns]].sum(1) for k,ns in all_chain_names.items()}
chain_arcs={}; chain_dist={}
for k,l in limbs.items():
    chain_arcs[k],chain_dist[k]=coordinates(v,[np.asarray(l[n]) for n in ('shoulder','elbow','wrist','pad')])
nearest=np.argmin(np.asarray([chain_dist[k] for k in limbs]),axis=0)
weighted=np.argmax(np.asarray([masses[k] for k in limbs]),axis=0)
ownership=np.where(np.max(np.asarray([masses[k] for k in limbs]),axis=0)>.04,weighted,nearest)
giant=masses['front.R']>.008
changed=np.zeros(len(v),bool); skin_report=[]
body_cols=[col[n] for n in ('pelvis','spine','chest','carapace','front_plate','shell.L','shell.R')]
for branch,k in enumerate(limbs):
    if k=='front.R': continue
    l=limbs[k]; s=chain_arcs[k]
    mask=(ownership==branch)&((masses[k]>.035)|((chain_dist[k]<.105)&(s>.025)&(v[:,2]<.60)))
    mask &= ~giant
    lweight=np.zeros_like(old)
    knee=smooth(l['a']-.028,l['a']+.028,s)
    ankle=smooth(l['a']+l['b']-.025,l['a']+l['b']+.018,s)
    ankle=np.maximum(ankle,1-smooth(.075,.115,v[:,2]))
    lweight[:,col[l['bones'][0]]]=(1-knee)*(1-ankle)
    lweight[:,col[l['bones'][1]]]=knee*(1-ankle)
    lweight[:,col[l['bones'][2]]]=ankle
    body=np.zeros_like(old); body[:,body_cols]=old[:,body_cols]
    empty=body.sum(1)<1e-8; body[empty,col[l['parent']]]=1
    body/=np.maximum(body.sum(1,keepdims=True),1e-8)
    attachment=1-smooth(.018,.135 if k=='front.L' else .115,s)
    w=lweight*(1-attachment[:,None])+body*attachment[:,None]
    toe=old[:,[col[n] for n in l['toes']]]; toe_mass=toe.sum(1)
    amount=np.minimum(.12*w[:,col[l['bones'][2]]],toe_mass)
    w[:,col[l['bones'][2]]]-=amount
    for j,n in enumerate(l['toes']): w[:,col[n]]+=amount*toe[:,j]/np.maximum(toe_mass,1e-8)
    ix=np.argpartition(w[mask],-4,axis=1)[:,-4:]
    val=np.take_along_axis(w[mask],ix,axis=1);val/=np.maximum(val.sum(1,keepdims=True),1e-8)
    indices[mask],values[mask]=ix,val; changed|=mask
    skin_report.append(dict(chain=k,vertices_authored=int(mask.sum()),knee_collar_m=.028,
        ankle_collar_m=.025,body_attachment_m=.135 if k=='front.L' else .115))
mesh.vertex_groups.clear()
for i,n in enumerate(names):
    group=mesh.vertex_groups.new(name=n)
    rr,cc=np.nonzero(indices==i)
    for vertex,slot in zip(rr,cc):
        weight=float(values[vertex,slot])
        if weight>1e-6:group.add([int(vertex)],weight,'REPLACE')
np.savez_compressed(OUT/'skin_weights.npz',bone_names=np.asarray(names),indices=indices,weights=values)
print('SLAG_V12_SUPPORT_SKIN_AUTHORED '+str(int(changed.sum())),flush=True)

# Segment frames preserve the neutral axial alignment; support knees now have
# their own flexion range, while the accepted giant-arm limits remain bounded.
offsets={}; ready_normals={}; ready_axes={}; ready_bends={}; poles={}
for k,l in limbs.items():
    s,e,w=[ready[n].translation for n in l['bones']]
    upper,lower=(e-s).normalized(),(w-e).normalized()
    normal=upper.cross(lower).normalized(); axis=(w-s).normalized()
    uf,lf=frame_basis(upper,normal),frame_basis(lower,normal)
    ready_normals[k]=normal;ready_axes[k]=axis;ready_bends[k]=upper.angle(lower)
    poles[k]=(e-s-axis*(e-s).dot(axis)).normalized()
    for name,frame in zip(l['bones'],(uf,lf,lf)):offsets[name]=frame.inverted()@ready[name].to_quaternion()
    l['min_bend']=math.radians(12)
    l['max_bend']=math.radians(118 if k=='front.R' else 134)
for name,part in [('front_upper_twist.R',0),('front_lower_twist_01.R',1),('front_lower_twist_02.R',1)]:
    l=limbs['front.R']; s,e,w=[ready[n].translation for n in l['bones']]
    frame=frame_basis(((e-s) if part==0 else (w-e)).normalized(),ready_normals['front.R'])
    offsets[name]=frame.inverted()@ready[name].to_quaternion()

source_chains={'front.R':('upperarm_r','lowerarm_r','hand_r'),
    'front.L':('upperarm_l','lowerarm_l','hand_l'),
    'rear.R':('thigh_r','calf_r','foot_r'),'rear.L':('thigh_l','calf_l','foot_l')}
def donor_hip(frame):return frame['pelvis'][0].z-frame['root'][0].z
start_hip0=donor_hip(sources['Jump_Start']['frames'][0]);start_hip1=donor_hip(sources['Jump_Start']['frames'][-1])
end_hip0=donor_hip(sources['Jump_End']['frames'][0])
end_hip_min=min(donor_hip(f) for f in sources['Jump_End']['frames'])

def body(role,u):
    if role.startswith('EyeLaser'):
        strength=ease(u/.42) if role=='EyeLaserWindup' else (1-ease(u) if role=='EyeLaserRecover' else 1.)
        return Vector((-.025*strength,.038*strength,-.025*strength)),rotation(ry=-.065*strength,rz=.035*strength),neutral,strength
    if role=='JumpWindup':
        if u<.62:
            strength=ease(u/.62)
            return Vector((-.025*strength,0,-.19*strength)),rotation(ry=.12*strength),sample('Jump_Start',0),strength
        src=sample('Jump_Start',sources['Jump_Start']['seconds']*(u-.62)/.38)
        push=max(0,min(1,(donor_hip(src)-start_hip0)/(start_hip1-start_hip0)))
        return Vector((-.025*(1-push),0,-.19+.235*push)),rotation(ry=.12*(1-push)),src,1.
    if role=='JumpRise':
        src=sample('Jump_Mid',sources['Jump_Mid']['seconds']*u)
        return Vector((0,0,.045*(1-ease(u/.32)))),rotation(ry=-.09*ease(u)),src,1.
    if role=='JumpFall':
        src=sample('Jump_Fall',sources['Jump_Fall']['seconds']*u)
        unfold=ease(u/.82)
        return Vector((0,0,.045*unfold)),rotation(ry=-.09*(1-unfold)),src,1.
    if role=='JumpImpact':
        src=sample('Jump_End',sources['Jump_End']['seconds']*u)
        absorb=max(0,min(1,(end_hip0-donor_hip(src))/(end_hip0-end_hip_min)))
        return Vector((-.028*absorb,0,.045-.245*absorb)),rotation(ry=.14*absorb),src,1.
    last=sources['Jump_End']['frames'][-1]
    last_absorb=max(0,min(1,(end_hip0-donor_hip(last))/(end_hip0-end_hip_min)))
    return Vector((-.028*last_absorb*(1-ease(u)),0,(.045-.245*last_absorb)*(1-ease(u)))),\
        rotation(ry=.14*last_absorb*(1-ease(u))),mix(last,neutral,ease(u)),1-ease(u)

def apply_chain(target,k,pad=None,bend=None,axis=None,normal_override=None,grounded=True):
    l=limbs[k]; parent=l['parent']; parent_delta=target[parent]@ready[parent].inverted()
    shoulder=parent_delta@ready[l['bones'][0]].translation
    parentq=parent_delta.to_quaternion()
    reference_axis=parentq@ready_axes[k]
    pole0=parentq@poles[k]
    if pad is not None:
        wrist=pad-(ready_pads[k]-ready[l['bones'][2]].translation)
        delta=wrist-shoulder;axis=delta.normalized()
        near=math.sqrt(l['a']**2+l['b']**2+2*l['a']*l['b']*math.cos(l['max_bend']))
        far=math.sqrt(l['a']**2+l['b']**2+2*l['a']*l['b']*math.cos(l['min_bend']))
        reach=max(near,min(far,delta.length))
    else:
        bend=max(l['min_bend'],min(l['max_bend'],bend))
        reach=math.sqrt(l['a']**2+l['b']**2+2*l['a']*l['b']*math.cos(bend))
        axis=axis.normalized()
    pole=reference_axis.rotation_difference(axis)@pole0
    if normal_override is not None:
        proposed=-normal_override.cross(axis)
        if proposed.length>1e-6:
            proposed.normalize()
            if proposed.dot(pole)<0:proposed.negate()
            pole=pole.lerp(proposed,.65).normalized()
    along=(l['a']**2-l['b']**2+reach*reach)/(2*reach)
    elbow=shoulder+axis*along+pole*math.sqrt(max(0,l['a']**2-along*along))
    wrist=shoulder+axis*reach
    upper,lower=(elbow-shoulder).normalized(),(wrist-elbow).normalized()
    normal=upper.cross(lower).normalized()
    uf,lf=frame_basis(upper,normal),frame_basis(lower,normal)
    for name,position,frame in zip(l['bones'],(shoulder,elbow,wrist),(uf,lf,lf)):
        q=ready[name].to_quaternion() if name==l['bones'][2] and grounded else frame@offsets[name]
        target[name]=Matrix.LocRotScale(position,q,Vector((1,1,1)))
    palm=l['bones'][2]
    for toe in l['toes']:target[toe]=target[palm]@ready[palm].inverted()@ready[toe]
    if k=='front.R':
        for name,p,frame in [('front_upper_twist.R','front_upper.R',uf),
            ('front_lower_twist_01.R','front_lower.R',lf),('front_lower_twist_02.R','front_lower.R',lf)]:
            pos=(target[p]@ready[p].inverted()@ready[name]).translation
            target[name]=Matrix.LocRotScale(pos,frame@offsets[name],Vector((1,1,1)))
        for helper,a,b,anchor in [('front_elbow_support.R','front_upper.R','front_lower.R','front_lower.R'),
            ('front_wrist_support.R','front_lower.R','front_palm.R','front_palm.R')]:
            q=shortest((target[a]@ready[a].inverted()).to_quaternion(),(target[b]@ready[b].inverted()).to_quaternion(),.5)
            target[helper]=Matrix.LocRotScale(target[anchor].translation,q@ready[helper].to_quaternion(),Vector((1,1,1)))
        q=shortest((target['chest']@ready['chest'].inverted()).to_quaternion(),(target['front_upper.R']@ready['front_upper.R'].inverted()).to_quaternion(),.45)
        target['front_shoulder.R']=Matrix.LocRotScale(shoulder,q@ready['front_shoulder.R'].to_quaternion(),Vector((1,1,1)))

def special_pose(role,u):
    if (role in ('EyeLaserWindup','JumpWindup') and u==0) or (role in ('EyeLaserRecover','JumpRecover') and u==1):
        return {n:m.copy() for n,m in ready.items()}
    shift,q,src,strength=body(role,u)
    G=around((-.05,0,.64),shift,q)
    target={'root':ready['root'].copy()}
    # Existing pelvis/spine/chest are articulated individually, not a single
    # mesh Z offset. Keep translations attached to the actual parent chain.
    for name in ('death_pivot','pelvis','spine','chest','carapace','front_plate','shell.L','shell.R'):
        b=arm.bones[name]
        base=G@ready[name] if name=='death_pivot' else target[b.parent.name]@ready[b.parent.name].inverted()@ready[name]
        donor={'pelvis':'pelvis','spine':'spine_02','chest':'spine_03'}.get(name)
        if donor and role.startswith('Jump'):
            weight={'pelvis':.12,'spine':.24,'chest':.19}[name]*strength
            extra=shortest(Quaternion(),src[donor][1]@neutral[donor][1].inverted(),weight)
            base=Matrix.LocRotScale(base.translation,extra@base.to_quaternion(),Vector((1,1,1)))
        target[name]=base
    for k,l in limbs.items():
        if role.startswith('EyeLaser') and k=='front.R':
            # Rise along the actual Rampage arm path, clear of the eye cluster.
            lift=strength
            casting=ready_pads[k].lerp(raised_pad,.80)
            casting.x=max(.18,min(.55,casting.x));casting.y=min(-.33,casting.y)
            casting.z=max(.86,min(1.06,casting.z))
            pad=ready_pads[k].lerp(casting,lift)
            apply_chain(target,k,pad=pad,normal_override=ready_normals[k].lerp(raised_normal,lift).normalized(),grounded=lift<.01)
        elif role in ('JumpRise','JumpFall'):
            parentq=(target[l['parent']]@ready[l['parent']].inverted()).to_quaternion()
            a,b,c=source_chains[k]
            source_axis=(src[c][0]-src[a][0]).normalized()
            idle_axis=(neutral[c][0]-neutral[a][0]).normalized()
            source_rotation=shortest(Quaternion(),idle_axis.rotation_difference(source_axis),.28)
            axis=source_rotation@(parentq@ready_axes[k])
            if role=='JumpRise':
                if u<.20:
                    # Early flight finishes the toe-off, visibly straight legs.
                    launch=ground_launch[k]
                    bend=launch[1]+(math.radians(14)-launch[1])*ease(u/.20)
                    axis=launch[0].lerp(axis,ease(u/.20)).normalized()
                else:
                    # Actual Jump_Mid knee/hip shortening shapes the tuck.
                    first=sources['Jump_Mid']['frames'][0]
                    last=sources['Jump_Mid']['frames'][-1]
                    da=(first[c][0]-first[a][0]).length;db=(last[c][0]-last[a][0]).length
                    current=(src[c][0]-src[a][0]).length
                    source_tuck=max(0,min(1,(da-current)/max(.02,da-db)))
                    tuck=max(ease((u-.20)/.80),source_tuck)
                    bend=math.radians(14)+(math.radians(108 if k=='front.R' else 128)-math.radians(14))*tuck
            else:
                # Height-driven runtime progress replaces the old fall loop.
                unfold=ease(u/.82)
                landing=ground_landing[k]
                bend=math.radians(108 if k=='front.R' else 128)*(1-unfold)+landing[1]*unfold
                axis=axis.lerp(landing[0],unfold).normalized()
            apply_chain(target,k,bend=bend,axis=axis,grounded=False)
            if role=='JumpRise' and u<.20:
                palm=l['bones'][2]
                target[palm]=Matrix.LocRotScale(target[palm].translation,
                    shortest(ready[palm].to_quaternion(),target[palm].to_quaternion(),ease(u/.20)),Vector((1,1,1)))
                for toe in l['toes']:target[toe]=target[palm]@ready[palm].inverted()@ready[toe]
            if role=='JumpFall':
                palm=l['bones'][2]
                target[palm]=Matrix.LocRotScale(target[palm].translation,
                    shortest(target[palm].to_quaternion(),ready[palm].to_quaternion(),ease(u/.82)),Vector((1,1,1)))
                for toe in l['toes']:target[toe]=target[palm]@ready[palm].inverted()@ready[toe]
        else:apply_chain(target,k,pad=ready_pads[k],grounded=True)
        if k=='front.R':
            q=shortest((target['front_lower.R']@ready['front_lower.R'].inverted()).to_quaternion(),
                (target['front_palm.R']@ready['front_palm.R'].inverted()).to_quaternion(),.5)
            target['front_wrist_support.R']=Matrix.LocRotScale(target['front_palm.R'].translation,
                q@ready['front_wrist_support.R'].to_quaternion(),Vector((1,1,1)))
    for name in ('ash_origin','attack_origin'):
        p=arm.bones[name].parent.name;target[name]=target[p]@ready[p].inverted()@ready[name]
    return target

# Cache the contact-space launch and landing chains to join the physical jump.
ground_launch={};ground_landing={}
for key,role,phase in [('launch','JumpWindup',1.),('landing','JumpImpact',0.)]:
    pose=special_pose(role,phase)
    destination=ground_launch if key=='launch' else ground_landing
    for k,l in limbs.items():
        s,e,w=[pose[n].translation for n in l['bones']]
        destination[k]=((w-s).normalized(),(e-s).angle(w-e))

contracts=[dict(name='EyeLaserWindup',seconds=1.5,loop=False),
    dict(name='EyeLaserFire',seconds=.65,loop=False),dict(name='EyeLaserRecover',seconds=.5,loop=False),
    dict(name='JumpWindup',seconds=.85,loop=False),dict(name='JumpRise',seconds=.65,loop=False),
    dict(name='JumpFall',seconds=.45,loop=False),dict(name='JumpImpact',seconds=.5,loop=False),
    dict(name='JumpRecover',seconds=.75,loop=False)]
for c in contracts:
    c.update(fps=60,start_frame=1,end_frame_inclusive=round(c['seconds']*60)+1,
        action='A_HundredEyedSlag_'+c['name']+'_V12',file='Animations/A_HundredEyedSlag_'+c['name']+'_V12.fbx',root_motion=False)
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
scene.frame_set(1);mesh.name='SK_HundredEyedSlag_V12'
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'HundredEyedSlag_ArticulationV12.blend'))
(OUT/'Delivery/Animations').mkdir(parents=True,exist_ok=True)
options=dict(use_selection=True,add_leaf_bones=False,use_armature_deform_only=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,
    bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'Delivery/SK_HundredEyedSlag_V12.fbx'),object_types={'ARMATURE','MESH'},
    bake_anim=False,use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='AUTO',embed_textures=False,**options)
mesh.select_set(False)
for c in contracts:
    a=bpy.data.actions[c['action']];rig.animation_data.action=a;rig.animation_data.action_slot=a.slots[0]
    scene.frame_start=1;scene.frame_end=c['end_frame_inclusive'];scene.frame_set(1)
    bpy.ops.export_scene.fbx(filepath=str(OUT/'Delivery'/c['file']),object_types={'ARMATURE'},bake_anim=True,**options)
(OUT/'animation_contract.json').write_text(json.dumps(dict(actions=contracts,
    jump_reference='Actual Epic Rampage Jump_Start/Mid/Fall/End, mapped to short support limbs',
    laser_reference='Actual accepted V9 Rampage-derived raised-arm pose, three-limb support shift',
    body_elevation='Capsule: native gravity. Articulation: pelvis/spine/chest plus four bone chains',
    mesh_weights_changed=True,weight_chains=skin_report,authored_weight_vertices=int(changed.sum()),
    mesh_path='/Game/Monsters/HundredEyedSlag/ArticulationV12/SK_HundredEyedSlag_V12',
    giant_right_arm_weights_changed=False,bone_count=len(arm.bones),added_bones=0,max_influences=4,
    bind_geometry_uv_materials_preserved=True,accepted_sweep_and_slam_changed=False,
    laser_charge_seconds=1.5,laser_target_prediction=False,fall_loops=False,
    preview_rendered=False,runtime_tested=False),indent=2),encoding='utf-8')
print('SLAG_V12_SKIN_AND_EIGHT_ANIMATIONS_EXPORTED',flush=True)
