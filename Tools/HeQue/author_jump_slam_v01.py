"""Author planted charge, airborne fold, fast dive, heavy contact and ground VFX."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/JumpSlamV01'
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
    if role=='Charge':
        sink=curve(t,[(0,0),(.25,-.035),(.95,-.23),(1.28,-.28),(1.35,-.28),(1.45,-.12),(1.50,.02)])
        lean=curve(t,[(0,0),(.95,-5),(1.35,-6),(1.50,0)])
        lift=0.;foot_back=0.;lag=curve(t,[(0,0),(1.15,5),(1.35,5),(1.50,-8)])
        chain_swing=curve(t,[(0,0),(1.25,.04),(1.50,-.18)])
    elif role=='Air':
        sink=curve(t,[(0,.02),(.12,-.01),(.30,-.03),(.9,-.03)])
        lean=curve(t,[(0,0),(.16,-4),(.42,2),(.9,3)])
        lift=curve(t,[(0,0),(.14,.11),(.30,.14),(.9,.14)])
        foot_back=curve(t,[(0,0),(.28,.06),(.9,.06)])
        lag=curve(t,[(0,-8),(.18,-13),(.45,4),(.9,2)])
        chain_swing=curve(t,[(0,-.18),(.22,-.24),(.52,.06),(.9,.03)])
    elif role=='Dive':
        sink=curve(t,[(0,-.03),(.10,-.02),(.22,-.04),(.35,-.04)])
        lean=curve(t,[(0,3),(.08,7),(.18,9),(.35,9)])
        lift=curve(t,[(0,.14),(.10,.04),(.18,0),(.35,0)])
        foot_back=curve(t,[(0,.06),(.16,0),(.35,0)])
        lag=curve(t,[(0,2),(.08,-14),(.35,-14)])
        chain_swing=curve(t,[(0,.03),(.10,.22),(.35,.22)])
    else:
        sink=curve(t,[(0,-.04),(.10,-.32),(.26,-.24),(.45,-.28),(1.05,-.27),(1.48,-.19),(2.08,-.07),(2.35,-.035),(2.6,0)])
        lean=curve(t,[(0,9),(.10,18),(.28,11),(.5,13),(1.05,13),(1.65,8),(2.3,2),(2.6,0)])
        lift=0.;foot_back=0.
        lag=curve(t,[(0,-14),(.08,-7),(.19,22),(.39,-11),(.64,6),(1.0,-3),(1.6,1),(2.6,0)])
        chain_swing=curve(t,[(0,.22),(.18,-.35),(.38,.20),(.67,-.10),(1.02,.045),(1.6,-.015),(2.6,0)])
    top=heads['HQ_Arch']
    mass=Matrix.Translation(top+Vector((0,.025*(-sink),sink)))@Matrix.Rotation(math.radians(lean),4,'X')@Matrix.Translation(-top)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    for side,s in sides.items():
        for name in s['arch']:transform(name,mass)
        hip=mass@heads[s['upper']];foot=heads[s['foot']]+Vector((0,foot_back,lift))
        knee=solve_two(hip,foot,s);at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        sole=Matrix.Translation(foot-heads[s['foot']])
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
for role,duration in (('Charge',1.5),('Air',.9),('Dive',.35),('Recover',2.6)):
    name='A_HeQue_Jump'+role+'V01';action=bpy.data.actions.new(name);action.use_fake_user=True;rig.animation_data.action=action
    scene.frame_start=1;scene.frame_end=round(duration*FPS)+1
    for f in range(scene.frame_end):
        scene.frame_set(f+1);pose(role,f/FPS)
        for b in rig.pose.bones:
            for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f+1,group=b.name)
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'ARMATURE'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
    clips.append(dict(role=role,name=name,duration=duration))
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_JumpSlam_v01.blend'))
bpy.ops.wm.read_factory_settings(use_empty=True)
def export(name,verts,faces,uvs):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();uv=mesh.uv_layers.new(name='ShockUV')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for index in poly.loop_indices:uv.data[index].uv=uvs[mesh.loops[index].vertex_index]
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
verts=[];faces=[];uvs=[];segments=128;rows=10
for row in range(rows+1):
    q=row/rows;r=1+.02*(q-.5);height=.46*math.sin(math.pi*q)**.8
    for col in range(segments+1):
        angle=col/segments*math.tau;verts.append((r*math.cos(angle),r*math.sin(angle),height));uvs.append((col/segments,1-q))
for row in range(rows):
    for col in range(segments):
        a=row*(segments+1)+col;faces.append((a,a+1,a+segments+2,a+segments+1))
export('SM_HeQue_JumpGroundWaveV01',verts,faces,uvs)
verts=[];faces=[];uvs=[];segments=64;rows=12
for row in range(rows+1):
    r=row/rows
    for col in range(segments+1):
        angle=col/segments*math.tau;verts.append((r*math.cos(angle),r*math.sin(angle),.35*(1-r*r)));uvs.append((col/segments,1-r))
for row in range(rows):
    for col in range(segments):
        a=row*(segments+1)+col;faces.append((a,a+1,a+segments+2,a+segments+1))
export('SM_HeQue_JumpGroundImpactV01',verts,faces,uvs)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_JumpGroundFX_v01.blend'))
report=dict(clips=clips,fps=FPS,charge_seconds=1.5,recovery_seconds=2.6,jump_height_cm=140,minimum_clearance_jump_cm=70,
    inner_radius_cm=220,impact_damage=75,wave_radius_cm=700,wave_damage=45,wave_seconds=.85,cooldown=14,
    wave_height_cm=46,wave_width_cm=55,fixed_vfx_components=2,impact_trigger='actual Character.Landed',gameplay_tested=False,rendered=False)
(ROOT/'Records/authoring.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('HEQUE_JUMP_SLAM_AUTHORED '+json.dumps(report),flush=True)
