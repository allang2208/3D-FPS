"""Fit library motion to the retained Meshy skin and author the standing spit.

Library body motion is preserved; the attack is a custom edit, not an unmodified
pack clip. No renders or gameplay tests are run by this production script.
"""
import bpy, json, math, statistics
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
OUT=ROOT/'Final';OUT.mkdir(exist_ok=True)
SAMPLE_FPS=120
metadata=json.loads((ROOT/'native.json').read_text(encoding='utf-8'))
cache={}
for role,spec in metadata.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=spec['fbx'],use_image_search=False)
    donor=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    scene=bpy.context.scene;rate=scene.render.fps/scene.render.fps_base
    action=donor.animation_data.action;first=action.frame_range[0]
    frames=[]
    for i in range(round(spec['seconds']*SAMPLE_FPS)+1):
        frame=first+i/SAMPLE_FPS*rate
        scene.frame_set(math.floor(frame),subframe=frame%1)
        frames.append({b.name:donor.matrix_world@b.matrix for b in donor.pose.bones})
    cache[role]={'rest':{b.name:donor.matrix_world@b.matrix_local for b in donor.data.bones},
                 'frames':frames,'seconds':spec['seconds']}

bpy.ops.wm.open_mainfile(filepath=str(BASE/'SpitterZombie_Animated.blend'))
scene=bpy.context.scene;rig=next(o for o in scene.objects if o.type=='ARMATURE')
meshes=[o for o in scene.objects if o.type=='MESH'];bones=list(rig.pose.bones)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
world_rest={n:rig.matrix_world@m for n,m in rest.items()};inv=rig.matrix_world.inverted()
for b in bones:b.rotation_mode='QUATERNION'
for tr in rig.animation_data.nla_tracks:tr.mute=True
def active(action):
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
def update():bpy.context.view_layer.update()
active(bpy.data.actions['A_Spitter_Idle']);scene.frame_set(0);update()
idle={b.name:b.matrix_basis.copy() for b in bones}
idle_world={b.name:rig.matrix_world@b.matrix for b in bones}
idle_tail={b.name:rig.matrix_world@b.tail for b in bones}
def wm(name):return rig.matrix_world@rig.pose.bones[name].matrix
def point(name):return wm(name).translation
def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)
def ramp(a,b,t):return smooth((t-a)/(b-a))
def lerp_matrix(a,b,t):
    return Matrix.LocRotScale(a.translation.lerp(b.translation,t),
        a.to_quaternion().slerp(b.to_quaternion(),t),a.to_scale().lerp(b.to_scale(),t))
def mix(a,b,w):return {n:lerp_matrix(a[n],b[n],w) for n in a}
def apply(pose):
    for b in bones:b.matrix_basis=pose[b.name]
    update()
def snapshot():return {b.name:b.matrix_basis.copy() for b in bones}
def sample(role,t):
    data=cache[role];f=max(0.,min(t*SAMPLE_FPS,len(data['frames'])-1))
    lo=int(f);hi=min(lo+1,len(data['frames'])-1);weight=f-lo
    matrices={};result={}
    for b in bones:
        n=b.name;a=data['frames'][lo][n];c=data['frames'][hi][n]
        q=a.to_quaternion().slerp(c.to_quaternion(),weight)
        delta=q@data['rest'][n].to_quaternion().inverted()
        q=(inv.to_quaternion()@delta@world_rest[n].to_quaternion()).normalized()
        bone=rig.data.bones[n]
        if bone.parent:
            pos=matrices[bone.parent.name]@(rest[bone.parent.name].inverted()@rest[n]).translation
        else:
            pos=inv@a.translation.lerp(c.translation,weight)
        m=Matrix.LocRotScale(pos,q,Vector((1,1,1)));matrices[n]=m
        result[n]=((rest[bone.parent.name].inverted()@rest[n]).inverted()@matrices[bone.parent.name].inverted()@m
                   if bone.parent else rest[n].inverted()@m)
    return result
def set_rotation(name,q):
    old=wm(name);rig.pose.bones[name].matrix=inv@Matrix.LocRotScale(old.translation,q,old.to_scale());update()
def aim(name,old,new):
    set_rotation(name,old.normalized().rotation_difference(new.normalized())@wm(name).to_quaternion())
def direction(name):return (rig.matrix_world@rig.pose.bones[name].tail-point(name)).normalized()
def move_hips(offset):
    m=wm('Hips');m.translation+=offset;rig.pose.bones['Hips'].matrix=inv@m;update()
def ground():
    deps=bpy.context.evaluated_depsgraph_get();low=float('inf')
    for mesh in meshes:
        obj=mesh.evaluated_get(deps);skin=obj.to_mesh()
        low=min(low,min((obj.matrix_world@v.co).z for v in skin.vertices));obj.to_mesh_clear()
    move_hips(Vector((0,0,.003-low)))

