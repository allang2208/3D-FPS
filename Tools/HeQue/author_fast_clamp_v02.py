"""Double only the approved clamp's 1.50-1.70 s closing stroke."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/HeavyClampV02'
for folder in ('Authoring','Export','Records','Before','Audio'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
heads={b.name:b.head_local.copy() for b in rig.data.bones};tails={b.name:b.tail_local.copy() for b in rig.data.bones}
ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive));desired={}
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
END=4.2 # Original pose functions retain their complete original time domain.
DURATION=4.1;START=1.5;CONTACT_END=1.65;FPS=120
for filename,names in (('author_side_crush.py',('ease','curve','transform','at')),('author_heavy_clamp.py',('knee_at','pose'))):
    tree=ast.parse((PROJECT/'Tools/HeQue'/filename).read_text('utf8'))
    functions=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    exec(compile(ast.Module(body=functions,type_ignores=[]),'HeQue/approved_clamp_source','exec'))
def source_time(t):
    return t if t<=1.5 else 1.5+(t-1.5)*2 if t<1.6 else t+.1
scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=round(DURATION*FPS)+1
name='A_HeQue_HeavyClampFastV02';action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
contacts=[]
for f in range(scene.frame_end):
    t=f/FPS;scene.frame_set(f+1);pose(source_time(t))
    for b in rig.pose.bones:
        b.keyframe_insert('location',frame=f+1,group=b.name)
        b.keyframe_insert('rotation_quaternion',frame=f+1,group=b.name)
        b.keyframe_insert('scale',frame=f+1,group=b.name)
    if START-1/FPS-1e-5<=t<=CONTACT_END+1e-5:contacts.append(dict(time=t))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_HeavyClamp_fast_v02.blend'))
report=json.loads((PROJECT/'SourceAssets/HeQueBoss20261014/HeavyClampV01/Records/motion.json').read_text('utf8'))
report.update(clip=name,duration=DURATION,fps=FPS,contact_start=START,contact_end=CONTACT_END,close_seconds=.10,
    recovery_seconds=DURATION-CONTACT_END,exhausted_hold_end=2.45,frames=contacts,
    source_clip='HeavyClampV01',source_close_seconds=.20,time_map=[[0,0],[1.5,1.5],[1.6,1.7],[DURATION,END]],
    air_cannon_range_cm=4800.,runtime_tested=False)
(ROOT/'Records/motion.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(PROJECT/'Source/FPSGAME/Monsters/HeQueClampTiming.h').write_text(
    '#pragma once\n// Generated with Tools/HeQue/author_fast_clamp_v02.py. Native seconds.\nnamespace HeQueClampTiming\n{\n'
    f'    inline constexpr float ContactStart={START:.2f}f;\n    inline constexpr float ContactEnd={CONTACT_END:.2f}f;\n'
    f'    inline constexpr float End={DURATION:.2f}f;\n}}\n',encoding='utf8')
print('HEQUE_FAST_CLAMP_AUTHORED '+json.dumps(dict(duration=DURATION,close_seconds=.10,contact_frames=len(contacts),range_cm=4800)),flush=True)
