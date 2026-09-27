"""Author the hand-specific fist charge; bake contact fitting offline, never render."""
from pathlib import Path
import json,math,shutil
import bpy
from mathutils import Matrix,Quaternion,Vector

ROOT=Path(__file__).resolve().parent;OUT=ROOT/'Charge';OUT.mkdir(exist_ok=True)
backup=(ROOT.parents[1]/'trash/monster-hands-20260927/SourceAssets/FleshHand20260926/Charge/BeforeVisualPolish20260927');backup.mkdir(parents=True,exist_ok=True)
for path in [OUT/'FleshHand_Charge.blend',OUT/'authoring.json']+list(OUT.glob('A_FleshHand_Charge*.fbx')):
    if path.exists() and not (backup/path.name).exists():shutil.copy2(path,backup/path.name)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'LocalRig/FleshHand_Green_WithLODs.blend'))
scene=bpy.context.scene;scene.render.fps=60
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=max((o for o in scene.objects if o.type=='MESH'),key=lambda o:len(o.data.vertices))
for o in scene.objects:o.hide_set(False)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
inverse={name:m.inverted() for name,m in rest.items()}
local={b.name:rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name] for b in rig.data.bones}
palm_normal=Vector((0,1,0));identity=Quaternion()
def local_turn(name,axis,degrees):
    return Quaternion((rest[name].to_3x3().inverted()@Vector(axis)).normalized(),math.radians(degrees))
def curl(name,degrees):
    # Actual source +Y palm and this phalanx's rest direction define flexion.
    bone=rig.data.bones[name];axis=(bone.tail_local-bone.head_local).normalized().cross(palm_normal).normalized()
    return local_turn(name,axis,degrees)
def fk(basis):
    posed={}
    for bone in rig.data.bones:
        parent=posed[bone.parent.name] if bone.parent else Matrix.Identity(4)
        posed[bone.name]=parent@local[bone.name]@basis.get(bone.name,identity).to_matrix().to_4x4()
    return posed

# Preserve the accepted bind, weights, bone lengths and unit scale. Each row is
# MCP/PIP/DIP joint increment, not cumulative angle or another rig's Euler pose.
digits=('index','middle','ring','little')
angles={'index':[80.,96.,44.],'middle':[84.,100.,48.],'ring':[87.,102.,51.],'little':[90.,104.,54.]}
adduction={'index':5.,'middle':0.,'ring':-3.,'little':-7.}
cupping={'index':0.,'middle':0.,'ring':3.,'little':6.}
limits=((66.,98.),(78.,112.),(30.,62.))
def finger_basis(rows):
    basis={}
    for digit in digits:
        basis[digit+'_metacarpal']=curl(digit+'_metacarpal',cupping[digit])
        for n,angle in enumerate(rows[digit],1):
            name=digit+'_%02d'%n;basis[name]=curl(name,angle)
            if n==1:basis[name]=local_turn(name,palm_normal,adduction[digit])@basis[name]
    return basis

# Fit real weighted distal pad vertices to the palm surface. The regularizer and
# joint bounds preserve grouped fist shape instead of twisting a tip into contact.
group_names={g.index:g.name for g in mesh.vertex_groups}
vertices=list(mesh.data.vertices)
pad_samples={};goals={}
for digit in digits:
    bone=rig.data.bones[digit+'_03'];end=bone.tail_local
    candidates=[v for v in vertices if any(group_names[g.group]==bone.name and g.weight>.35 for g in v.groups)
                and v.normal.dot(palm_normal)>.25]
    chosen=sorted(candidates,key=lambda v:(v.co-end).length)[:5]
    if not chosen:raise RuntimeError('Missing palmar fingertip surface: '+digit)
    pad_samples[digit]=[(v.co.copy(),[(group_names[g.group],g.weight) for g in v.groups if g.weight>0]) for v in chosen]
    x=rig.data.bones[digit+'_01'].head_local.x
    z={'index':.385,'middle':.365,'ring':.355,'little':.335}[digit]
    candidates=[v for v in vertices if abs(v.co.x-x)<.05 and abs(v.co.z-z)<.04 and v.normal.y>.55]
    if not candidates:raise RuntimeError('Missing palm contact surface: '+digit)
    palm=min(candidates,key=lambda v:(v.co.x-x)**2+(v.co.z-z)**2)
    goals[digit]=palm.co+Vector((0,.012,0))
def pad(digit,posed):
    points=[]
    for co,weights in pad_samples[digit]:
        points.append(sum(((posed[name]@inverse[name]@co)*weight for name,weight in weights),Vector())/sum(w for _,w in weights))
    return sum(points,Vector())/len(points)
preferred={d:row[:] for d,row in angles.items()}
for digit in digits:
    def cost():
        point=pad(digit,fk(finger_basis(angles)));delta=point-goals[digit]
        # Reaching the palm is balanced with reasonable PIP/DIP articulation.
        return delta.length_squared+sum((angles[digit][i]-preferred[digit][i])**2 for i in range(3))*.00000035
    for step in (6.,3.,1.):
        for _ in range(4):
            for joint,(lo,hi) in enumerate(limits):
                original=angles[digit][joint];best=original;best_cost=cost()
                for candidate in (max(lo,original-step),min(hi,original+step)):
                    angles[digit][joint]=candidate;value=cost()
                    if value<best_cost:best=candidate;best_cost=value
                angles[digit][joint]=best
