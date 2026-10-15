"""Authored M66 reactions on the user's repaired rig; preserves mesh and weights."""
from pathlib import Path
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66')
# Reuse the accepted rig coordinates and measured leg chains, not its export loop.
exec((BASE/'LocomotionV02/author_locomotion.py').read_text(encoding='utf-8').split('contracts=[]')[0])
import numpy as np
ROOT=BASE/'ReactionsV03'
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
pose_frame('Idle',0.);bpy.context.view_layer.update()
neutral={n:rig.pose.bones[n].matrix.copy() for n in ordered}
nlocal={n:neutral[parents[n]].inverted()@neutral[n] if parents[n] else neutral[n].copy() for n in ordered}
pivot=neutral['Bone_000'].translation.copy()
base_feet={side:neutral[foot].translation.copy() for side,_,_,foot in chains}
floor_z=min((mesh.matrix_world@v.co).z for v in mesh.data.vertices)
previous_quats={}

def pulse(t):
    if t<.14:return smooth(t/.14)
    if t<.28:return 1.-.12*smooth((t-.14)/.14)
    return .88*(1.-smooth((t-.28)/.57))

def apply_worlds(worlds):
    for n in ordered:
        pb=rig.pose.bones[n];pb.rotation_mode='QUATERNION'
        parent=worlds[parents[n]]@local[n] if parents[n] else local[n]
        pb.matrix_basis=parent.inverted()@worlds[n]

def solve_planted_legs(worlds):
    for side,upper,lower,foot in chains:
        target=base_feet[side];hip=worlds[upper].translation.copy()
        a=(rest[lower].translation-rest[upper].translation).length
        b=(rest[foot].translation-rest[lower].translation).length
        axis=(target-hip).normalized();dist=max(.01,min((target-hip).length,a+b-.001))
        pole=rest[lower].translation-rest[upper].translation
        pole=(pole-axis*pole.dot(axis)).normalized()
        along=(a*a-b*b+dist*dist)/(2*dist)
        knee=hip+axis*along+pole*math.sqrt(max(0.,a*a-along*along))
        for n,start,end in ((upper,hip,knee),(lower,knee,target)):
            q=(worlds[parents[n]]@nlocal[n]).to_quaternion()
            q=(q@Vector((0,1,0))).rotation_difference((end-start).normalized())@q
            worlds[n]=q.to_matrix().to_4x4();worlds[n].translation=start
        worlds[foot]=neutral[foot].copy()
        for n in ordered:
            ancestor=parents[n]
            while ancestor:
                if ancestor==foot:
                    worlds[n]=worlds[parents[n]]@nlocal[n];break
                ancestor=parents[ancestor]

