"""Author heavier distance-matched HeQue walking/pivot cycles on the delivered rig."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/WeightyMoveV02'
for name in ('Authoring','Export','Records','Before'):(ROOT/name).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
heads={b.name:b.head_local.copy() for b in rig.data.bones};tails={b.name:b.tail_local.copy() for b in rig.data.bones}
bone_order=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive));desired={}
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
helpers=ast.parse((PROJECT/'Tools/HeQue/author_rig_motion.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('smooth','clear','at','transform','solve_two')],type_ignores=[]),'HeQue/heavy_helpers','exec'))

def curve(t,keys):
    for (a,x),(b,y) in zip(keys[:-1],keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]

STANCE=.72;SPAN=.54;DURATION=2.4;TURN_DEGREES=82.
def pose(role,u):
    clear();phase=math.tau*u;impact=(u*2)%1.
    bob=curve(impact,[(0,-.042),(.14,-.078),(.43,-.045),(.72,-.032),(1,-.042)])
    shift=Vector((-.052*math.sin(phase),-.04,bob))
    lean=4.+1.6*math.sin(phase*2-.55);roll=-2.6*math.sin(phase-.18)
    yaw=2.6*math.sin(phase-.3)
    pivot=heads['HQ_Arch']
    mass=Matrix.Translation(pivot+shift)@Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Rotation(math.radians(lean),4,'X')@Matrix.Rotation(math.radians(roll),4,'Y')@Matrix.Translation(-pivot)
    transform('HQ_Arch',mass)
    for side,s in sides.items():
        for name in s['arch']:transform(name,mass)
        hip=mass@heads[s['upper']];foot=heads[s['foot']].copy()
        q=(u+(0 if side=='R' else .5))%1.
        if q<STANCE:
            # Linear back-travel cancels real forward displacement in stance.
            travel=-SPAN/2+SPAN*q/STANCE;lift=0.
            pitch=curve(q/STANCE,[(0,-3),(.12,0),(.78,0),(1,5)])
        else:
            swing=(q-STANCE)/(1-STANCE)
            travel=curve(swing,[(0,SPAN/2),(.20,.18),(.70,-.22),(1,-SPAN/2)])
            lift=curve(swing,[(0,0),(.30,.085),(.65,.095),(.80,.083),(1,0)])
            pitch=curve(swing,[(0,5),(.38,10),(.76,3),(1,-3)])
        foot_yaw=0.
        if role=='Move':foot.y+=travel
        else:
            # Counter-rotate a planted foot around the real turn centre; its
            # angular travel is exactly the runtime turn-stride denominator.
            half=math.radians(TURN_DEGREES)*STANCE*.5
            if q<STANCE:foot_yaw=half-2*half*q/STANCE
            else:foot_yaw=-half+2*half*smooth((q-STANCE)/(1-STANCE))
            if role=='TurnRight':foot_yaw=-foot_yaw
            foot=Matrix.Rotation(foot_yaw,3,'Z')@foot
        foot.z+=lift
        knee=solve_two(hip,foot,s);at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        sole=Matrix.Translation(foot)@Matrix.Rotation(foot_yaw,4,'Z')@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Translation(-heads[s['foot']])
        for name in (s['foot'],s['toe'],s['tip']):transform(name,sole)
        lower=desired[s['lower']]@rest[s['lower']].inverted();transform('HQ_Cuff_'+side,lower)
        upper=desired[s['upper']]@rest[s['upper']].inverted();transform('HQ_Flank_'+side,upper)
    cp=heads['HQ_CoreSwing']
    core=mass@Matrix.Translation(cp)@Matrix.Rotation(math.radians(5.5*math.sin(phase-.8)),4,'X')@Matrix.Rotation(math.radians(3.0*math.sin(phase-1.1)),4,'Y')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length
        wave=.20*math.sin(phase-.65-i*.13)+.065*math.sin(phase*2-.6-i*.17)
        direction=Vector((-.13+.07*math.sin(phase-i*.15),.05+wave,-1.)).normalized()
        if current.z+direction.z*length<.025:
            direction=Vector((-.88,.38,max(-.2,min(.5,(.025-current.z)/length)))).normalized()
        target=current+direction*length;at(name,current,target);current=target
    for b in bone_order:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

scene=bpy.context.scene;scene.render.fps=60;scene.frame_start=1;scene.frame_end=round(DURATION*60)+1
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
clips=[]
for role in ('Move','TurnLeft','TurnRight'):
    name='A_HeQue_'+role+'_HeavyV02';action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    for frame in range(scene.frame_end):
        scene.frame_set(frame+1);pose(role,frame/(scene.frame_end-1))
        for b in rig.pose.bones:
            b.keyframe_insert('location',frame=frame+1,group=b.name)
            b.keyframe_insert('rotation_quaternion',frame=frame+1,group=b.name)
            b.keyframe_insert('scale',frame=frame+1,group=b.name)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
    clips.append(dict(role=role,name=name,duration=DURATION))
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_weighty_move_v02.blend'))
report=dict(clips=clips,stance_fraction=STANCE,stance_travel_m=SPAN,stride_cm=SPAN/STANCE*450/1.7,
    walk_speed=100.,return_speed=80.,turn_speed=42.,turn_stride_degrees=TURN_DEGREES,acceleration=140.,braking=180.,
    runtime_steps_per_second_at_full_speed=2*100/(SPAN/STANCE*450/1.7),gameplay_tested=False)
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_WEIGHTY_MOVEMENT_AUTHORED '+json.dumps(report),flush=True)