closed=finger_basis(angles)

# Thumb opposition comes after the four fingers have folded: aim the actual
# three thumb segments across the outside of the index/middle fingers. This
# semantic construction keeps the thumb outside the fist, not trapped inside it.
thumb_directions=((.02,.15,.07),(.07,.08,.055),(.09,0,.025))
for n,direction in enumerate(thumb_directions,1):
    name='thumb_%02d'%n;posed=fk(closed);current=posed[name].to_quaternion()
    desired=Vector(direction).normalized()
    delta=(current@Vector((0,1,0))).rotation_difference(desired)
    closed[name]=current.inverted()@delta@current

def smooth(a,b,t):
    t=max(0.,min(1.,(t-a)/(b-a)));return t*t*(3-2*t)
def reset():
    for p in rig.pose.bones:p.location=(0,0,0);p.scale=(1,1,1);p.rotation_mode='QUATERNION';p.rotation_quaternion=identity
def grip(t,opening=False):
    # Small stagger between fingers, then the thumb closes over them. Opening
    # reverses that order to free the thumb before the fingers unfold.
    for i,digit in enumerate(digits):
        start=.11+i*.025;end=.68+i*.025
        amount=smooth(start,end,t) if not opening else 1-smooth(.20+i*.018,.88+i*.018,t)
        for suffix in ('_metacarpal','_01','_02','_03'):
            name=digit+suffix;rig.pose.bones[name].rotation_quaternion=identity.slerp(closed[name],amount)
    amount=smooth(.56,.94,t) if not opening else 1-smooth(.06,.42,t)
    for n in range(1,4):
        name='thumb_%02d'%n;rig.pose.bones[name].rotation_quaternion=identity.slerp(closed[name],amount)
def support():
    bpy.context.view_layer.update()
    evaluated=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get())
    # Root rest Y points up; pose-location channels are bone-local, not world XYZ.
    dz=-min((mesh.matrix_world@v.co).z for v in evaluated.data.vertices)
    rig.pose.bones['root'].location+=rest['root'].to_3x3().inverted()@Vector((0,0,dz))
def export(path):
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_bones=True,bake_anim_use_nla_strips=False,bake_anim_use_all_actions=False,
        bake_anim_step=1,bake_anim_simplify_factor=0,path_mode='AUTO')
clips={}
for role,duration in (('ChargeWindup',1.2),('ChargeRush',.6),('ChargeRecover',.7)):
    reset();action=bpy.data.actions.new('A_FleshHand_'+role);action.use_fake_user=True
    rig.animation_data_create();rig.animation_data.action=action
    frames=round(duration*60);scene.frame_start=0;scene.frame_end=frames
    for frame in range(frames+1):
        scene.frame_set(frame);reset();t=frame/frames
        if role=='ChargeWindup':
            grip(t);lean=-14*smooth(0,.65,t)+26*smooth(.80,1,t)
            lean+=.65*math.sin(2*math.pi*11*frame/60)*smooth(.62,.83,t)*(1-smooth(.90,1,t))
        elif role=='ChargeRush':
            grip(1);lean=12+.8*math.sin(2*math.pi*t)
        else:
            grip(t,True);lean=12*(1-smooth(0,.42,t))-7*math.sin(math.pi*smooth(.05,1,t))
        rig.pose.bones['wrist'].rotation_quaternion=local_turn('wrist',(-1,0,0),lean)
        support()
        for p in rig.pose.bones:
            p.keyframe_insert('location',frame=frame,group=p.name)
            p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name)
            p.keyframe_insert('scale',frame=frame,group=p.name)
    path=OUT/('A_FleshHand_'+role+'.fbx');export(path)
    clips[role]={'file':str(path),'duration_seconds':duration,'frames':frames,'loop':role=='ChargeRush'}
reset();rig.animation_data.action=None
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FleshHand_Charge.blend'))
receipt={'revision':'FistChargeVisual20260927V2','fps':60,'clips':clips,'palm_axis':[0,1,0],
    'method':'Per-finger anatomical flexion and weighted pad-to-palm fitting; external thumb opposition; unchanged bind and bone lengths',
    'finger_joint_degrees':angles,'finger_adduction_degrees':adduction,'metacarpal_cup_degrees':cupping,
    'palm_contact_goals':{d:list(v) for d,v in goals.items()},'thumb_segment_directions':thumb_directions,
    'skill_sources':['skills/ue5-fps-arms-animation/references/pose-contact.md','skills/ue5-fps-arms-animation/references/vertical-grip-family.md'],
    'runtime_motion':'CharacterMovement root-motion source; animation is in-place','rendered':False,'tested':False}
(OUT/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('FLESHHAND_CHARGE_AUTHORED '+str(OUT),flush=True)
