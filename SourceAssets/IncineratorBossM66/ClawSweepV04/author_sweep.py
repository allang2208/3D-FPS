"""M66 attack 01: loaded right-arm claw sweep, planted feet, asymmetric recovery."""
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66')
exec((BASE/'ReactionsV03/author_reactions.py').read_text(encoding='utf-8').split('\ncontracts=[]')[0])
ROOT=BASE/'ClawSweepV04'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
DURATION=2.6;CONTACT_START=1.;CONTACT_END=1.35
upper,lower,wrist='Bone_027','Bone_026','Bone_025'
finger_roots=['Bone_057','Bone_061','Bone_065','Bone_069','Bone_073']
hand_direction=(neutral['Bone_066'].translation-neutral[wrist].translation).normalized()
hand_width=(neutral['Bone_073'].translation-neutral['Bone_061'].translation).normalized()
hand_normal=hand_width.cross(hand_direction).normalized()
finger_axes={}
for root in finger_roots:
    for i in range(4):
        n='Bone_%03d'%(int(root[-3:])-i)
        direction=rest[n].to_quaternion()@Vector((0,1,0))
        bend=direction.cross(hand_normal).normalized()
        finger_axes[n]=rest[n].to_quaternion().inverted()@bend

def phase(a,b,t):return smooth((t-a)/(b-a))
def descendant(n,ancestor):
    while parents[n]:
        n=parents[n]
        if n==ancestor:return True
    return False
hand_children=[n for n in ordered if descendant(n,wrist)]

def pose_sweep(t):
    load=phase(.12,.86,t);swing=phase(.98,1.30,t);release=phase(1.48,DURATION,t)
    held=load*(1-release)
    twist=math.radians(-19+55*swing)*held
    fingers=phase(0,.25,t)*(1-release)
    # The mass shift leads the wrist; the rear sacs respond after the strike.
    body_swing=phase(.91,1.22,t)
    lag=math.sin(max(0.,t-1.08)*18)*math.exp(-4*max(0.,t-1.08))*phase(.98,1.16,t)*(1-release)
    worlds={}
    for n in ordered:
        world=worlds[parents[n]]@nlocal[n] if parents[n] else nlocal[n].copy()
        if n=='Bone_000':
            world.translation+=Vector(((-.035+.09*body_swing)*held,-.045*held,-.065*held))
            world=rotate(world,(0,0,1),twist*.20)
        if n in ('Bone_007','Bone_006','Bone_005'):
            world=rotate(world,(0,0,1),twist*.22)
            world=rotate(world,(1,0,0),.025*held)
        if n=='Bone_020':world=rotate(world,(0,0,1),twist*.14)
        if n=='Bone_032':world=rotate(world,(1,0,0),.07*held)
        if n=='Bone_031':world=rotate(world,(0,1,0),-.045*held)
        if n.startswith('M66_Sac'):
            world=rotate(world,(0,0,1),-.035*lag)
            world=world@Matrix.Diagonal((1+.008*held,1+.008*held,1+.004*held,1))
        if n.startswith('M66_Vent'):world=rotate(world,(0,1,0),(.055 if n.endswith('Tip') else .025)*lag)
        worlds[n]=world
    # Wrist traces an arc; extending the existing fingers supplies the reach.
    # Keep authored bone lengths, rather than stretching the mesh to a radius.
    angle=math.radians(78-135*swing)
    radial=Vector((-math.sin(angle),-math.cos(angle),0))
    goal=Vector((centre.x,centre.y,2.12))+radial*.85
    goal.z+=.10*math.sin(math.pi*swing)
    standing_wrist=worlds[wrist].translation.copy()
    target=standing_wrist.lerp(goal,held)
    shoulder=worlds[upper].translation.copy()
    a=(rest[lower].translation-rest[upper].translation).length
    b=(rest[wrist].translation-rest[lower].translation).length
    direction=(target-shoulder).normalized()
    distance=max(abs(a-b)+.02,min((target-shoulder).length,a+b-.004))
    target=shoulder+direction*distance
    parent_delta=worlds[parents[upper]].to_quaternion()@neutral[parents[upper]].to_quaternion().inverted()
    pole=parent_delta@(rest[lower].translation-rest[upper].translation)
    pole=(pole-direction*pole.dot(direction)).normalized()
    along=(a*a-b*b+distance*distance)/(2*distance)
    elbow=shoulder+direction*along+pole*math.sqrt(max(0,a*a-along*along))
    for n,start,end in ((upper,shoulder,elbow),(lower,elbow,target)):
        q=(worlds[parents[n]]@nlocal[n]).to_quaternion()
        q=(q@Vector((0,1,0))).rotation_difference((end-start).normalized())@q
        worlds[n]=q.to_matrix().to_4x4();worlds[n].translation=start
    neutral_q=neutral[wrist].to_quaternion()
    desired_direction=(radial+Vector((0,0,-.38))).normalized()
    attack_q=hand_direction.rotation_difference(desired_direction)@neutral_q
    q=neutral_q.slerp(attack_q,held)
    worlds[wrist]=q.to_matrix().to_4x4();worlds[wrist].translation=target
    for n in hand_children:
        world=worlds[parents[n]]@nlocal[n]
        if n in finger_axes:
            # Unfurl first, then hook through the strike; knuckles lead tips.
            curl=(-.10+.24*phase(.97,1.24,t))*fingers
            world=world@Quaternion(finger_axes[n],curl).to_matrix().to_4x4()
        if n in finger_roots:
            index=finger_roots.index(n)-2
            axis=rest[n].to_quaternion().inverted()@hand_direction
            world=world@Quaternion(axis,index*.025*fingers).to_matrix().to_4x4()
        worlds[n]=world
    solve_planted_legs(worlds);apply_worlds(worlds)

action=bpy.data.actions.new('A_M66_ClawSweep_V04');rig.animation_data.action=action;action.use_fake_user=True
frames=round(DURATION*60);scene.frame_start=0;scene.frame_end=frames;last={}
for frame in range(frames+1):
    scene.frame_set(frame);pose_sweep(frame/60.)
    for pb in rig.pose.bones:
        q=pb.rotation_quaternion.copy()
        if pb.name in last and q.dot(last[pb.name])<0:q.negate()
        pb.rotation_quaternion=q;last[pb.name]=q
        for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=pb.name)
action['M66_source']='Original M66 planted asymmetric right claw sweep; measured two-bone arm and leg placement'
action['contact_start']=CONTACT_START;action['contact_end']=CONTACT_END;action['loop']=False
scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
destination=ROOT/'Export/A_M66_ClawSweep_V04.fbx'
bpy.ops.export_scene.fbx(filepath=str(destination),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
    bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_claw_sweep_v04.blend'))
manifest={'source':str(SOURCE),'authoring':str(ROOT/'Authoring/M66_claw_sweep_v04.blend'),
 'clips':[{'role':'ClawSweep','action':action.name,'fbx':str(destination),'seconds':DURATION,'fps':60,'frames':frames+1,'loop':False}],
 'contact_start_seconds':CONTACT_START,'contact_end_seconds':CONTACT_END,'bones':len(rest),
 'mesh_modified':False,'runtime_tested':False,'rendered':False,'root_motion':False}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('M66_CLAW_SWEEP_AUTHORED '+str(DURATION),flush=True)