def make_pose(role,t,duration):
    rotations={};offset=Vector((0,0,0));tilt=roll=collapse=0.;wave=0.
    def rot(n,axis,angle):rotations.setdefault(n,[]).append((axis,angle))
    if role.startswith('Hit'):
        strength=pulse(t);delayed=pulse(max(0,t-.055))
        ax,ay={'HitFront':(-1,0),'HitBack':(1,0),'HitRight':(0,1),'HitLeft':(0,-1)}[role]
        tilt=ax*.10*strength;roll=ay*.09*strength
        offset=Vector((ay*.035,-ax*.035,-.045*strength))
        for n in ('Bone_007','Bone_006','Bone_005'):
            rot(n,(1,0,0),ax*.025*strength);rot(n,(0,1,0),ay*.022*strength)
        rot('Bone_027',(1,0,0),-.12*delayed);rot('Bone_026',(0,1,0),.08*delayed)
        rot('Bone_032',(1,0,0),.06*strength)
        wave=math.sin(22*t)*math.exp(-5*t)*strength
    elif role=='Stun':
        phase=TAU*t/duration;tilt=.052*math.sin(phase);roll=.067*math.sin(phase+.8)
        offset=Vector((.035*math.sin(phase+.4),.018*math.sin(2*phase),-.035*(1+math.sin(phase))*.5))
        for n in ('Bone_006','Bone_005'):rot(n,(1,0,0),.025*math.sin(phase-.4))
        rot('Bone_027',(1,0,0),.075*math.sin(phase-.8))
        rot('Bone_026',(0,0,1),.045*math.sin(phase-1.3));wave=.3*math.sin(phase-1.1)
    elif role=='Airborne':
        curl=smooth(t/.3);phase=TAU*max(0,t-.3)/.8
        tilt=-.26*curl+.025*math.sin(phase)*curl;roll=-.10*curl
        rot('Bone_012',(1,0,0),-.40*curl);rot('Bone_017',(1,0,0),-.24*curl)
        rot('Bone_011',(1,0,0),.72*curl);rot('Bone_016',(1,0,0),.55*curl)
        rot('Bone_027',(1,0,0),.24*curl);rot('Bone_026',(0,0,1),.16*curl)
        wave=.6*math.sin(phase-.5)*curl
    else:
        if role=='Landing':
            collapse=smooth(t/.75)
            shock=math.sin(math.pi*min(1,t/.28))**2
            offset.z=-.20*shock;wave=math.sin(24*t)*math.exp(-5*t)
        elif role=='GetUp':
            # Pause on the right side, brace the giant arm, then lift hips and torso.
            collapse=1.-smooth((t-.35)/2.55)
            brace=smooth(t/.5)*(1.-smooth((t-2.1)/.7))
            rot('Bone_027',(1,0,0),-.22*brace);rot('Bone_026',(0,0,1),-.18*brace)
            rot('Bone_036',(1,0,0),.18*brace)
            wave=.12*math.sin(6*t)*math.sin(math.pi*min(1,t/duration))
        else:
            collapse=smooth((t-.22)/1.48)
            buckle=smooth(t/.32)*(1.-smooth((t-.8)/.65))
            offset.z=-.28*buckle;wave=math.sin(15*max(0,t-.8))*math.exp(-5*max(0,t-.8))*collapse
        tilt=-1.16*collapse;roll=-.42*collapse
        offset.x-=.17*collapse;offset.y+=.15*collapse
        rot('Bone_012',(1,0,0),-.32*collapse);rot('Bone_017',(1,0,0),-.48*collapse)
        rot('Bone_011',(1,0,0),.88*collapse);rot('Bone_016',(1,0,0),1.02*collapse)
        rot('Bone_027',(1,0,0),-.32*collapse);rot('Bone_026',(0,0,1),.24*collapse)
        rot('Bone_032',(1,0,0),.15*collapse)
    rot('Bone_000',(1,0,0),tilt);rot('Bone_000',(0,1,0),roll)
    for n in ordered:
        if n.startswith('M66_Sac'):rot(n,(1,0,0),.028*wave)
        if n.startswith('M66_Vent'):rot(n,(0,1,0),(.05 if n.endswith('Tip') else .025)*wave)
        if n in ('Bone_057','Bone_061','Bone_065','Bone_069','Bone_073'):
            rot(n,(1,0,0),.06*collapse)
    worlds={}
    for n in ordered:
        m=worlds[parents[n]]@nlocal[n] if parents[n] else nlocal[n].copy()
        if n=='Bone_000':m.translation+=offset
        for axis,angle in rotations.get(n,[]):m=rotate(m,axis,angle)
        worlds[n]=m
    if role.startswith('Hit') or role=='Stun':solve_planted_legs(worlds)
    apply_worlds(worlds)
    if role in ('Landing','GetUp','Death'):
        # Author body-floor placement from the deformed surface, in centimetre-
        # consistent rig coordinates. The actor owns actual airborne travel.
        bpy.context.view_layer.update();evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
        coords=np.empty(len(evaluated.data.vertices)*3,dtype=np.float32)
        evaluated.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
        transform=np.array(evaluated.matrix_world,dtype=np.float64)
        z=coords@transform[2,:3]+transform[2,3]
        shift=Vector((0,0,floor_z-float(z.min())))
        local_shift=rig.matrix_world.inverted().to_3x3()@shift
        for m in worlds.values():m.translation+=local_shift
        apply_worlds(worlds)

contracts=[]
for role,seconds in [('HitFront',.85),('HitRight',.85),('HitBack',.85),('HitLeft',.85),
                     ('Stun',2.8),('Airborne',1.1),('Landing',.9),('GetUp',3.2),('Death',2.3)]:
    action=bpy.data.actions.new('A_M66_'+role+'_V03');rig.animation_data.action=action
    action.use_fake_user=True;frames=round(seconds*60);scene.frame_start=0;scene.frame_end=frames
    previous_quats={}
    for frame in range(frames+1):
        scene.frame_set(frame);make_pose(role,frame/60.,seconds)
        for pb in rig.pose.bones:
            q=pb.rotation_quaternion.copy()
            if pb.name in previous_quats and q.dot(previous_quats[pb.name])<0:q.negate()
            pb.rotation_quaternion=q;previous_quats[pb.name]=q
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=pb.name)
    action['M66_source']='Original asymmetric M66 reaction, existing repaired user rig'
    action['loop']=role=='Stun';scene.frame_set(0)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
    destination=ROOT/'Export'/('A_M66_'+role+'_V03.fbx')
    bpy.ops.export_scene.fbx(filepath=str(destination),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_use_all_bones=True,bake_anim_force_startend_keying=True,
        bake_anim_step=1.,bake_anim_simplify_factor=0.,use_mesh_modifiers=False,axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
    contracts.append({'role':role,'action':action.name,'fbx':str(destination),'seconds':seconds,'frames':frames+1,'fps':60,'loop':role=='Stun'})
    print('M66_EXPORTED '+role,flush=True)
rig.animation_data.action=bpy.data.actions['A_M66_Death_V03']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_start=0;scene.frame_end=138;scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_reactions_v03.blend'))
manifest={'source':str(SOURCE),'authoring':str(ROOT/'Authoring/M66_reactions_v03.blend'),
    'clips':contracts,'bones':len(rest),'mesh_modified':False,'root_motion':False,
    'hit_impact_seconds':.14,'hit_recovery_start_seconds':.28,'air_loop_start_seconds':.3,
    'death_physics_handoff_seconds':.9,'runtime_tested':False,'rendered':False,
    'method':'Original four-direction planted recoil, asymmetric sway, airborne curl, surface-grounded landing/get-up and death; delayed arm/sac/vent motion'}
(ROOT/'Records/animation_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('M66_REACTIONS_AUTHORED '+str(len(contracts)),flush=True)
