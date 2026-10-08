"""Retain the ripple gait; replace four legacy actions on the same bind skeleton."""
from pathlib import Path
import bpy, math, json
from mathutils import Vector, Matrix, Quaternion
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006');OUT=ROOT/'RigRepairV3'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'BoundCongregate_RigV3.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');scene=bpy.context.scene
recipe=json.loads((ROOT/'Authoring/rig_recipe.json').read_text());scene.render.fps=30
rest={b.name:b.matrix_local.copy() for b in rig.data.bones};pose={}
def point(p):return Vector((p[0]*recipe['scale'],p[1]*recipe['scale'],(p[2]-recipe['ground_z'])*recipe['scale']))
def convert(name,matrix,inverse=False):
    bone=rig.data.bones[name];kwargs=dict(invert=inverse)
    if bone.parent:kwargs.update(parent_matrix=pose[bone.parent.name],parent_matrix_local=rest[bone.parent.name])
    return bone.convert_local_to_pose(matrix,rest[name],**kwargs)
def refresh():
    for b in rig.data.bones:pose[b.name]=convert(b.name,rig.pose.bones[b.name].matrix_basis)
def assign(name,matrix):
    rig.pose.bones[name].matrix_basis=convert(name,matrix,True);pose[name]=matrix.copy()
def rotate(name,axis,angle):
    rig.pose.bones[name].rotation_quaternion=Quaternion((rest[name].to_3x3().inverted()@Vector(axis)).normalized(),angle)
def segment(name,head,tail):
    direction=rig.data.bones[name].tail_local-rig.data.bones[name].head_local
    m=direction.rotation_difference(tail-head).to_matrix().to_4x4()@rest[name];m.translation=head;assign(name,m)
def leg_pose(leg,goal):
    upper,lower,foot=['leg_'+leg['name']+'_'+s for s in ('upper','lower','foot')]
    hip,knee,ankle,_=[point(p) for p in leg['points']];parent=rig.data.bones[upper].parent.name
    delta=pose[parent]@rest[parent].inverted();start=delta@hip;old_knee=delta@knee
    a,b=(knee-hip).length,(ankle-knee).length;direction=(goal-start).normalized()
    d=max(abs(a-b)+.002,min((goal-start).length,(a+b)*.975))
    pole=old_knee-start;pole-=direction*pole.dot(direction)
    if pole.length<.001:pole=Vector((0,0,1))-direction*direction.z
    x=(a*a-b*b+d*d)/(2*d);joint=start+direction*x+pole.normalized()*math.sqrt(max(0,a*a-x*x));end=start+direction*d
    segment(upper,start,joint);segment(lower,joint,end)
    m=rest[foot].copy();m.translation=end;assign(foot,m)
def smooth(t):
    t=max(0,min(1,t));return t*t*t*(10+t*(-15+6*t))
def bump(t,start,peak,end):return smooth((t-start)/(peak-start)) if t<peak else 1-smooth((t-peak)/(end-peak))
for role,duration in [('Idle',4),('Bite',1.7),('Hit',.7),('Death',2.2)]:
    previous=bpy.data.actions.get('A_BoundCongregate_'+role+'V3')
    if previous:bpy.data.actions.remove(previous)
    action=bpy.data.actions.new('A_BoundCongregate_'+role+'V3');action.use_fake_user=True;rig.animation_data.action=action
    scene.frame_start=1;scene.frame_end=round(duration*30)+1
    for frame in range(1,scene.frame_end+1):
        scene.frame_set(frame);t=(frame-1)/30;phase=t/duration;wave=math.tau*phase
        for pb in rig.pose.bones:pb.rotation_mode='QUATERNION';pb.matrix_basis=Matrix.Identity(4)
        offset=Vector((0,0,.012*math.sin(wave)));wind=pulse=collapse=0.
        if role=='Bite':
            wind=bump(t,0,.45,.72);pulse=bump(t,.65,.92,1.42)
            offset+=Vector((0,.055*wind-.20*pulse,.045*wind))
            rotate('body',(1,0,0),-.06*wind+.09*pulse)
            for side,sign in [('L',-1),('R',1)]:rotate('jaw_'+side,(0,0,1),sign*(.12*wind-.20*pulse))
        elif role=='Hit':
            pulse=bump(t,0,.17,.7);offset.y=.060*pulse;rotate('body',(0,1,0),-.05*pulse)
        elif role=='Death':
            collapse=smooth(t/1.7);offset.z=-.18*collapse;rotate('body',(0,1,0),.06*collapse)
        else:rotate('body',(0,1,0),.010*math.sin(wave))
        rig.pose.bones['body'].location=rest['body'].to_3x3().inverted()@offset
        for pb in rig.pose.bones:
            prefix=pb.name.split('_')[0]
            if prefix not in ('curl','feeler','scent','grasp'):continue
            index=int(pb.name.rsplit('_',1)[1]);amplitude=(.018 if prefix=='curl' else .030)*(1+.5*pulse)*(1-.85*collapse)
            ax=(rest[pb.name].to_3x3().inverted()@Vector((1,0,0))).normalized()
            az=(rest[pb.name].to_3x3().inverted()@Vector((0,0,1))).normalized()
            # Integer harmonics close the entire idle chain, including its tips.
            pb.rotation_quaternion=Quaternion(ax,amplitude*math.sin(wave-index*.55))@Quaternion(az,amplitude*.4*math.sin(2*wave-index*.7))
        refresh()
        for leg in recipe['legs']:
            hip,_,ankle,_=[point(p) for p in leg['points']]
            goal=ankle+Vector((hip.x-ankle.x,hip.y-ankle.y,0))*.18
            if role=='Death':goal+=Vector((ankle.x,ankle.y,0)).normalized()*.04*collapse
            leg_pose(leg,goal)
        for pb in rig.pose.bones:
            for channel in ('location','rotation_quaternion','scale'):pb.keyframe_insert(channel,frame=frame,group=pb.name)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:key.interpolation='LINEAR'
manifest=dict(fps=30,walk_speed_cm=50,clips={})
for role in ('Idle','Walk','TurnLeft','TurnRight','Bite','Hit','Death'):
    action=bpy.data.actions['A_BoundCongregate_'+role+('V2' if role in ('Walk','TurnLeft','TurnRight') else 'V3')]
    rig.animation_data.action=action;scene.frame_start,scene.frame_end=map(round,action.frame_range)
    scene.frame_set(1);bpy.context.view_layer.update();bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
    name='A_BoundCongregate_'+role+'V3';path=OUT/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'ARMATURE'},axis_forward='-Y',axis_up='Z',
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',add_leaf_bones=False,use_armature_deform_only=False,bake_anim=True,
        bake_anim_use_all_actions=False,bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0,bake_anim_force_startend_keying=True,path_mode='STRIP')
    manifest['clips'][role]=dict(name=name,file=str(path),duration=(scene.frame_end-1)/30,loop=role in ('Idle','Walk','TurnLeft','TurnRight'))
rig.animation_data.action=None
for pb in rig.pose.bones:pb.matrix_basis.identity()
bpy.context.view_layer.update();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BoundCongregate_RigV3.blend'))
(OUT/'motion_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('ACTIONS_V3_EXPORTED',flush=True)
