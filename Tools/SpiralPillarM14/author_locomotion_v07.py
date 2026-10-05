"""Add periodic secondary motion to M14's existing crawl and turn actions."""
from pathlib import Path
import json, math
import bpy
from mathutils import Vector, Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV07'
for folder in ('Authoring','Exports','Records'):(OUT/folder).mkdir(parents=True,exist_ok=True)
source=ROOT/'ProductionV06/Authoring/M14_Rigged_SoftDeath_v06.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig=bpy.data.objects['M14_Rig'];scene=bpy.context.scene
scene.render.fps=30;scene.frame_start=0;scene.frame_end=72
axes={bone.name:bone.bone.matrix_local.to_3x3().inverted() for bone in rig.pose.bones}

def turn(name,axis,angle):
    bone=rig.pose.bones[name]
    bone.rotation_quaternion=Quaternion(axes[name]@Vector(axis),angle)@bone.rotation_quaternion

def shift(name,delta):
    rig.pose.bones[name].location+=axes[name]@Vector(delta)

clips={}
for role in ('Move','TurnLeft','TurnRight'):
    original=bpy.data.actions['A_M14_'+role]
    rig.animation_data.action=original
    # Read the existing authored stride into the new action, including planted
    # roots/base. Only body/accessory rotation and local mouth motion are added.
    samples=[]
    for frame in range(73):
        scene.frame_set(frame)
        samples.append({bone.name:(bone.location.copy(),bone.rotation_quaternion.copy(),bone.scale.copy())
                        for bone in rig.pose.bones})
    name='A_M14_'+role+'_v07'
    action=bpy.data.actions.new(name);action.use_fake_user=True
    rig.animation_data.action=action
    turn_side=0 if role=='Move' else (1 if role=='TurnLeft' else -1)
    for frame,sample in enumerate(samples):
        scene.frame_set(frame)
        for bone in rig.pose.bones:
            bone.rotation_mode='QUATERNION'
            bone.location,bone.rotation_quaternion,bone.scale=sample[bone.name]
        # All frequencies are integer cycle harmonics: matching pose/velocity at
        # the loop seam, with no random-frame jitter at the existing 2x speed.
        phase=2*math.pi*(frame%72)/72.
        previous=(0.,0.,0.)
        for k in range(1,6):
            height=k/5.;lag=.30*k
            desired=(height*(.028*math.sin(2*phase-lag)+.012*math.sin(phase-.35)),
                     height*(.078*math.sin(phase-lag)+.010*math.sin(2*phase-lag+.6)+turn_side*.018),
                     height*.024*math.sin(phase-lag-.65))
            # Differences along the spine bound the cumulative lean of the top.
            for axis,value,old in zip(((1,0,0),(0,1,0),(0,0,1)),desired,previous):
                turn(f'spine_{k:02d}',axis,value-old)
            previous=desired
        for side,sign in (('L',1),('R',-1)):
            side_phase=phase+(.32 if side=='L' else -.48)
            for k in range(3):
                lag=.50+k*.35
                swing=sign*(.025+.008*k)*math.sin(side_phase-lag)
                flutter=sign*(.0015+.0015*k)*math.sin(3*side_phase-lag*1.4)
                fore=.014*math.sin(2*side_phase-lag-.45)
                turn(f'mem_{side}_{k}',(0,1,0),swing+flutter)
                turn(f'mem_{side}_{k}',(1,0,0),fore)
                # Shared main swing keeps chain and membrane attachment regions
                # together. Only a small metal rattle separates their motion.
                turn(f'chain_{side}_{k}',(0,1,0),swing+sign*.002*math.sin(3*side_phase-lag-.3))
                turn(f'chain_{side}_{k}',(1,0,0),fore)
            turn('sac_'+side,(1,0,0),.063*math.sin(side_phase-1.1)+.010*math.sin(2*side_phase-1.5))
            turn('sac_'+side,(0,1,0),sign*.037*math.sin(side_phase-1.35))
            turn('sac_'+side,(0,0,1),sign*.009*math.sin(2*side_phase-1.8))
        turn('maw',(1,0,0),.021*math.sin(2*phase-.65))
        turn('maw',(0,1,0),.018*math.sin(phase-.8))
        shift('maw',(.0035*math.sin(phase-.8),.004*math.sin(2*phase-.9),.005*math.sin(2*phase-1.1)))
        for k in range(8):
            angle=2*math.pi*k/8
            ripple=.0015*math.sin(2*phase-angle-.8)
            shift(f'jaw_{k:02d}',(math.cos(angle)*ripple,.0006*math.sin(3*phase-angle),math.sin(angle)*ripple))
        turn('restraint',(0,0,1),.003*math.sin(2*phase-1.25))
        turn('restraint',(1,0,0),.002*math.sin(3*phase-.9))
        for bone in rig.pose.bones:
            bone.keyframe_insert('location',frame=frame,group=bone.name)
            bone.keyframe_insert('rotation_quaternion',frame=frame,group=bone.name)
            bone.keyframe_insert('scale',frame=frame,group=bone.name)
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag=strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:key.interpolation='LINEAR'
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    bpy.context.view_layer.objects.active=rig
    path=OUT/'Exports'/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),object_types={'ARMATURE'},use_selection=True,
        apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
        add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL',path_mode='STRIP',
        use_mesh_modifiers=False,bake_anim=True,bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
    clips[role]={'action':name,'file':str(path),'duration_seconds':2.4,'loop':True,'source_action':original.name}
    print('M14_V07_AUTHORED',role,flush=True)
rig.animation_data.action=None
for bone in rig.pose.bones:
    bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
scene.frame_set(0)
blend=OUT/'Authoring/M14_Rigged_Locomotion_v07.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
record={'source_blend':str(source),'blend':str(blend),'clips':clips,'fps':30,
    'root_base_and_root_stride':'copied from original actions without additions',
    'secondary_motion':'bounded spine wave; delayed asymmetric sacs; attached membrane/chain swing; mouth and plate micro-motion',
    'runtime_walk_speed_cm_s':56.,'source_stride_speed_cm_s':28.,'full_speed_rate':2.,
    'geometry_skin_death_attacks_unchanged':True,'runtime_physics_added':False,'tested':False,'rendered':False}
(OUT/'Records/authoring.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('M14_V07_AUTHORING_SAVED',flush=True)
