"""Fit the migrated M16 to the accepted Manny arms and bake private clips.

No rendering or tests. Source M16 geometry/UV and all mechanical identities
are retained. Contacts are fitted in the receiver frame, not by gun bounds.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector

O=Path(__file__).parent
S=O.parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'M4TacticalToss20260910/M4_Hand_MAT_Editable.blend'),use_scripts=False)
scene=bpy.context.scene
rig=bpy.data.objects['SK_M4_Infima']
hands=bpy.data.objects['SK_Manny_Arms_Export']
oldrest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
oldnames=list(oldrest)

def action(a):
    rig.animation_data.action=a
    rig.animation_data.action_slot=a.slots[0]

def sample(a,f):
    action(a);scene.frame_set(int(f),subframe=f-int(f));bpy.context.view_layer.update()
    return {b.name:b.matrix.copy() for b in rig.pose.bones}

def smooth(t):
    t=max(0.,min(1.,t));return t*t*(3.-2.*t)

def mix_transform(a,b,w):
    ap,aq,az=a.decompose();bp,bq,bz=b.decompose()
    return Matrix.LocRotScale(ap.lerp(bp,w),aq.slerp(bq,w),az.lerp(bz,w))

def charge_source_frame(f):
    keys=[(111,0),(119,7),(125,12),(137,18),(139,19),(143,22),(149,27),(162,38)]
    if f<=111:return 0.
    for (a,ga),(b,gb) in zip(keys,keys[1:]):
        if f<=b:return ga+(gb-ga)*(f-a)/(b-a)
    return 38.

sources={k:(bpy.data.actions[n],end,60) for k,n,end in [
    ('idle','M4_idle',180),('aim','M4_aim',2),('fire','M4_fire',46),
    ('aim_fire','M4_aim_fire',46),('reload','M4_HK416_reload',126),
    ('equip_charge','M4_HK416_equip_charge',38),('inspect','M4_inspect',180)]}
with bpy.data.libraries.load(str(S/'M4WrapGrip20260910/M4_Hand_MAT_Editable.blend'),link=False) as (src,dst):
    # Accepted complete arm/finger authoring before the later accelerated slap
    # and baked impact vibration. Keep the source's throw/insert/seat section.
    dst.actions=['M4_MAT_reload_empty','M4_MAT_equip_charge']
sources['reload_empty']=(dst.actions[0],162,60)
charge_action=dst.actions[1]
recovery_action=bpy.data.actions['M4_MAT_reload']
with bpy.data.libraries.load(str(S/'M4TacticalSprint20260915/Base/M4_TacticalSprint_Base_Editable.blend'),link=False) as (src,dst):
    dst.actions=[n for n in src.actions if 'TacticalSprint' in n]
for kind in ['Enter','Loop','Exit']:
    a=next(a for a in dst.actions if a.name.endswith('_'+kind))
    sources['sprint_'+kind.lower()]=(a,round(a.frame_range[1]),60)
with bpy.data.libraries.load(str(S/'M4QuickMeleeRefine20260919N/Base/M4_QuickCombat_Base_Editable.blend'),link=False) as (src,dst):
    dst.actions=['M4_QuickCombatRefineN_Base']
quick=dst.actions[0]
sources['quick_melee']=(quick,54,float(quick.frame_range[1])/.9)

base=sample(sources['idle'][0],0)
root=base['WPN_root'];rootinv=root.inverted()
reference=json.loads((O/'authoring_reference.json').read_text())
def centre(bounds):return Vector([(a+b)/2 for a,b in bounds])
grip_ref=centre(reference['parts']['M4_Grip Default Unreal_Export']['bounds'])
mag_ref=centre(reference['parts']['M4_Magazine Light.003_Export']['bounds'])
rotate=Matrix.Rotation(-math.pi/2,4,'Z')@Matrix.Scale(.01,4)
grip_src=rotate@centre(reference['m16_parts']['M16A2_PistolGrip']['bounds_cm'])
fit=Matrix.Translation(grip_ref-grip_src)@rotate
mag_shift=fit@centre(reference['m16_parts']['M16A2_Magazine']['bounds_cm'])-mag_ref
support_shift=Vector((0,0,fit.translation.z+.056809802-reference['parts']['M4_Handguard Kmode Unreal_Export']['bounds'][2][0]))
receipt={'fit_translation_m':list(fit.translation),'scale_cm_to_m':.01,
    'magazine_contact_shift_m':list(mag_shift),'support_contact_shift_m':list(support_shift),
    'reference':'Accepted M4 reload, normal recovery and right-hand charging motion; left hand supports the rifle during charging.',
    'reload_arm_policy':'Normal reload keeps M4 poses. Empty tail reuses M4 normal recovery and complete WrapGrip charging arms/fingers/twists; no arm IK or twist reset.',
    'empty_charge':{'reload_source':'M4WrapGrip20260910/M4_MAT_reload_empty',
        'charging_source':'M4WrapGrip20260910/M4_MAT_equip_charge','preserve_through_frame':88,
        'left_support_frame':111,'hook_contact_frame':125,'full_pull_frame':137,
        'release_frame':139,'handle_closed_frame':143,'recovery_end_frame':162,
        'mechanical_cues_frames':[21,54,80,125,139],'baked_slap_impact':False},
    'clips':{},'testing':'Not run; authored/exported/imported only.'}

# Cache source poses before changing any rest bone or assigning new actions.
cache={}
for kind,(a,end,fps) in sources.items():
    cache[kind]=[sample(a,k*.5*fps/60) for k in range(end*2+1)]
    receipt['clips'][kind]={'source':a.name,'frames':end,'fps':60,'source_fps':fps,'duration':end/60,
        'loop':kind in ['idle','sprint_loop']}
print('M16 source poses cached',flush=True)
# Reuse the accepted normal-reload release/return, then the complete right-hand
# charging action. The support hand is back on the fore-end before the right
# hand leaves the pistol grip. No new wrist or finger poses are synthesized.
normal_start=sample(recovery_action,98);normal_end=sample(recovery_action,126)
charge_start=sample(charge_action,0);charge_end=sample(charge_action,38)
recover_offset=cache['reload_empty'][176]['WPN_root']@normal_start['WPN_root'].inverted()
charge_offset=normal_end['WPN_root']@charge_start['WPN_root'].inverted()
charge_end_offset=normal_end['WPN_root']@charge_end['WPN_root'].inverted()
charge_donors={}
for k in range(177,325):
    f=k*.5
    if f<111:
        w=(f-88)/23
        donor=sample(recovery_action,98+28*w)
        delta=mix_transform(recover_offset,Matrix.Identity(4),smooth(w))
    else:
        donor=sample(charge_action,charge_source_frame(f));charge_donors[k]=donor
        delta=mix_transform(charge_offset,charge_end_offset,smooth((f-149)/13))
    cache['reload_empty'][k]={n:delta@m for n,m in donor.items()}
charging_reference=json.loads((O/'charging_reference.json').read_text())
m4_rear=[Vector(p) for p in charging_reference['m4_handle_rear_vertices_m']]
m16_rear=[fit@Vector(p) for p in charging_reference['M16A2_ChargingHandle']['rear_vertices_cm']]
bounds=lambda points:[[min(p[i] for p in points),max(p[i] for p in points)] for i in range(3)]
handle_contact_shift=centre(bounds(m16_rear))-centre(bounds(m4_rear))
charge_closed=charge_start['WPN_root'].inverted()@charge_start['WPN_ChargingHandle']
stroke=max((p['WPN_root'].inverted()@p['WPN_ChargingHandle']).translation.y-charge_closed.translation.y for p in charge_donors.values())
receipt['empty_charge'].update({'t_handle_contact_receiver_m':list(centre(bounds(m16_rear))),
    'contact_shift_from_m4_m':list(handle_contact_shift),'pull_travel_m':stroke})
for ob in list(scene.objects):
    if ob not in [rig,hands]:bpy.data.objects.remove(ob,do_unlink=True)
with bpy.data.libraries.load(str(S/'M16A2Migration20260919/M16A2_Mechanical_Editable.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.startswith('M16A2_')]
parts={ob.name.removeprefix('M16A2_'):ob for ob in dst.objects}
manifest=json.loads((S/'M16A2Migration20260919/manifest.json').read_text())
positions={p['name']:Vector((p['head_cm'][0],-p['head_cm'][1],p['head_cm'][2])) for p in manifest['bones']}
mapping={'Receiver':'WPN_root','Magazine':'WPN_SOCKET_Magazine','Bolt':'WPN_bolt',
    'Trigger':'WPN_Trigger','BoltCatch':'WPN_BoltCatch','ChargingHandle':'WPN_ChargingHandle',
    'ChargingHandleLatch':'WPN_ChargingHandleLatch','MagazineRelease':'WPN_MagazineRelease',
    'EjectionPortCover':'WPN_EjectionPortCover','Stock':'WPN_M16Stock','PistolGrip':'WPN_M16Grip',
    'Handguard':'WPN_M16Handguard','Muzzle':'WPN_M16Muzzle'}
source_bones={p['name']:p['bone'] for p in manifest['parts']}
markers={'WPN_RearSight':'RearSight','WPN_FrontSight':'FrontSight',
    'WPN_SOCKET_Muzzle':'SOCKET_Muzzle','WPN_SOCKET_Eject':'SOCKET_Eject'}
newbase={}
for label,name in mapping.items():
    if name=='WPN_root':continue
    local=rootinv@base.get(name,root)
    local.translation=fit@positions[source_bones[label]]
    # The source latch pivot is not stored in the same frame; use its actual
    # contact centre, then parent it to the handle to preserve pull travel.
    if label=='ChargingHandleLatch':local.translation=fit@centre(reference['m16_parts']['M16A2_'+label]['bounds_cm'])
    newbase[name]=root@local
for name,source in markers.items():
    local=rootinv@base[name];local.translation=fit@positions[source];newbase[name]=root@local

rig.animation_data_clear()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for name,pose in newbase.items():
    if name in oldrest:
        rest=oldrest[name]@base[name].inverted()@pose
        rig.data.edit_bones[name].matrix=rest
    else:
        parent='WPN_ChargingHandle' if name=='WPN_ChargingHandleLatch' else 'WPN_root'
        b=rig.data.edit_bones.new(name);b.parent=rig.data.edit_bones[parent]
        # A zero-length edit bone cannot retain the matrix's head-to-tail axis.
        # Establish a valid bone first, then assign the complete bind transform.
        b.length=.02;b.matrix=oldrest['WPN_root']@rootinv@pose
bpy.ops.object.mode_set(mode='OBJECT');rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
parents={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
names=list(rest);lr={n:rest[parents[n]].inverted()@rest[n] if parents[n] else rest[n] for n in names}

for label,ob in parts.items():
    scene.collection.objects.link(ob)
    # File mesh coordinates already include its mechanical receiver origin.
    b=mapping[label];pose=newbase.get(b,root)
    ob.data.transform(rest[b]@pose.inverted()@root@fit)
    ob.modifiers.clear();ob.vertex_groups.clear();ob.parent=rig
    ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
    ob.vertex_groups.new(name=b).add(list(range(len(ob.data.vertices))),1.,'REPLACE')
    ob.modifiers.new('M16_Manny','ARMATURE').object=rig
    mat=ob.data.materials[0].copy();mat.name='M_M16_'+({'Muzzle':'Flash_Hider','Handguard':'Foreend','ChargingHandle':'ChargingLever','ChargingHandleLatch':'ChargingLatch'}.get(label,label))
    ob.data.materials.clear();ob.data.materials.append(mat)
    ob.hide_render=False;ob.hide_set(False)

def shift_arm(p,side,shift):
    un,ln,hn='upperarm_'+side,'lowerarm_'+side,'hand_'+side
    a,b,c=[p[n].translation.copy() for n in (un,ln,hn)]
    goal=c+shift;l1=(b-a).length;l2=(c-b).length;d=(goal-a).length
    axis=(goal-a).normalized()
    if d>=l1+l2:a+=axis*(d-l1-l2+.0001);d=(goal-a).length
    pole=b-a;pole-=axis*pole.dot(axis);pole.normalize()
    along=(l1*l1-l2*l2+d*d)/(2*d);elbow=a+axis*along+pole*math.sqrt(max(0,l1*l1-along*along))
    p[un]=Matrix.LocRotScale(a,(b-p[un].translation).rotation_difference(elbow-a)@p[un].to_quaternion(),p[un].to_scale())
    p[ln]=Matrix.LocRotScale(elbow,(c-b).rotation_difference(goal-elbow)@p[ln].to_quaternion(),p[ln].to_scale())
    for n in names:
        if n==hn or n.endswith('_'+side) and n.startswith(('thumb','index','middle','ring','pinky')):p[n].translation+=shift
        elif n.endswith('_'+side) and n.startswith(('upperarm_twist','lowerarm_twist')):p[n]=p[parents[n]]@lr[n]

def empty_charging_tail(p,k):
    """Match the actual T-handle and keep the full M4 arm deformation."""
    f=k*.5
    weapon=p['WPN_root']
    travel=stroke*smooth((f-125)/12)*(1-smooth((f-139)/4))
    handle=rootinv@newbase['WPN_ChargingHandle'];handle.translation.y+=travel
    p['WPN_ChargingHandle']=weapon@handle
    p['WPN_ChargingHandleLatch']=p['WPN_ChargingHandle']@lr['WPN_ChargingHandleLatch']
    # The handle moves independently until it catches the already locked bolt.
    bolt=rootinv@newbase['WPN_bolt'];bolt.translation.y+=max(.035,travel) if f<=139 else travel
    p['WPN_bolt']=weapon@bolt
    catch=rootinv@newbase['WPN_BoltCatch']
    catch_turn=Matrix.Rotation(math.radians(10)*(1-smooth((f-134)/3)),4,'Y')
    p['WPN_BoltCatch']=weapon@Matrix.Translation(catch.translation)@catch_turn@catch.to_3x3().to_4x4()
    # Rotate the separate latch about its forward hinge, not its mesh centre.
    latch_bounds=charging_reference['M16A2_ChargingHandleLatch']['bounds_cm']
    hinge=fit@Vector((latch_bounds[0][1],sum(latch_bounds[1])*.5,sum(latch_bounds[2])*.5))
    hinge.y+=travel
    latch_weight=smooth((f-119)/5)*(1-smooth((f-139)/4))
    turn=Matrix.Translation(hinge)@Matrix.Rotation(math.radians(-12)*latch_weight,4,'Z')@Matrix.Translation(-hinge)
    p['WPN_ChargingHandleLatch']=weapon@turn@weapon.inverted()@p['WPN_ChargingHandleLatch']
    if f<111:return
    donor=charge_donors[k]
    donor_travel=(donor['WPN_root'].inverted()@donor['WPN_ChargingHandle']).translation.y-charge_closed.translation.y
    contact_weight=smooth((f-111)/14)*(1-smooth((f-139)/23))
    shift=weapon.to_3x3()@((handle_contact_shift+Vector((0,travel-donor_travel,0)))*contact_weight)
    for n in oldnames:
        if n.endswith('_r'):p[n].translation+=shift

actions={}
(O/'Export').mkdir(exist_ok=True)
for kind,poses in cache.items():
    end=sources[kind][1]
    baked=[]
    for k,old in enumerate(poses):
        f=k*.5;p={n:m.copy() for n,m in old.items()}
        for n in names:
            if n in newbase:
                p[n]=(old[n]@oldrest[n].inverted()@rest[n]) if n in oldrest else p[parents[n]]@lr[n]
        for n in markers:p[n]=p['WPN_root']@rest['WPN_root'].inverted()@rest[n]
        q=p['WPN_root'].to_quaternion()
        # Keep the accepted M4 reload arm chain intact, including twist bones.
        # Re-solving the arm and resetting twists erased the donor's forearm roll.
        # The empty tail uses the existing right-hand charging action.
        if kind not in ['reload','reload_empty']:
            support=1.
            if kind=='equip_charge':support=0.
            elif kind.startswith('sprint_'):
                support=0. if kind=='sprint_loop' else 1-smooth(f/end) if kind=='sprint_enter' else smooth(f/end)
            shift_arm(p,'l',q@(support_shift*support))
        elif kind=='reload_empty':empty_charging_tail(p,k)
        if kind=='equip_charge':
            weight=smooth(f/7)*(1-smooth((f-29)/9))
            shift_arm(p,'r',(p['WPN_ChargingHandle'].translation-old['WPN_ChargingHandle'].translation)*weight)
        # Additional mechanical pieces retain separate rigid bones. The cover
        # remains in its authored open pose; the mag release depresses at release.
        if kind in ['reload','reload_empty']:
            out=29 if kind=='reload' else 21
            press=smooth((f-out+5)/3)*(1-smooth((f-out-1)/5))
            p['WPN_MagazineRelease'].translation+=q@Vector((-.002*press,0,0))
        baked.append(p)
    a=bpy.data.actions.new('M16_'+kind);a.use_fake_user=True;rig.animation_data.action=a
    previous={}
    for k,p in enumerate(baked):
        for n in names:
            m=lr[n].inverted()@(p[parents[n]].inverted()@p[n] if parents[n] else p[n])
            loc,rot,scale=m.decompose()
            if n in previous and previous[n].dot(rot)<0:rot.negate()
            previous[n]=rot.copy();b=rig.pose.bones[n];b.rotation_mode='QUATERNION'
            b.location=loc;b.rotation_quaternion=rot;b.scale=scale
            for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=k*.5)
    for layer in a.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    scene.render.fps=60;scene.frame_start=0;scene.frame_end=end
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(O/'Export'/f'A_M16_{kind}.fbx'),use_selection=True,
        object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_step=.5,bake_anim_simplify_factor=0)
    actions[kind]=a
    print('M16 exported '+kind,flush=True)
action(actions['idle']);scene.frame_set(0);scene.frame_end=180
bpy.ops.object.select_all(action='DESELECT')
for ob in [rig,hands,*parts.values()]:ob.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'Export/SK_M16_Manny.fbx'),use_selection=True,
    object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M16_Manny_Editable.blend'))
receipt['sight_markers_receiver_m']={n:list(rootinv@newbase[n].translation) for n in markers}
(O/'build.json').write_text(json.dumps(receipt,indent=2))
print('M16_BUILD_COMPLETE',flush=True)
