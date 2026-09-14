"""Author body-fit animation on the original Meshy skin, from native UE retargets."""
import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion

ROOT=Path(__file__).parent
OUT=ROOT/'final';OUT.mkdir(exist_ok=True)
FPS=120
specs={'Idle':(160,192,0),'Walk':(160,200,0),'Attack':(215,250,0),'Death':(260,260,48)}
source_meta=json.loads((ROOT/'authoring_inputs.json').read_text())

def activate(rig,action):
    rig.animation_data_create();rig.animation_data.action=action
    if action and action.slots:rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks:track.mute=True

# Import the native clips as production inputs. Cache matrices, then discard only
# their temporary Blender scene objects; the FBX originals stay on disk.
cache={}
for role,(source_intervals,_,_) in specs.items():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(ROOT/f'native_retarget/A_FatZombie_Raw_{role}.fbx'))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    action=rig.animation_data.action
    rest={b.name:rig.matrix_world@b.matrix_local for b in rig.data.bones}
    samples=[]
    start=action.frame_range[0]
    # UE's FBX writer appends a duplicate terminal key. Use the source duration.
    for i in range(source_intervals+1):
        bpy.context.scene.frame_set(round(start+i))
        samples.append({b.name:rig.matrix_world@b.matrix for b in rig.pose.bones})
    cache[role]=(rest,samples)

bpy.ops.wm.open_mainfile(filepath=str(ROOT/'FatZombie_Meshy_Source.blend'))
scene=bpy.context.scene;scene.render.fps=FPS
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE')
meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' and m.object==rig for m in o.modifiers)]
for obj in list(bpy.data.objects):
    if obj not in [rig]+meshes:bpy.data.objects.remove(obj,do_unlink=True)
activate(rig,None)
for a in list(bpy.data.actions):bpy.data.actions.remove(a)
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
world_rest={n:rig.matrix_world@m for n,m in rest.items()}
inv_world=rig.matrix_world.inverted()
ordered=list(rig.pose.bones)
for b in ordered:b.rotation_mode='QUATERNION'

# Reconnect and pack the user's four PBR maps in the editable source.
mat=bpy.data.materials.new('M_FatZombie_Meshy');mat.use_nodes=True
bsdf=mat.node_tree.nodes.get('Principled BSDF')
maps=[('Base Color','_texture_0.png'),('Normal','_texture_0_normal.png'),('Roughness','_texture_0_roughness.png'),('Metallic','_texture_0_metallic.png')]
for index,(socket,suffix) in enumerate(maps):
    im=bpy.data.images.load(str(next((ROOT/'sources/meshy').glob('*'+suffix))),check_existing=True)
    im.colorspace_settings.name='sRGB' if socket=='Base Color' else 'Non-Color';im.pack()
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=im;tex.location=(-600,300-index*260)
    output=tex.outputs['Color']
    if socket=='Normal':
        normal=mat.node_tree.nodes.new('ShaderNodeNormalMap');normal.location=(-280,0)
        mat.node_tree.links.new(output,normal.inputs['Color']);output=normal.outputs['Normal']
    mat.node_tree.links.new(output,bsdf.inputs[socket])
for mesh in meshes:mesh.data.materials.clear();mesh.data.materials.append(mat)

torso_names={'Hips','Spine02','Spine01','Spine','neck'}
torso_points=[]
for mesh in meshes:
    groups={g.index:g.name for g in mesh.vertex_groups}
    for v in mesh.data.vertices:
        if sum(g.weight for g in v.groups if groups.get(g.group) in torso_names)>.65:
            torso_points.append(inv_world@mesh.matrix_world@v.co)
body_rx=max(abs(v.x) for v in torso_points)+.035
body_ymin=min(v.y for v in torso_points)-.035
body_ymax=max(v.y for v in torso_points)+.035
body_ycenter=(body_ymin+body_ymax)*.5
body_ry=(body_ymax-body_ymin)*.5

def update():bpy.context.view_layer.update()
def set_pose(name,m):
    pb=rig.pose.bones[name];pb.matrix=m;update()

