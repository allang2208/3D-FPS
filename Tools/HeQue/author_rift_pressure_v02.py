"""Heavy two-shot pressure action and bounded three-dimensional air VFX meshes."""
import ast,bpy,json,math
from pathlib import Path
from mathutils import Vector,Matrix
PROJECT=Path('D:/FPS3D/FPSGAME');BASE=PROJECT/'SourceAssets/HeQueBoss20261014/RigV01'
ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/RiftPressureV02'
for folder in ('Authoring','Export','Audio','Records','Before'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(BASE/'Authoring/HeQue_refined_rig_motion_v01.blend'))
rig=bpy.data.objects['HeQueRig'];rig.animation_data_clear();rig.animation_data_create()
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};heads={b.name:b.head_local.copy() for b in rig.data.bones}
tails={b.name:b.tail_local.copy() for b in rig.data.bones};ordered=sorted(rig.data.bones,key=lambda b:len(b.parent_recursive));desired={}
sides=json.loads((BASE/'Records/authoring.json').read_text('utf8'))['sides']
for path,names in (('author_side_crush.py',('ease','curve','transform','at')),('author_rig_motion.py',('solve_two',))):
    tree=ast.parse((PROJECT/'Tools/HeQue'/path).read_text('utf8'))
    exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'HeQue/rift_v02_helpers','exec'))
END=4.3;FPS=120;PULSES=(1.55,2.15)

def kickback(t,p):return curve(t,[(0,0),(p,0),(p+.065,1),(p+.10,.91),(p+.30,0),(END,0)])
def pose(t):
    desired.clear()
    charge=curve(t,[(0,0),(.35,.2),(1.25,1),(1.55,1),(1.64,.42),(1.96,.98),(2.15,1.02),(2.24,.3),(2.65,.16),(3.7,0),(END,0)])
    recoil=kickback(t,PULSES[0])+1.12*kickback(t,PULSES[1])
    settle=curve(t,[(0,0),(2.32,0),(2.65,1),(3.55,.25),(END,0)])
    top=heads['HQ_Arch'];brace=Vector((-.012*charge,.025*charge+.102*recoil,-.09*charge-.024*recoil-.045*settle))
    mass=Matrix.Translation(top+brace)@Matrix.Rotation(math.radians(-7*recoil-1.5*charge),4,'X')@Matrix.Translation(-top)
    transform('HQ_Root',Matrix.Identity(4));transform('HQ_Arch',mass)
    def narrow(v):return mass@Vector((v.x*(1-.25*charge),v.y,v.z))
    for side,s in sides.items():
        for name in s['arch']:at(name,narrow(heads[name]),narrow(tails[name]))
        hip=narrow(heads[s['upper']]);foot=heads[s['foot']].copy()
        knee=solve_two(hip,foot,s);at(s['upper'],hip,knee);at(s['lower'],knee,foot)
        for name in (s['foot'],s['toe'],s['tip']):transform(name,Matrix.Identity(4))
        transform('HQ_Cuff_'+side,desired[s['lower']]@rest[s['lower']].inverted())
        transform('HQ_Flank_'+side,desired[s['upper']]@rest[s['upper']].inverted())
    core_lag=0.
    for p,gain in zip(PULSES,(1,1.12)):
        age=t-p
        if age>=0:core_lag+=gain*math.sin(age*math.tau*3.2)*math.exp(-age*5.3)*12
    cp=heads['HQ_CoreSwing']
    core=mass@Matrix.Translation(cp+Vector((0,-.022*charge,.055*charge)))@Matrix.Rotation(math.radians(core_lag),4,'X')@Matrix.Translation(-cp)
    for name in ('HQ_CoreSwing','Bone_000','Bone_001','Bone_003','Bone_002'):transform(name,core)
    cuff=desired['HQ_Cuff_R']@rest['HQ_Cuff_R'].inverted();current=cuff@heads['HQ_Chain_00']
    for i in range(15):
        name=f'HQ_Chain_{i:02d}';length=(tails[name]-heads[name]).length;sway=0.
        for p,gain in zip(PULSES,(1,1.12)):
            age=t-p-i*.012
            if age>=0:sway+=gain*math.sin(age*15)*math.exp(-age*4.6)*.42
        direction=(Vector((-.006,.002,-.0355)).normalized()+Vector((.08*sway,sway,0))).normalized()
        if current.z+direction.z*length<.025:
            direction.z=max(-1.,min(1.,(.025-current.z)/length))
            xy=Vector((direction.x,direction.y,0)).normalized()*math.sqrt(max(0.,1-direction.z**2))
            direction.x=xy.x;direction.y=xy.y
        target=current+direction*length;at(name,current,target);current=target
    for b in ordered:
        parent=desired[b.parent.name]@rest[b.parent.name].inverted()@rest[b.name] if b.parent else rest[b.name]
        if b.name not in desired:desired[b.name]=parent
        rig.pose.bones[b.name].matrix_basis=parent.inverted()@desired[b.name]
    bpy.context.view_layer.update()

