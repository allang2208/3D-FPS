"""Bake the existing Wolf actions onto the fitted Meshy rig, including jaw.

Authoring only: anatomical scale/limb constraints are part of the retarget,
not a game/animation test. No source clips or gameplay contracts are edited.
"""
import bpy, json, math
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'SourceAssets/InfectedDogMeshy20260924/CompletionV2'
SRC=json.loads((OUT/'wolf_motion_sources.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(OUT/'InfectedDog_MeshyV2.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
bpy.context.view_layer.objects.active=rig
scene=bpy.context.scene;scene.render.fps=60;scene.render.fps_base=1.
R=Matrix.Diagonal((1,-1,1))
def source_transform(d):
    q=d['q'];rot=Quaternion((q[3],q[0],q[1],q[2])).to_matrix()
    return Matrix.LocRotScale(R@Vector(d['p'])*.01,(R@rot@R).to_quaternion(),Vector((1,1,1)))
SREF={n:source_transform(t) for n,t in SRC['rest'].items()}
NAMES=[b.name for b in rig.data.bones]
PARENTS={b.name:b.parent.name if b.parent else None for b in rig.data.bones}
REST={b.name:b.matrix_local.copy() for b in rig.data.bones}
LOCAL={n:REST[PARENTS[n]].inverted()@REST[n] if PARENTS[n] else REST[n].copy() for n in NAMES}
MAP={'pelvis':'Wolf_-Pelvis','spine_01':'Wolf_-Spine','chest':'Wolf_-Spine1',
     'neck_01':'Wolf_-Neck','neck_02':'Wolf_-Neck1','neck_03':'Wolf_-Neck2','head':'Wolf_-Head'}
for i in range(6):MAP['tail_%02d'%(i+1)]='Wolf_-Tail'+(str(i) if i else '')
CHAINS=[]
for side in ['L','R']:
    for t,s in [('scapula','Clavicle'),('upperarm','UpperArm'),('forearm','Forearm'),('carpus','Hand'),('front_toes','Finger0'),('thigh','Thigh'),('calf','Calf'),('hock','HorseLink'),('hindfoot','Foot')]:
        MAP[t+'.'+side]='Wolf_-'+side+'-'+s
    CHAINS += [[x+'.'+side for x in ['upperarm','forearm','carpus']],
               [x+'.'+side for x in ['thigh','calf','hock','hindfoot']]]

def fk(local):
    world={}
    for n in NAMES:world[n]=world[PARENTS[n]]@local[n] if PARENTS[n] else local[n].copy()
    return world
def set_rotation(local,n,q):
    w=fk(local);p=PARENTS[n]
    rotation=w[p].to_quaternion().inverted()@q if p else q
    local[n]=Matrix.LocRotScale(local[n].translation,rotation,Vector((1,1,1)))
def set_position(local,n,pos):
    w=fk(local);p=PARENTS[n]
    local[n].translation=w[p].inverted()@pos if p else pos
def aim(local,n,child,direction):
    w=fk(local);current=w[child].translation-w[n].translation
    if direction.length>1e-8 and current.length>1e-8:
        set_rotation(local,n,current.rotation_difference(direction)@w[n].to_quaternion())
def solve_chain(local,chain,goal):
    world=fk(local);points=[world[n].translation.copy() for n in chain]
    lengths=[(b-a).length for a,b in zip(points,points[1:])]
    origin=points[0].copy();delta=goal-origin
    reach=min(delta.length,sum(lengths)*.999)
    goal=origin+delta.normalized()*reach
    if len(chain)==3:
        reach=max(reach,abs(lengths[0]-lengths[1])+1e-5)
        direction=(goal-origin).normalized();bend=points[1]-origin
        bend-=direction*bend.dot(direction)
        if bend.length<1e-6:bend=Vector((0,1,0))
        along=(lengths[0]**2-lengths[1]**2+reach**2)/(2*reach)
        height=math.sqrt(max(0,lengths[0]**2-along**2))
        points[1]=origin+direction*along+bend.normalized()*height;points[2]=goal
    else:
        for _ in range(32):
            points[-1]=goal.copy()
            for i in range(len(points)-2,-1,-1):
                points[i]=points[i+1]+(points[i]-points[i+1]).normalized()*lengths[i]
            points[0]=origin.copy()
            for i in range(1,len(points)):
                points[i]=points[i-1]+(points[i]-points[i-1]).normalized()*lengths[i-1]
            if (points[-1]-goal).length<1e-5:break
    for i,n in enumerate(chain[:-1]):aim(local,n,chain[i+1],points[i+1]-points[i])

# The old Ponytail1 group actually covers the lower muzzle (841 strongly
# weighted source vertices, Y=-.863..-.639 and Z=.616.. .775 m). Retain its
# timing, but calibrate its closed angle to this model's closed rest mouth.
jaw_axis=SREF['Wolf_-Head'].to_quaternion().inverted()@Vector((1,0,0))
jaw_ref=SREF['Wolf_-Head'].to_quaternion().inverted()@SREF['Wolf_-Ponytail1'].to_quaternion()
def jaw_angle(sw):
    q=(sw['Wolf_-Head'].to_quaternion().inverted()@sw['Wolf_-Ponytail1'].to_quaternion())@jaw_ref.inverted()
    a=2*math.atan2(Vector((q.x,q.y,q.z)).dot(jaw_axis),q.w)
    return (a+math.pi)%(2*math.pi)-math.pi
closed=min(jaw_angle({n:source_transform(t) for n,t in row.items()})
           for role in ['Idle','RestLoop','SleepLoop'] for row in SRC['clips'][role]['world'])
scale_z=REST['pelvis'].translation.z/SREF['Wolf_-Pelvis'].translation.z
stride_scale=1.06
folder=OUT/'Animations';folder.mkdir(exist_ok=True)
report={'source_set':'Restored WolfV1 actions plus WolfV2 BiteWeightShift',
        'fps':60,'stride_scale':stride_scale,'body_vertical_scale':scale_z,
        'jaw_closed_source_degrees':math.degrees(closed),'clips':{},
        'runtime_tested':False,'animation_previewed':False}
rig.animation_data_create()
for role,data in SRC['clips'].items():
    action=bpy.data.actions.new('A_InfectedDogMeshy_'+role);action.use_fake_user=True
    rig.animation_data.action=action
    count=data['intervals'];scene.frame_start=1;scene.frame_end=count+1
    jaw_values=[]
    for frame,row in enumerate(data['world'],1):
        sw={n:source_transform(t) for n,t in row.items()}
        def delta(n):return sw[n].to_quaternion()@SREF[n].to_quaternion().inverted()
        local={n:m.copy() for n,m in LOCAL.items()}
        dp=sw['Wolf_-Pelvis'].translation-SREF['Wolf_-Pelvis'].translation
        dp.x*=scale_z;dp.y*=stride_scale;dp.z*=scale_z
        set_position(local,'pelvis',REST['pelvis'].translation+dp)
        for n in NAMES:
            if n in MAP:set_rotation(local,n,delta(MAP[n])@REST[n].to_quaternion())
            elif n=='spine_02':
                q=delta('Wolf_-Spine').slerp(delta('Wolf_-Spine1'),.55)
                set_rotation(local,n,q@REST[n].to_quaternion())
        for chain in CHAINS:
            for i,n in enumerate(chain[:-1]):
                a,b=MAP[n],MAP[chain[i+1]]
                aim(local,n,chain[i+1],sw[b].translation-sw[a].translation)
            paw=chain[-1];sp=MAP[paw]
            motion=sw[sp].translation-SREF[sp].translation
            motion.x*=scale_z;motion.y*=stride_scale;motion.z*=scale_z
            goal=REST[paw].translation+motion
            # A source paw may be marginally below its reference floor. Keep
            # its original lift, while fitting the new paw's support height.
            if role not in ['Death','RestEnter','RestLoop','RestExit','SleepLoop']:
                goal.z=max(REST[paw].translation.z*.35,goal.z)
            solve_chain(local,chain,goal)
            set_rotation(local,paw,delta(sp)@REST[paw].to_quaternion())
            side=paw[-1]
            if paw.startswith('carpus'):
                toe='front_toes.'+side
                set_rotation(local,toe,delta(MAP[toe])@REST[toe].to_quaternion())
        opening=max(0,min(math.radians(42),jaw_angle(sw)-closed))
        jaw_values.append(math.degrees(opening))
        world=fk(local)
        head_delta=world['head'].to_quaternion()@REST['head'].to_quaternion().inverted()
        set_rotation(local,'jaw',head_delta@Quaternion(Vector((1,0,0)),opening)@REST['jaw'].to_quaternion())
        for n in NAMES:
            pb=rig.pose.bones[n];basis=LOCAL[n].inverted()@local[n]
            loc,rot,scale=basis.decompose();pb.rotation_mode='QUATERNION'
            if frame>1 and pb.rotation_quaternion.dot(rot)<0:rot.negate()
            pb.location=loc;pb.rotation_quaternion=rot;pb.scale=scale
            pb.keyframe_insert('location',frame=frame,group=n)
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=n)
            pb.keyframe_insert('scale',frame=frame,group=n)
    scene.frame_set(1)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    path=folder/(action.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},
        add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,
        bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_force_startend_keying=True,bake_anim_step=1.,bake_anim_simplify_factor=0.,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE')
    report['clips'][role]={'file':str(path),'source':data['source'],'seconds':data['seconds'],
        'frames':count+1,'jaw_open_degrees_range':[min(jaw_values),max(jaw_values)]}
    print('MESHY_ACTION_BAKED',role,count+1,report['clips'][role]['jaw_open_degrees_range'],flush=True)
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'InfectedDog_MeshyV2_Animated.blend'))
(OUT/'animation_authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('MESHY_ALL_ACTIONS_SAVED',len(report['clips']),flush=True)