# Keep the head oriented toward the same forward authoring target as the earlier
# contract. This is a baked direction, not a new runtime target-tracking system.
GAZE=Vector((0,-4,1.60))
head_rest=world_rest['Head'];rest_front=(rig.matrix_world@rig.data.bones['headfront'].head_local-head_rest.translation).normalized()
rest_up=rig.matrix_world@rig.data.bones['head_end'].head_local-head_rest.translation
rest_up=(rest_up-rest_front*rest_up.dot(rest_front)).normalized()
head_up_local=head_rest.to_quaternion().inverted()@rest_up
eye_local=head_rest.to_quaternion().inverted()@(rest_front*.10+rest_up*.075)
def gaze(weight=1.):
    before={n:rig.pose.bones[n].matrix_basis.copy() for n in ['neck','Head']}
    # Let the neck share compensation; retain a small amount of source cant.
    neck_dir=direction('neck');desired=Vector((neck_dir.x*.25,-.12,1)).normalized()
    aim('neck',neck_dir,neck_dir.lerp(desired,.60))
    for _ in range(3):
        q=wm('Head').to_quaternion();eye=point('Head')+q@eye_local
        face=(point('headfront')-point('Head')).normalized()
        set_rotation('Head',face.rotation_difference((GAZE-eye).normalized())@q)
    q=wm('Head').to_quaternion();face=(point('headfront')-point('Head')).normalized()
    up=q@head_up_local;up=(up-face*up.dot(face)).normalized()
    vertical=Vector((0,0,1));vertical=(vertical-face*vertical.dot(face)).normalized()
    angle=math.atan2(face.dot(up.cross(vertical)),up.dot(vertical))
    set_rotation('Head',Quaternion(face,angle*.82)@q)
    for n in ['neck','Head']:
        bone=rig.pose.bones[n];bone.matrix_basis=lerp_matrix(before[n],bone.matrix_basis,weight)
    update()

def key_pose(frame,previous):
    for b in bones:
        q=b.rotation_quaternion.copy()
        if b.name in previous and q.dot(previous[b.name])<0:q.negate()
        b.rotation_quaternion=q;previous[b.name]=q.copy()
        for prop in ['location','rotation_quaternion','scale']:b.keyframe_insert(prop,frame=frame,group=b.name)
def new_action(name,fps,seconds):
    old=bpy.data.actions.get(name)
    if old:bpy.data.actions.remove(old)
    action=bpy.data.actions.new(name);action.use_fake_user=True;active(action)
    scene.render.fps=fps;scene.render.fps_base=1;scene.frame_start=0;scene.frame_end=round(seconds*fps)
    return action
def export(name,action,fps,loop,source):
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [rig]+meshes:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    file=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'ARMATURE','MESH'},
        add_leaf_bones=False,bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',path_mode='STRIP')
    return {'file':str(file),'asset_name':name,'fps':fps,'seconds':scene.frame_end/fps,'loop':loop,'source':source}

report={'movement':{},'runtime_tested':False,'preview_rendered':False,'mesh_or_skin_modified':False}
for role in ['Walk_A','Walk_B','Walk_C','Run_A']:
    fps=60;seconds=round(metadata[role]['seconds']*fps)/fps
    name='A_Spitter_LibraryV7_'+role;action=new_action(name,fps,seconds)
    first_pose=sample(role,0);last_pose=sample(role,seconds)
    apply(first_pose);start_hip=point('Hips').copy()
    apply(last_pose);drift=point('Hips')-start_hip
    first_fitted=None;previous={};feet=[]
    for frame in range(scene.frame_end+1):
        t=frame/fps;phase=t/seconds;scene.frame_set(frame)
        apply(sample(role,t));move_hips(Vector((-drift.x*phase,-drift.y*phase,0)))
        gaze();ground()
        if first_fitted is None:first_fitted=snapshot()
        if t>seconds-.15:apply(mix(snapshot(),first_fitted,ramp(seconds-.15,seconds,t)))
        feet.append({side:list(point(side+'Foot')) for side in ['Left','Right']})
        key_pose(frame,previous)
    speeds=[]
    for side in ['Left','Right']:
        low=min(f[side][2] for f in feet)
        for i in range(1,len(feet)-1):
            vy=(feet[i+1][side][1]-feet[i-1][side][1])*fps*.5
            if feet[i][side][2]<low+.045 and vy>.08:speeds.append(vy*100)
    reference=statistics.median(speeds) if speeds else 130.
    entry=export(name,action,fps,True,metadata[role]['source']+'; native UE retarget, original bind lengths, grounding, forward gaze')
    entry['reference_speed_cm_s']=round(reference,3);report['movement'][role]=entry
    print('SPITTER_V7_MOVEMENT_SAVED',role,reference,flush=True)