scene=bpy.context.scene;scene.render.fps=FPS;scene.frame_start=1;scene.frame_end=round(END*FPS)+1
action=bpy.data.actions.new('A_HeQue_RiftPressureV02');action.use_fake_user=True;rig.animation_data.action=action
for f in range(scene.frame_end):
    scene.frame_set(f+1);pose(f/FPS)
    for b in rig.pose.bones:
        for channel in ('location','rotation_quaternion','scale'):b.keyframe_insert(channel,frame=f+1,group=b.name)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export/A_HeQue_RiftPressureV02.fbx'),use_selection=True,object_types={'ARMATURE'},
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_ALL',add_leaf_bones=False,
    bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
scene.frame_set(1);bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_RiftPressure_v02.blend'))

bpy.ops.wm.read_factory_settings(use_empty=True)
def export(name,verts,faces,uvs):
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();uv=mesh.uv_layers.new(name='PressureUV')
    for poly in mesh.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:uv.data[li].uv=uvs[mesh.loops[li].vertex_index]
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.export_scene.fbx(filepath=str(ROOT/'Export'/(name+'.fbx')),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,bake_anim=False,mesh_smooth_type='FACE')

def dome(name,depth,back=False):
    verts=[];faces=[];uvs=[];rows=14;segments=64
    for sign in ((1,-1) if back else (1,)):
        start=len(verts)
        for row in range(rows+1):
            r=row/rows
            for col in range(segments+1):
                theta=math.tau*col/segments
                edge=r*(1+.012*math.sin(theta*7)*math.sin(math.pi*r))
                x=sign*depth*math.sqrt(max(0,1-r*r))
                verts.append((x,edge*math.cos(theta),edge*math.sin(theta)))
                # FBX/UE flips V. Supply 1-r so imported UV.y is radial r.
                uvs.append((col/segments,1-r))
        for row in range(rows):
            for col in range(segments):
                a=start+row*(segments+1)+col
                face=(a,a+segments+2,a+segments+1) if row==0 else (a,a+1,a+segments+2,a+segments+1)
                faces.append(tuple(reversed(face)) if sign>0 else face)
    export(name,verts,faces,uvs)
dome('SM_HeQue_PressureShellV02',.28,True)
dome('SM_HeQue_TensionMembraneV02',.035)
dome('SM_HeQue_PressureImpactV02',.12)
verts=[];faces=[];uvs=[];rows=10;segments=48
for layer in range(2):
    start=len(verts)
    for row in range(rows+1):
        u=row/rows
        for col in range(segments+1):
            theta=math.tau*col/segments
            radius=(.22+.60*math.sin(math.pi*u)**.7)*(1-layer*.22)
            radius*=1+.08*math.sin(theta*5+u*9+layer*2)
            verts.append((u,radius*math.cos(theta),radius*math.sin(theta)))
            uvs.append((u,1-col/segments))
    for row in range(rows):
        for col in range(segments):
            a=start+row*(segments+1)+col;faces.append((a,a+1,a+segments+2,a+segments+1))
export('SM_HeQue_PressureMistV02',verts,faces,uvs)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/HeQue_PressureMeshes_v02.blend'))
(ROOT/'Records/authoring.json').write_text(json.dumps(dict(duration=END,pulses=PULSES,fps=FPS,
    shell_diameter_cm=200,shell_depth_cm=56,charge_sink_cm=23.8,recoil_cm=[27,30.2],
    fixed_mesh_components=12,source_uv_v='1-r or 1-azimuth, converted by legacy FBX to radius/azimuth',
    gameplay_tested=False,visual_tested=False),indent=2),encoding='utf8')
print('HEQUE_RIFT_V02_AUTHORED',flush=True)