def solve_limb(names,dest,pole_offset):
    first,mid,last=[rig.pose.bones[n] for n in names]
    p0=first.matrix.translation.copy();p1=mid.matrix.translation.copy();p2=last.matrix.translation.copy()
    l1=(p1-p0).length;l2=(p2-p1).length
    direction=dest-p0;dist=max(.0001,min(direction.length,l1+l2-.00001));direction.normalize()
    along=(l1*l1-l2*l2+dist*dist)/(2*dist)
    pole=p1-p0+pole_offset;pole-=direction*pole.dot(direction)
    if pole.length<.00001:pole=Vector((0,-1,0));pole-=direction*pole.dot(direction)
    pole.normalize();elbow=p0+direction*along+pole*math.sqrt(max(0,l1*l1-along*along))
    target_end=p0+direction*dist
    end_quat=last.matrix.to_quaternion()
    q=(p1-p0).rotation_difference(elbow-p0)@first.matrix.to_quaternion()
    set_pose(first.name,Matrix.LocRotScale(p0,q,Vector((1,1,1))))
    pm=mid.matrix.translation.copy();pe=last.matrix.translation.copy()
    q=(pe-pm).rotation_difference(target_end-pm)@mid.matrix.to_quaternion()
    set_pose(mid.name,Matrix.LocRotScale(pm,q,Vector((1,1,1))))
    set_pose(last.name,Matrix.LocRotScale(last.matrix.translation,end_quat,Vector((1,1,1))))

def smooth(a,b,x):
    t=max(0,min(1,(x-a)/(b-a)));return t*t*(3-2*t)

def source_pose(role,index):
    raw_rest,frames=cache[role]
    lo=int(index);hi=min(lo+1,len(frames)-1);alpha=index-lo
    mats={}
    for name in rest:
        a,b=frames[lo][name],frames[hi][name]
        q=a.to_quaternion().slerp(b.to_quaternion(),alpha)
        delta=q@raw_rest[name].to_quaternion().inverted()
        q=(inv_world.to_quaternion()@delta@world_rest[name].to_quaternion()).normalized()
        bone=rig.data.bones[name]
        if bone.parent:
            local_rest=rest[bone.parent.name].inverted()@rest[name]
            pos=mats[bone.parent.name]@local_rest.translation
        else:
            # UE's exported animation translations already evaluate in meters
            # after Blender's FBX scene conversion. Its exported rest skeleton
            # is 100x smaller than those keys: deriving scale from that rest
            # pose multiplied the pelvis displacement by 100 a second time.
            # The native retarget already used this exact target mesh.
            pos=inv_world@a.translation.lerp(b.translation,alpha)
        m=Matrix.LocRotScale(pos,q,Vector((1,1,1)));mats[name]=m
        if bone.parent:
            basis=(rest[bone.parent.name].inverted()@rest[name]).inverted()@mats[bone.parent.name].inverted()@m
        else:basis=rest[name].inverted()@m
        rig.pose.bones[name].matrix_basis=basis
    update()

def fit(role,phase):
    live=1-smooth(.3,.62,phase) if role=='Death' else 1
    for side,sign in [('Left',1),('Right',-1)]:
        ankle=rig.pose.bones[side+'Foot'].matrix.translation.copy()
        ankle.x+=sign*.03*live
        if live>0:solve_limb([side+'UpLeg',side+'Leg',side+'Foot'],ankle,Vector((sign*.02*live,0,0)))
    body=rig.pose.bones['Spine01'].matrix@rest['Spine01'].inverted()
    body_inv=body.inverted()
    for side,sign in [('Left',1),('Right',-1)]:
        hand=rig.pose.bones[side+'Hand'].matrix.translation.copy()
        p=body_inv@hand
        if .65<p.z<1.45:
            y=(p.y-body_ycenter)/body_ry
            if abs(y)<1:
                minx=body_rx*math.sqrt(1-y*y)+.045
                p.x=sign*max(sign*p.x,minx)
        p.x+=sign*.018*live
        solve_limb([side+'Arm',side+'ForeArm',side+'Hand'],body@p,body.to_3x3()@Vector((sign*.045,0,0)))
    # Author the ground contact on the actual skinned body, including the back
    # during the death fall. This modifies pelvis keys, not the bind pose.
    deps=bpy.context.evaluated_depsgraph_get();low=1000
    for mesh in meshes:
        ob=mesh.evaluated_get(deps);data=ob.to_mesh()
        low=min(low,min((ob.matrix_world@v.co).z for v in data.vertices));ob.to_mesh_clear()
    amount=.003-low
    if role=='Death' and amount<0:amount*=smooth(.48,.7,phase)
    m=rig.pose.bones['Hips'].matrix.copy();m.translation+=inv_world.to_3x3()@Vector((0,0,amount))
    set_pose('Hips',m)