def time_curve(keys,t):
    # Monotone Hermite time warp; retains the source's continuous motion.
    if t<=keys[0][0]:return keys[0][1]
    if t>=keys[-1][0]:return keys[-1][1]
    x=[p[0] for p in keys];y=[p[1] for p in keys]
    h=[x[i+1]-x[i] for i in range(len(x)-1)];d=[(y[i+1]-y[i])/h[i] for i in range(len(h))]
    m=[0.]*len(keys)
    for i in range(1,len(keys)-1):
        if d[i-1]*d[i]>0:
            a=2*h[i]+h[i-1];b=h[i]+2*h[i-1];m[i]=(a+b)/(a/d[i-1]+b/d[i])
    i=next(i for i in range(len(h)) if x[i]<=t<x[i+1]);v=(t-x[i])/h[i]
    return (2*v**3-3*v*v+1)*y[i]+(v**3-2*v*v+v)*h[i]*m[i]+(-2*v**3+3*v*v)*y[i+1]+(v**3-v*v)*h[i]*m[i+1]
def limb(upper,lower,tip,target,pole,tip_rotation):
    a=point(upper);b=point(lower);c=point(tip);l1=(b-a).length;l2=(c-b).length
    axis=(target-a).normalized();length=max(abs(l1-l2)+.001,min((target-a).length,(l1+l2)*.997))
    end=a+axis*length;side=pole-a-axis*(pole-a).dot(axis);side.normalize()
    along=(l1*l1-l2*l2+length*length)/(2*length)
    joint=a+axis*along+side*math.sqrt(max(0,l1*l1-along*along))
    aim(upper,b-a,joint-a);aim(lower,point(tip)-point(lower),end-point(lower));set_rotation(tip,tip_rotation)

# Extract the source D foot arc as authoring data, then direct that step forward.
step_data=[]
for i in range(67):
    t=i/120;apply(sample('Attack_D',t));step_data.append(point('LeftFoot').copy())
step_start=step_data[0];step_span=max((Vector((p.x-step_start.x,p.y-step_start.y,0))).length for p in step_data)
step_height=max(p.z-step_start.z for p in step_data)
def source_step(t):
    f=max(0,min(t*120,len(step_data)-1));i=int(f);p=step_data[i].lerp(step_data[min(i+1,len(step_data)-1)],f-i)
    extent=Vector((p.x-step_start.x,p.y-step_start.y,0)).length/max(.001,step_span)
    lift=max(0,p.z-step_start.z)/max(.001,step_height)
    return min(1,extent),lift
apply(sample('Attack_A',0));a_origin=point('Hips').copy()
apply(sample('Attack_A',.715));a_peak=point('Hips').copy()
forward_scale=.225/max(.10,a_origin.y-a_peak.y)
A_TIME=[(0,0),(.065,.12),(.165,.36),(.235,.55),(.275,.60),(1/3,.685),(.40,.715),(.49,.715),(1,.715)]
D_TIME=[(0,.73),(.43,.73),(.60,.83),(.78,1.0),(.94,1.13),(1,1.13)]
STEP_TIME=[(0,0),(.09,.12),(.18,.30),(.27,.53),(.65,.53),(1,.53)]

class PassiveArm:
    """Damped three-link chain driven only by the moving shoulder and gravity."""
    def __init__(self,side):
        self.side=side
        self.names=[side+'Arm',side+'ForeArm',side+'Hand']
        self.p=[idle_world[n].translation.copy() for n in self.names]+[idle_tail[side+'Hand'].copy()]
        self.old=[p.copy() for p in self.p]
        self.lengths=[(self.p[i+1]-self.p[i]).length for i in range(3)]
        self.sign=1 if self.p[0].x>idle_world['Hips'].translation.x else -1
    def solve(self,anchor,hips,chest):
        dt=1/120;self.p[0]=anchor.copy()
        for i in range(1,4):
            current=self.p[i].copy()
            velocity=(current-self.old[i])*(.985 if self.side=='Left' else .981)
            self.p[i]+=velocity+Vector((0,0,-9.81))*dt*dt
            self.old[i]=current
        axis=chest-hips
        for _ in range(12):
            self.p[0]=anchor.copy()
            for i,length in enumerate(self.lengths):
                delta=self.p[i+1]-self.p[i];distance=max(1e-8,delta.length)
                correction=delta*(1-length/distance)
                if i==0:self.p[i+1]-=correction
                else:self.p[i]+=correction*.5;self.p[i+1]-=correction*.5
            # Torso clearance, no hand reach or palm-contact target.
            for i in range(1,4):
                q=self.p[i];u=max(0,min(1,(q-hips).dot(axis)/max(1e-8,axis.length_squared)))
                center=hips+axis*u;delta=q-center;radius=.145 if i==1 else .13
                if delta.length<radius:
                    if delta.length<1e-6:delta=Vector((self.sign,0,0))
                    self.p[i]=center+delta.normalized()*radius
                self.p[i].z=max(.055,self.p[i].z)
        return [p.copy() for p in self.p]

