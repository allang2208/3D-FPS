"""V7: staggered, elbow-led right-palm recovery on the V6 bow action.

Read the V6 source, preserve its left wrist and all weapon/impact trajectories,
and replace only the unloaded right arm after follow-through. Background bake.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
P=Path(__file__).parent
ROOT=P.parents[1]
PRIOR=P.parent/'BowQuickCombatWrist20260927'
source=PRIOR/'author_wrist.py'
prior={'__file__':str(source)}
exec(compile(source.read_text().split('\nbpy.ops.wm.open_mainfile')[0],str(source),'exec'),prior)
for key in ('rest','local','parent','order','mat','smooth','world_to_blender',
            'limb_frame','anatomy','R','L','G','RELEASE','timing','keys'):
    globals()[key]=prior[key]
palm=prior['prior']
idle=palm['idle'];idle_local=palm['idle_local']
FPS=240
OUT=P/'Export';OUT.mkdir(parents=True,exist_ok=True)
START=.56
CLEAR=.625
SETTLE=.885

def ease(x):
    x=max(0.,min(1.,x))
    return x*x*x*(10.+x*(-15.+6.*x))

def curve(points,t,initial_velocity=None):
    """C1 Hermite path, inherited entry velocity and zero-speed final arrival."""
    if t<=points[0][0]:return points[0][1].copy()
    if t>=points[-1][0]:return points[-1][1].copy()
    for i,((a,p),(b,q)) in enumerate(zip(points,points[1:])):
        if a<=t<=b:
            v0=(initial_velocity if initial_velocity is not None else Vector()) if i==0 else (q-points[i-1][1])/(b-points[i-1][0])
            v1=Vector() if i+2==len(points) else (points[i+2][1]-p)/(points[i+2][0]-a)
            u=(t-a)/(b-a)
            return p*(2*u**3-3*u*u+1)+v0*(b-a)*(u**3-2*u*u+u)+q*(-2*u**3+3*u*u)+v1*(b-a)*(u**3-u*u)

start=prior['pose'](START)
near_before=prior['pose'](START-.001)
near_after=prior['pose'](START+.001)
velocities={n:(near_after[n].translation-near_before[n].translation)/.002
            for n in ('hand_r','lowerarm_r','upperarm_r')}
clear=(palm['bow_at'](CLEAR)@palm['right_contact']).translation+Vector((-4.,1.5,-1.))
wrist_keys=[(START,start['hand_r'].translation),(CLEAR,clear),
            (.750,clear.lerp(idle['hand_r'].translation,.53)+Vector((-2.,-4.,-3.))),
            (.840,idle['hand_r'].translation+Vector((3.,-6.,6.))),
            (SETTLE,idle['hand_r'].translation)]
shoulder_keys=[(START,start['upperarm_r'].translation),(SETTLE,idle['upperarm_r'].translation)]
elbow_keys=[(START,start['lowerarm_r'].translation),
            (.735,start['lowerarm_r'].translation.lerp(idle['lowerarm_r'].translation,.52)+Vector((-3.,-4.,-3.))),
            (SETTLE,idle['lowerarm_r'].translation)]
finger_times={'index':(.615,.820),'middle':(.620,.825),
              'ring':(.630,.835),'pinky':(.635,.840),'thumb':(.650,.855)}
right_names={'clavicle_r'}
for n in order:
    if parent[n] in right_names and n!='bow_nock':right_names.add(n)

def pose(t):
    w=prior['pose'](t)
    if t<=START:return w
    if t>=SETTLE:
        for n in right_names:w[n]=idle[n].copy()
        return w
    clav,up,low,hand='clavicle_r','upperarm_r','lowerarm_r','hand_r'
    wrist=curve(wrist_keys,t,velocities[hand])
    # Retain the incoming bow rotation during detachment. Its angular speed
    # is already zero at LetGo; stop following it there, without a hard turn.
    carrying=palm['bow_at'](min(t,RELEASE))@palm['right_contact']
    rotation=carrying.to_quaternion().slerp(idle[hand].to_quaternion(),ease((t-.595)/(.855-.595)))
    target=mat(wrist,rotation.to_matrix())
    shoulder=curve(shoulder_keys,t,velocities[up])
    pole=curve(elbow_keys,t,velocities[low])
    l1,l2=local[low].translation.length,local[hand].translation.length
    axis=(wrist-shoulder).normalized()
    distance=(wrist-shoulder).length
    reach=(l1+l2)*.945
    if distance>reach:
        shoulder+=axis*(distance-reach)
        distance=reach
    bend=pole-shoulder-axis*(pole-shoulder).dot(axis)
    bend.normalize()
    along=(l1*l1-l2*l2+distance*distance)/(2.*distance)
    elbow=shoulder+axis*along+bend*math.sqrt(max(0.,l1*l1-along*along))
    ud,ld=(elbow-shoulder).normalized(),(wrist-elbow).normalized()
    ru,rl=rest[low].translation-rest[up].translation,rest[hand].translation-rest[low].translation
    across=R@Vector(anatomy['r']['across'])
    hand_delta=target.to_3x3()@rest[hand].to_3x3().transposed()
    lower_delta=limb_frame(ld,hand_delta@across)@limb_frame(rl,across).transposed()
    upper_delta=limb_frame(ud,ud.cross(ld))@limb_frame(ru,ru.cross(rl)).transposed()
    compatible=limb_frame(ud,hand_delta@across)@limb_frame(ru,across).transposed()
    upper_rotation=upper_delta.to_quaternion().slerp(compatible.to_quaternion(),.20).to_matrix()@rest[up].to_3x3()
    lower_rotation=lower_delta@rest[low].to_3x3()
    # Restore the native idle axial frames during the movement, avoiding the
    # old second, whole-arm fade near the endpoint. Geometry stays on the IK.
    roll=ease((t-.665)/(SETTLE-.665))
    idle_ud=(idle[low].translation-idle[up].translation).normalized()
    idle_ld=(idle[hand].translation-idle[low].translation).normalized()
    idle_up=idle_ud.rotation_difference(ud).to_matrix()@idle[up].to_3x3()
    idle_low=idle_ld.rotation_difference(ld).to_matrix()@idle[low].to_3x3()
    upper_rotation=upper_rotation.to_quaternion().slerp(idle_up.to_quaternion(),roll).to_matrix()
    lower_rotation=lower_rotation.to_quaternion().slerp(idle_low.to_quaternion(),roll).to_matrix()
    w[clav]=idle[clav].copy()
    w[clav].translation=shoulder-w[clav].to_3x3()@local[up].translation
    w[up],w[low],w[hand]=mat(shoulder,upper_rotation),mat(elbow,lower_rotation),target
    descendants={up,low,hand}
    for n in order:
        if parent[n] not in descendants or n in (low,hand,'bow_nock'):continue
        descendants.add(n)
        relative=local[n].copy()
        if n in palm['right_open_local']:
            digit=n.split('_')[0]
            a,b=finger_times.get(digit,(.625,.84))
            relative=palm['blend_frame'](palm['right_open_local'][n],idle_local[n],ease((t-a)/(b-a)))
        w[n]=w[parent[n]]@relative
    return w

bpy.ops.wm.open_mainfile(filepath=str(PRIOR/'Bow_QuickCombat.blend'))
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['Bow_V7_Native'];arm=rig.data
scene=bpy.context.scene;scene.render.fps=FPS
rig.animation_data_create()
rig.animation_data.action=bpy.data.actions.new('A_Bow_QuickCombat_RecoveryNatural')
scene.frame_start=0;scene.frame_end=round(L*FPS)
last={}
for frame in range(scene.frame_end+1):
    world=pose(frame/FPS)
    for n in order:
        b=rig.pose.bones[n]
        relative=world_to_blender(world[parent[n]]).inverted()@world_to_blender(world[n]) if parent[n] else world_to_blender(world[n])
        restlocal=arm.bones[parent[n]].matrix_local.inverted()@arm.bones[n].matrix_local if parent[n] else arm.bones[n].matrix_local
        b.rotation_mode='QUATERNION';b.matrix_basis=restlocal.inverted()@relative
        if frame and b.rotation_quaternion.dot(last[n])<0:b.rotation_quaternion.negate()
        last[n]=b.rotation_quaternion.copy()
        for prop in ('location','rotation_quaternion','scale'):b.keyframe_insert(prop,frame=frame)
scene.frame_set(0);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(OUT/'A_Bow_QuickCombat.fbx'),use_selection=True,
    object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Bow_QuickCombat.blend'))
(P/'authoring.json').write_text(json.dumps({
    'fps':FPS,'timing_seconds':timing,
    'asset':'/Game/Weapons/DarkBow20260925/QuickCombat20260926/A_Bow_QuickCombat',
    'prior_source':str(source),'right_recover_start':START,'right_recover_settle':SETTLE,
    'wrist_path':[(t,list(p)) for t,p in wrist_keys],
    'finger_relaxation_seconds':finger_times,
    'change':'Release, continuous curved tuck, staggered palm/finger relaxation, idle axial handoff',
    'preserved':'V6 left wrist, bow path, push contact, source length and runtime impact/speed',
    'rendered':False,'runtime_tested':False},indent=2),encoding='utf-8')
print('BOW_RECOVERY_AUTHORED',str(OUT/'A_Bow_QuickCombat.fbx'))