def export(role):
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.fbx(filepath=str(OUT/f'A_FatZombie_{role}.fbx'),use_selection=True,
        object_types={'ARMATURE'},add_leaf_bones=False,use_armature_deform_only=False,
        bake_anim=True,bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True,bake_anim_simplify_factor=0,
        axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS')

actions={};report={}
for role,(src_intervals,dst_intervals,hold) in specs.items():
    action=bpy.data.actions.new('A_FatZombie_'+role);action.use_fake_user=True;activate(rig,action)
    action['source_animation']=source_meta['clips'][role]['source'];action['loop']=role in ['Idle','Walk']
    scene.frame_start=0;scene.frame_end=dst_intervals+hold
    previous={};first_pose={}
    for frame in range(scene.frame_end+1):
        scene.frame_set(frame)
        # Read the source independently of keys being written to the target.
        phase=min(1,frame/dst_intervals)
        source_pose(role,phase*src_intervals);fit(role,phase)
        # The source loops have duplicate terminal poses. Keep that seam after
        # body-fit IK and skin-ground correction instead of accumulating a
        # different endpoint from Blender's currently evaluated action.
        if frame==0:first_pose={pb.name:pb.matrix_basis.copy() for pb in ordered}
        if role in ['Idle','Walk'] and frame==dst_intervals:
            for pb in ordered:pb.matrix_basis=first_pose[pb.name]
            update()
        for pb in ordered:
            q=pb.rotation_quaternion.copy()
            if pb.name in previous and q.dot(previous[pb.name])<0:q.negate()
            pb.rotation_quaternion=q;previous[pb.name]=q.copy();pb.scale=(1,1,1)
            pb.keyframe_insert('location',frame=frame,group=pb.name)
            pb.keyframe_insert('rotation_quaternion',frame=frame,group=pb.name)
            pb.keyframe_insert('scale',frame=frame,group=pb.name)
        if frame%80==0:print(f'FAT_ZOMBIE_AUTHORING {role} {frame}/{scene.frame_end}',flush=True)
    if action.slots:rig.animation_data.action_slot=action.slots[0]
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
    scene.frame_set(0);export(role);actions[role]=action
    report[role]={'source':action['source_animation'],'fps':FPS,'frames':[0,scene.frame_end],
                  'seconds':scene.frame_end/FPS,'source_seconds':src_intervals/FPS,
                  'motion_seconds':dst_intervals/FPS,'hold_seconds':hold/FPS,'loop':action['loop']}

activate(rig,actions['Idle']);scene.frame_start=0;scene.frame_end=192;scene.frame_set(0)
rig['animation_source']='Mesh2Motion CC0, native UE IK retarget, body fit on original skin'
rig['authoring_note']='Candidate animation assets. No runtime or visual acceptance test performed.'
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'FatZombie_Meshy_Animated.blend'))
(ROOT/'animation_contract.json').write_text(json.dumps({'clips':report,'body_fit':{'arm_body_radius_m':body_rx,'stance_offset_each_m':.03,'hand_padding_m':.045},'state':'authored; user visual/runtime testing pending'},indent=2),encoding='utf-8')
print('FAT_ZOMBIE_BODY_FIT_COMPLETE '+json.dumps(report),flush=True)