name='A_Spitter_AttackV7';action=new_action(name,120,1.)
arms={side:PassiveArm(side) for side in ['Left','Right']};previous={}
for frame in range(121):
    t=frame/120;scene.frame_set(frame)
    pose=mix(sample('Attack_A',time_curve(A_TIME,t)),sample('Attack_D',time_curve(D_TIME,t)),ramp(.43,.67,t))
    pose=mix(idle,pose,ramp(0,.09,t)*(1-ramp(.84,1,t)));apply(pose)
    # Convert the source leap into a supported standing lunge. Keep the source
    # torso rotations, but remove falling translation and large sideways turn.
    source_hip=point('Hips').copy();recovery=1-ramp(.43,1,t)
    advance=max(-.035,min(.225,(a_origin.y-source_hip.y)*forward_scale))*recovery
    drop=max(-.075,min(.025,(source_hip.z-a_origin.z)*.30))*recovery
    target=idle_world['Hips'].translation+Vector(((source_hip.x-a_origin.x)*.12*recovery,-advance,drop))
    move_hips(target-point('Hips'))
    lateral=(point('LeftShoulder')-point('RightShoulder')).normalized()
    forward=lateral.cross(Vector((0,0,1))).normalized()
    yaw=math.atan2(forward.x,-forward.y)
    set_rotation('Hips',Quaternion((0,0,1),-yaw*.85*ramp(0,.10,t)*(1-ramp(.85,1,t)))@wm('Hips').to_quaternion())
    stride,lift=source_step(time_curve(STEP_TIME,t));return_weight=1-ramp(.65,1,t)
    for side in ['Left','Right']:
        foot=side+'Foot';q=idle_world[foot].to_quaternion();target=idle_world[foot].translation.copy()
        if side=='Left':
            target+=Vector((.025*stride,-.215*stride,.075*lift))*return_weight
            if t>.65:target.z+=.045*math.sin(math.pi*min(1,(t-.65)/.35))**2
        else:
            heel=math.radians(11*ramp(.25,.38,t)*(1-ramp(.44,.63,t)))
            q=Quaternion((1,0,0),heel)@q
            toe=idle_world[side+'ToeBase'].translation
            local=idle_world[foot].to_quaternion().inverted()@(toe-idle_world[foot].translation)
            target=toe-q@local
        pole=idle_world[side+'Leg'].translation+Vector((0,-.13*ramp(.12,.30,t)*return_weight,0))
        limb(side+'UpLeg',side+'Leg',foot,target,pole,q)
    for side in ['Left','Right']:
        for part in ['Shoulder','Arm','ForeArm','Hand']:rig.pose.bones[side+part].matrix_basis=idle[side+part]
    update()
    for side,arm in arms.items():
        points=arm.solve(point(side+'Arm'),point('Hips'),point('neck'))
        for i,part in enumerate(['Arm','ForeArm','Hand']):
            aim(side+part,direction(side+part),points[i+1]-point(side+part))
        settle=ramp(.67,1,t)
        for part in ['Shoulder','Arm','ForeArm','Hand']:
            bone=rig.pose.bones[side+part];bone.matrix_basis=lerp_matrix(bone.matrix_basis,idle[side+part],settle)
        update()
    gaze(ramp(0,.08,t)*(1-ramp(.88,1,t)))
    # Exact idle endpoint avoids retaining an attack lean after the combat clock.
    if frame==0 or frame==120:apply(idle)
    key_pose(frame,previous)

entry=export(name,action,120,False,'ZombieAnimationPack Attack_A anticipation/lunge and Attack_D recovery; custom standing support, passive arm dynamics and forward gaze')
entry.update(release_seconds=1/3,finger_animation=False)
report['attack']=entry;report['source_time_warps']={'Attack_A':A_TIME,'Attack_D':D_TIME,'step_from_Attack_D':STEP_TIME}
report['gaze_authoring_target_metres']=list(GAZE);report['runtime_target_tracking_modified']=False
report['source_pack_assets_modified']=False
scene.frame_set(0)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'SpitterZombie_LibraryMotionV7.blend'))
(ROOT/'authoring.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
contract=json.loads((BASE/'animation_contract.json').read_text(encoding='utf-8'))
contract['Walk']=report['movement']['Walk_A'];contract['Attack']=entry
contract['MovementVariants']={'selection':'shuffled_world_class_round_per_movement_state_entry','variants':report['movement']}
(BASE/'animation_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf-8')
print('SPITTER_LIBRARY_V7_AUTHORED',flush=True)
