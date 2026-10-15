"""HeQue Rift Pressure: narrowing cleft, tension, two releases and a visible bowed wave."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/RiftPressureV01'
for name in ('Authoring','Export','Audio','Records','Before'):(ROOT/name).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones};bone_order=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive));desired={}
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
helpers=ast.parse((PROJECT/'Tools/HeQue/author_rig_motion.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in helpers.body if isinstance(n,ast.FunctionDef) and n.name in
    ('smooth','clear','at','transform','solve_two')],type_ignores=[]),'HeQue/rift_helpers','exec'))
END=4.3;PULSES=(1.55,2.15)
def envelope(t,a,b,c,d):return smooth((t-a)/(b-a))*(1-smooth((t-c)/(d-c)))
def pose(t):
    clear();tension=envelope(t,0.,1.35,2.25,3.7)
    recoil=sum(envelope(t,p-.04,p+.035,p+.07,p+.32) for p in PULSES)
    brace=Vector((0,-.018*tension+.025*recoil,-.045*tension-.018*recoil))
    mass=Matrix.Translation(brace)
    transform('HQ_Arch',mass)
    def narrow(v):return Vector((v.x*(1-.22*tension),v.y,v.z))+brace
    for side,s in sides.items():
        for name in s['arch']:at(name,narrow(heads[name]),narrow(tails[name]))
        hip=narrow(heads[s['upper']]);foot=heads[s['foot']].copy()
        knee=solve_two(hip,foot,s);at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        for name in (s['foot'],s['toe'],s['tip']):transform(name,Matrix.Identity(4))
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    pivot=heads['HQ_CoreSwing'];shake=0.
    for pulse in PULSES:
        age=t-pulse
        if age>=0:shake+=math.sin(age*math.tau*7)*math.exp(-age*10)*1.5
    core=mass@Matrix.Translation(pivot+Vector((0,-.012*tension,.035*tension)))@Matrix.Rotation(math.radians(-5*recoil+shake),4,'X')@Matrix.Translation(-pivot)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length
        sway=sum(math.sin(max(0,t-p-i*.016)*15)*math.exp(-max(0,t-p-i*.016)*5)*(t>=p+i*.016) for p in PULSES)
        direction=Vector((-.17,.055+.1*sway,-1)).normalized()
        if current.z+direction.z*length<.025:direction=Vector((-.88,.38,max(-.2,min(.5,(.025-current.z)/length)))).normalized()
        target=current+direction*length;at(name,current,target);current=target
    for b in bone_order:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()
scene=bpy.context.scene;scene.render.fps=60;scene.frame_start=1;scene.frame_end=round(END*60)+1
action=bpy.data.actions.new('A_HeQue_RiftPressure');action.use_fake_user=True;rig.animation_data.action=action
for frame in range(scene.frame_end):
    scene.frame_set(frame+1);pose(frame/60)
    for b in rig.pose.bones:
        for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=frame+1,group=b.name)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/A_HeQue_RiftPressure.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_RiftPressure_v01.blend'))
# A shallow, continuous lens. Its imported normal is +X and radius is 100cm.
bpy.ops.wm.read_factory_settings(use_empty=True);verts=[];faces=[];uvs=[];rows=16;segments=96
for row in range(rows+1):
    radius=row/rows
    for col in range(segments+1):
        theta=math.tau*col/segments
        verts.append((.18*(1-radius*radius),radius*math.cos(theta),radius*math.sin(theta)))
        uvs.append((col/segments,radius))
for row in range(rows):
    for col in range(segments):
        a=row*(segments+1)+col
        faces.append((a,a+segments+2,a+segments+1) if row==0 else (a,a+1,a+segments+2,a+segments+1))
mesh=bpy.data.meshes.new('HeQuePressureLens');mesh.from_pydata(verts,[],faces);mesh.update();uv=mesh.uv_layers.new(name='PressureUV')
for poly in mesh.polygons:
    poly.use_smooth=True
    for li in poly.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
obj=bpy.data.objects.new('SM_HeQue_PressureLens',mesh);bpy.context.collection.objects.link(obj);obj.select_set(True);bpy.context.view_layer.objects.active=obj
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/SM_HeQue_PressureLens.fbx'),use_selection=True,object_types={'MESH'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_PressureLens.blend'))
(ROOT/'Records/authoring.json').write_text(json.dumps(dict(duration=END,pulses=PULSES,fps=60,range_cm=2400,speed_cm_s=1400,
    damage_per_wave=38,cooldown=7.5,visible_radius_cm=100,gameplay_tested=False),indent=2),encoding='utf8')
print('HEQUE_RIFT_PRESSURE_AUTHORED',flush=True)
