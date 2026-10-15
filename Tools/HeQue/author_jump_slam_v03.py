"""Refine whole-body airborne motion while retaining V02 charge and ground FX."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/CombatV03'
for folder in ('Authoring','Export','Audio','Records','Before'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones};ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive));desired={}
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
for path,names in (('author_side_crush.py',('ease','curve','transform','at')),('author_rig_motion.py',('solve_two',))):
    tree=ast.parse((PROJECT/'Tools/HeQue'/path).read_text('utf8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'HeQue/jump_helpers','exec'))
FPS=120
def pose(role,t):
    desired.clear()
    squash=0.;stretch=0.;roll=0.;twist=0.;arch_curl=0.;foot_pitch=0.;feet_split=0.
    if role=='Charge':
        sink=curve(t,[(0,0),(.32,-.03),(1.1,-.23),(1.62,-.32),(1.80,-.32),(1.87,-.24),(1.95,.035)])
        lean=curve(t,[(0,0),(1.2,-6),(1.62,-8),(1.80,-8),(1.95,-1)])
        lift=0.;foot_back=0.;lag=curve(t,[(0,0),(1.5,6),(1.80,6),(1.95,-10)])
        chain_swing=curve(t,[(0,0),(1.62,.055),(1.80,.055),(1.95,-.24)])
    elif role=='Air':
        sink=curve(t,[(0,.035),(.12,-.015),(.32,-.065),(.50,-.045),(.9,-.045)])
        lean=curve(t,[(0,-1),(.16,-7),(.40,2),(.56,5),(.9,5)])
        lift=curve(t,[(0,0),(.14,.17),(.35,.20),(.9,.20)])
        foot_back=curve(t,[(0,0),(.26,.07),(.9,.07)])
        lag=curve(t,[(0,-10),(.16,-16),(.36,3),(.9,3)])
        chain_swing=curve(t,[(0,-.24),(.18,-.30),(.36,.05),(.9,.05)])
        roll=curve(t,[(0,0),(.28,-3),(.50,-2),(.9,-2)])
        twist=curve(t,[(0,0),(.35,3.5),(.55,2),(.9,2)])
        arch_curl=curve(t,[(0,0),(.16,-3),(.45,4),(.9,4)])
        foot_pitch=curve(t,[(0,0),(.20,-12),(.45,-8),(.9,-8)])
        feet_split=curve(t,[(0,0),(.14,.02),(.9,.02)])
    elif role=='Dive':
        # The feet brace early, while arch/torso/heart continue their staggered
        # fall-through instead of freezing the entire creature at the first pose.
        sink=curve(t,[(0,-.045),(.025,-.08),(.075,.015),(.18,-.05),(.25,-.05)])
        lean=curve(t,[(0,5),(.02,1),(.09,19),(.18,14),(.25,14)])
        lift=curve(t,[(0,.20),(.015,.11),(.04,0),(.25,0)])
        foot_back=curve(t,[(0,.07),(.04,0),(.25,0)])
        lag=curve(t,[(0,3),(.04,-23),(.13,-20),(.20,-18),(.25,-18)])
        chain_swing=curve(t,[(0,.05),(.04,.36),(.18,.30),(.25,.30)])
        roll=curve(t,[(0,-2),(.055,3),(.11,0),(.25,0)])
        twist=curve(t,[(0,2),(.065,-3.5),(.13,0),(.25,0)])
        arch_curl=curve(t,[(0,4),(.065,10),(.13,3),(.18,0),(.25,0)])
        foot_pitch=curve(t,[(0,-8),(.025,5),(.04,0),(.25,0)])
        feet_split=curve(t,[(0,.02),(.025,.008),(.04,0),(.25,0)])
    else:
        sink=curve(t,[(0,-.05),(.067,-.41),(.23,-.14),(.44,-.30),(.70,-.285),(1.38,-.285),(1.72,-.21),(2.17,-.08),(2.45,-.025),(2.6,0)])
        lean=curve(t,[(0,14),(.075,23),(.25,7),(.46,16),(1.38,16),(1.8,10),(2.35,3),(2.6,0)])
        lift=0.;foot_back=0.
        squash=curve(t,[(0,0),(.075,1),(.17,0),(.38,.28),(.62,0),(2.6,0)])
        stretch=curve(t,[(0,0),(.17,0),(.23,1),(.36,0),(2.6,0)])
        lag=curve(t,[(0,-18),(.055,-10),(.14,27),(.31,-16),(.54,10),(.85,-4),(1.25,1.5),(1.7,0),(2.6,0)])
        chain_swing=curve(t,[(0,.30),(.14,-.44),(.32,.26),(.58,-.14),(.91,.065),(1.4,-.025),(2.6,0)])
    top=heads['HQ_Arch']
    scale=Matrix.Diagonal((1+.045*squash-.012*stretch,1+.02*squash,1-.065*squash+.025*stretch,1))
    mass=Matrix.Translation(top+Vector((0,.025*(-sink),sink)))@Matrix.Rotation(math.radians(twist),4,'Z')@Matrix.Rotation(math.radians(roll),4,'Y')@Matrix.Rotation(math.radians(lean),4,'X')@scale@Matrix.Translation(-top)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    for side,s in sides.items():
        sign=1 if side=='L' else -1
        pivot=heads[s['arch'][0]]
        side_mass=mass@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(arch_curl*(1+.15*sign)),4,'X')@Matrix.Translation(-pivot)
        for name in s['arch']:transform(name,side_mass)
        hip=side_mass@heads[s['upper']];foot=heads[s['foot']]+Vector((0,foot_back,lift+sign*feet_split))
        knee=solve_two(hip,foot,s);at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        sole=Matrix.Translation(foot)@Matrix.Rotation(math.radians(foot_pitch*(1+.1*sign)),4,'X')@Matrix.Translation(-heads[s['foot']])
        for name in (s['foot'],s['toe'],s['tip']):transform(name,sole)
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    cp=heads['HQ_CoreSwing'];core=mass@Matrix.Translation(cp)@Matrix.Rotation(math.radians(lag),4,'X')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length
        direction=(Vector((-.006,.002,-.0355)).normalized()+Vector((chain_swing*.10,chain_swing*(1+i*.015),0))).normalized()
        if role in ('Charge','Recover') and current.z+direction.z*length<.025:
            direction.z=max(-1.,min(1.,(.025-current.z)/length))
            xy=Vector((direction.x,direction.y,0)).normalized()*math.sqrt(max(0.,1-direction.z**2));direction.x=xy.x;direction.y=xy.y
        target=current+direction*length;at(name,current,target);current=target
    for b in ordered:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

scene=bpy.context.scene;scene.render.fps=FPS;clips=[]
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
for role,duration in (('Air',.9),('Dive',.25),('Recover',2.6)):
    name='A_HeQue_Jump'+role+'V03';action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    scene.frame_start=1;scene.frame_end=round(duration*FPS)+1
    for f in range(scene.frame_end):
        scene.frame_set(f+1);pose(role,f/FPS)
        for b in rig.pose.bones:
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f+1,group=b.name)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
    clips.append(dict(role=role,name=name,duration=duration))
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_JumpSlam_v03.blend'))
report=dict(clips=clips,fps=FPS,jump_height_cm=210,charge_seconds=1.95,recovery_seconds=2.6,
    dive_speed_cm_per_second=1600,cripple_seconds=5,kick_push_cm=1000,clamp_stun_seconds=2,psychic_cooldown=30,
    weakpoint_bone='HQ_CoreSwing',preserved_fx='JumpSlamV02',gameplay_tested=False,rendered=False)
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_COMBAT_V03_AUTHORED '+json.dumps(report),flush=True)
