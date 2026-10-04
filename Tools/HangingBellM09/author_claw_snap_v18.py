"""Author a faster, sharper body-driven M09 claw, retaining the continuous V16 mesh and rig.

Production bake only; no game, render, regression or acceptance run. All spatial
support constraints are baked into the clip and reuse the runtime ceiling IK.
"""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Quaternion,Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003')
OUT=ROOT/'ClawSnapV18'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ArmContinuityV16/Authoring/M09_Claw_Continuous_V16.blend'))
rig=bpy.data.objects['M09_Rig_V03'];scene=bpy.context.scene
rig.data.pose_position='POSE';scene.render.fps=60;scene.render.fps_base=1.
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
local={b.name:(rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]) for b in rig.data.bones}
source=[]
for i in range(67):
    scene.frame_set(i+1)
    source.append({p.name:p.rotation_quaternion.copy() for p in rig.pose.bones})
rig.animation_data_clear();rig.animation_data_create()
for p in rig.pose.bones:
    for c in list(p.constraints):p.constraints.remove(c)
    p.rotation_mode='QUATERNION'

def smooth(x):
    x=max(0.,min(1.,x));return x*x*x*(10+x*(-15+6*x))

def shape(t,keys):
    if t<=keys[0][0]:return keys[0][1]
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]

def monotone_time(t):
    # Monotone cubic slopes keep the reach and strike connected. The brief
    # .445-.495 hold is at the rake's follow-through, not during the windup.
    knots=[(0.,0.),(.13,.085),(.24,.20),(.33,.31),(.38,.35),(.445,.62),
           (.495,.62),(.61,.78),(.79,1.01),(.98,1.1),(1.1,1.1)]
    if t<=0:return 0.
    if t>=1.1:return 1.1
    slopes=[(b[1]-a[1])/(b[0]-a[0]) for a,b in zip(knots,knots[1:])]
    tangents=[0.]
    for left,right in zip(slopes,slopes[1:]):
        tangents.append(0. if left*right<=0 else 2*left*right/(left+right))
    tangents.append(0.)
    for k,((a,x),(b,y)) in enumerate(zip(knots,knots[1:])):
        if t>b:continue
        u=(t-a)/(b-a)
        return (2*u**3-3*u*u+1)*x+(u**3-2*u*u+u)*(b-a)*tangents[k]+(-2*u**3+3*u*u)*y+(u**3-u*u)*(b-a)*tangents[k+1]

def twist(t):
    return shape(t,[(0.,0.),(.235,-18.),(.325,-16.),(.435,25.5),(.495,25.5),(.61,10.),(.76,-5.),(.91,1.5),(1.04,0.),(1.1,0.)])

def pitch(t):
    return shape(t,[(0.,0.),(.24,5.5),(.325,4.8),(.435,-11.),(.495,-11.),(.62,-2.5),(.79,2.),(1.04,0.),(1.1,0.)])

def lean(t):
    return shape(t,[(0.,0.),(.24,-3.5),(.435,4.5),(.495,4.5),(.64,.7),(.80,-1.),(1.04,0.),(1.1,0.)])

def rot(name,axis,degrees):
    axis=rest[name].to_quaternion().inverted()@Vector(axis)
    rig.pose.bones[name].rotation_quaternion=Quaternion(axis.normalized(),math.radians(degrees))@rig.pose.bones[name].rotation_quaternion

def globals_now():
    result={}
    for b in rig.data.bones:
        result[b.name]=(result[b.parent.name] if b.parent else Matrix.Identity(4))@local[b.name]@rig.pose.bones[b.name].rotation_quaternion.to_matrix().to_4x4()
    return result

def frame(direction,normal):
    y=direction.normalized();z=(normal-y*normal.dot(y)).normalized()
    return Matrix((y.cross(z).normalized(),y,z)).transposed().to_quaternion()

def global_rotation(name,q,matrices):
    parent=rig.data.bones[name].parent
    parent_q=matrices[parent.name].to_quaternion() if parent else Quaternion()
    rig.pose.bones[name].rotation_quaternion=(local[name].to_quaternion().inverted()@parent_q.inverted()@q).normalized()
    matrices[name]=(matrices[parent.name] if parent else Matrix.Identity(4))@local[name]@rig.pose.bones[name].rotation_quaternion.to_matrix().to_4x4()

support={}
for side in ('L','R'):
    names=[f'big_{n}_{side}' for n in ('upperarm','forearm','hand')]
    a,b,c=[rest[n].translation for n in names]
    upper,lower=b-a,c-b;direction=(c-a).normalized()
    support[side]=(names,a,b,c,upper,lower,upper.cross(lower).normalized(),
                   (upper-direction*upper.dot(direction)).normalized())

