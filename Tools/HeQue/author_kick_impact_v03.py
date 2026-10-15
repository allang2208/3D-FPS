"""Retime the user-approved V02 kick: slow charge, explosive release, heavy settle."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector

PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/SideCrushV03'
for folder in ('Authoring','Export','Records','Before','Audio'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];body=bpy.data.objects['HeQueBody']
rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones}
ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive))
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides'];desired={}
END=3.2  # V02 functions retain their original source duration.
DURATION=3.6;FPS=120;START=189/FPS;CONTACT_END=202/FPS
for path,names in (('author_side_crush.py',('transform','at')),('author_forward_kick_v02.py',('track','solve','pose'))):
    tree=ast.parse((PROJECT/'Tools/HeQue'/path).read_text('utf8'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    for node in functions:
        if node.name=='pose':node.name='source_pose'
    exec(compile(ast.Module(body=functions,type_ignores=[]),'HeQue/approved_kick_source','exec'))

# The path stays V02. The source clock crawls into a readable loaded hold,
# accelerates sharply through extension, then brakes and recovers independently.
TIME_MAP=[(0,0),(.36,.32),(1.26,.90),(1.48,.90),(1.52,.97),(1.56,1.18),
    (1.62,1.45),(1.66,1.53),(1.74,1.57),(1.90,1.76),(2.60,2.22),(3.16,2.70),(DURATION,END)]

def pose(t):
    source_pose(track(t,TIME_MAP))
    mass=desired['HQ_Arch']@rest['HQ_Arch'].inverted()
    # Secondary mass follows real elapsed time so it does not freeze in the
    # loaded hold or snap through the fast clock with the leg.
    lag=math.radians(track(t,[(0,0),(.80,-5),(1.26,-4),(1.48,-2),(1.60,14),(1.78,-19),(2.04,10),(2.36,-5),(2.82,2),(DURATION,0)]))
    side=math.radians(track(t,[(0,0),(.70,5),(1.48,2),(1.73,-8),(2.12,4),(2.55,-2),(DURATION,0)]))
    cp=heads['HQ_CoreSwing'];core=mass@Matrix.Translation(cp)@Matrix.Rotation(lag,4,'X')@Matrix.Rotation(side,4,'Y')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length;delay=max(0,t-i*.014)
        swing=track(delay,[(0,0),(.95,-.06),(1.48,0),(1.64,.28),(1.84,-.40),(2.14,.22),(2.48,-.10),(2.92,.04),(DURATION,0)])
        sideways=track(delay,[(0,0),(.85,-.08),(1.48,-.02),(1.78,.16),(2.12,-.09),(2.65,.035),(DURATION,0)])
        direction=(Vector((-.006,.002,-.0355)).normalized()+Vector((sideways,swing,0))).normalized()
        if current.z+direction.z*length<.025:
            direction.z=max(-1.,min(1.,(.025-current.z)/length))
            xy=Vector((direction.x,direction.y,0)).normalized()*math.sqrt(max(0.,1-direction.z**2))
            direction.x=xy.x;direction.y=xy.y
        target=current+direction*length;at(name,current,target);current=target
    for b in ordered:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=round(DURATION*FPS)+1
action=bpy.data.actions.new('A_HeQue_ForwardKickImpactV03');action.use_fake_user=True;rig.animation_data.action=action
frames=[]
for f in range(scene.frame_end):
    t=f/FPS;scene.frame_set(f+1);pose(t)
    for b in rig.pose.bones:
        b.keyframe_insert('location',frame=f+1,group=b.name)
        b.keyframe_insert('rotation_quaternion',frame=f+1,group=b.name)
        b.keyframe_insert('scale',frame=f+1,group=b.name)
    # Include a lead-in sample for the first continuous damage segment.
    if START-1/FPS-1e-5<=t<=CONTACT_END+1e-5:frames.append(dict(time=t))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/A_HeQue_ForwardKickImpactV03.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_ForwardKick_Impact_v03.blend'))
motion=json.loads((PROJECT/'SourceAssets/HeQueBoss20261014/SideCrushV02/Records/motion.json').read_text('utf8'))
motion.update(clip='A_HeQue_ForwardKickImpactV03',duration=DURATION,fps=FPS,frames=frames,contact_start=START,contact_end=CONTACT_END,
    approved_pose_source='SideCrushV02',time_map=TIME_MAP,release_seconds=.18,aoe='continuous swept foot/lower-limb bounds',
    aoe_padding_cm=dict(lateral=45,forward=20,vertical=15),push_cm=240.,hit_radius_cm=45.,
    key_phases=dict(weight_transfer=[0,.36],slow_lift=[.36,1.26],loaded_hold=[1.26,1.48],fast_release=[1.48,1.66],
        brake_recoil=[1.66,1.90],folded_recovery=[1.90,3.16],landing_settle=[3.16,DURATION]))
(ROOT/'Records/motion.json').write_text(json.dumps(motion,indent=2),encoding='utf8')
(PROJECT/'Source/FPSGAME/Monsters/HeQueSweepTiming.h').write_text(
    '#pragma once\n// Generated by author_kick_impact_v03.py; animation, AOE and audio share native seconds.\n'
    'namespace HeQueSweepTiming\n{\n'
    f'    inline constexpr float ContactStart={START:.8f}f;\n    inline constexpr float ContactEnd={CONTACT_END:.8f}f;\n'
    f'    inline constexpr float End={DURATION:.2f}f;\n}}\n',encoding='utf8')
print('HEQUE_KICK_IMPACT_AUTHORED '+json.dumps(dict(duration=DURATION,release_seconds=.18,contact_frames=len(frames),fps=FPS)),flush=True)