action=bpy.data.actions.new('A_M09_CrownClaw_Snap_V18');action.use_fake_user=True
rig.animation_data.action=action;scene.frame_start=1;scene.frame_end=67
bone_names=[b.name for b in rig.data.bones if b.use_deform]
for i in range(67):
    t=i/60.;at=monotone_time(t)*60;lo=min(65,int(at));alpha=at-lo
    for p in rig.pose.bones:
        p.location=(0,0,0);p.scale=(1,1,1)
        p.rotation_quaternion=source[lo][p.name].slerp(source[lo+1][p.name],alpha)
    # The twist is distributed along the torso; the fixed top anchor and baked
    # support-chain solution retain contact while the lower body drives the rake.
    for name,weight in [('spine_01',.18),('spine_02',.43),('spine_03',.30),('spine_04',.09)]:
        rot(name,(0,0,1),twist(t)*weight)
        rot(name,(1,0,0),pitch(t)*weight)
        rot(name,(0,1,0),lean(t)*weight)
    rot('suspension',(1,0,0),pitch(t)*.13)
    # Add a restrained opening bias before the diagonal inward rake.
    flare=shape(t,[(0.,0.),(.24,1.),(.33,.8),(.44,0.),(1.1,0.)])
    for side,sign in [('L',1),('R',-1)]:rot('small_upperarm_'+side,(0,0,1),-sign*5.5*flare)
    # Heavy crown and membrane tips follow after the torso rather than turning
    # as one rigid piece. Recover to the exact same guard at the end.
    tail_weight=1-smooth((t-.86)/.24)
    rot('crown_neck',(0,0,1),(twist(t-.045)-twist(t))*.30*tail_weight)
    rot('eye_crown',(0,0,1),(twist(t-.065)-twist(t))*.18*tail_weight)
    rot('eye_crown',(1,0,0),(pitch(t-.055)-pitch(t))*.30*tail_weight)
    for side,sign in [('L',1),('R',-1)]:
        for layer in range(1,4):
            lag=.02+layer*.015
            opening=shape(t-lag,[(0.,0.),(.25,2.5),(.445,8.),(.58,4.),(.76,-1.5),(1.01,0.)])*tail_weight
            drag=(twist(t-lag)-twist(t))*.12*tail_weight
            for joint,weight in enumerate((.40,.29,.20,.11),1):
                name=f'membrane_{side}{layer}_{joint:02d}'
                rot(name,(0,1,0),sign*opening*weight)
                rot(name,(0,0,1),drag*weight)
    matrices=globals_now()
    for side in ('L','R'):
        names,a0,b0,target,u0,f0,n0,pole0=support[side]
        shoulder=matrices[names[0]].translation;r=(target-shoulder).normalized()
        distance=(target-shoulder).length;length_u=u0.length;length_f=f0.length
        distance=min(length_u+length_f-.001,max(abs(length_u-length_f)+.001,distance))
        pole=(pole0-r*pole0.dot(r)).normalized()
        along=(length_u**2-length_f**2+distance**2)/(2*distance)
        elbow=shoulder+r*along+pole*math.sqrt(max(0.,length_u**2-along**2))
        u,f=elbow-shoulder,target-elbow;n=u.cross(f).normalized()
        global_rotation(names[0],frame(u,n)@frame(u0,n0).inverted()@rest[names[0]].to_quaternion(),matrices)
        global_rotation(names[1],frame(f,n)@frame(f0,n0).inverted()@rest[names[1]].to_quaternion(),matrices)
        global_rotation(names[2],rest[names[2]].to_quaternion(),matrices)
    for name in bone_names:
        for channel in ('location','rotation_quaternion','scale'):
            rig.pose.bones[name].keyframe_insert(channel,frame=i+1,group=name)
for slot in action.slots:
    for layer in action.layers:
        for strip in layer.strips:
            bag=strip.channelbag(slot)
            if bag:
                for fc in bag.fcurves:
                    for key in fc.keyframe_points:key.interpolation='LINEAR'
scene.frame_set(1)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
fbx=OUT/'Exports/A_M09_CrownClaw_Snap_V18.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE'},
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,
    add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring/M09_Claw_Snap_V18.blend'),compress=True)
(OUT/'Records/motion_manifest.json').write_text(json.dumps({
    'version':'ClawSnapV18','source_model':'ArmContinuityV16','duration':1.1,'fps':60,'frames':67,
    'contact':[.35,.55],'rapid_rake':[.38,.445],'followthrough_hold':[.445,.495],
    'prior_rapid_rake_seconds':.095,'rapid_rake_speed_multiplier':.095/.065,'arm_guard_recovered_at':.98,
    'torso_twist_deg':[-18,25.5],'torso_pitch_deg':[5.5,-11],
    'body_drive':'Quicker anticipation, stronger torso torque, 65ms inward/downward rake, 50ms authored follow-through hold, brisk damped recovery',
    'secondary_motion':'Crown and six membranes with delayed response',
    'ceiling_support':'Original hand world positions/orientations, baked two-bone support solution',
    'mesh_bind_weights_physics_unchanged':True,'damage_AI_timing_unchanged':True,
    'game_tested':False,'rendered':False,'acceptance':'Pending user test','file':str(fbx)},indent=2),encoding='utf8')
print('M09_CLAW_SNAP_V18_AUTHORED',flush=True)
