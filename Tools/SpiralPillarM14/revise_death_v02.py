"""Author M14 coherent death, retaining the original mesh, skin and other actions."""
from pathlib import Path
import json, math, bpy
import numpy as np
from mathutils import Vector, Quaternion

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT=ROOT/'ProductionV02'
for directory in ('Authoring','Exports','Records'):(OUT/directory).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'ProductionV01/Authoring/M14_Rigged_Animated_v01.blend'))
rig=bpy.data.objects['M14_Rig'];scene=bpy.context.scene
rig.animation_data.action=None
# Source surface samples are used to author floor clearance, not to render/test a pose.
points=[]
for ob in scene.objects:
    if ob.type!='MESH':continue
    vertices=np.empty(len(ob.data.vertices)*3,np.float32)
    ob.data.vertices.foreach_get('co',vertices)
    points.append(vertices.reshape(-1,3))
points=np.concatenate(points)
pivot=np.array(rig.data.bones['base'].head_local,dtype=np.float32)

def reset():
    for bone in rig.pose.bones:
        bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)

def smooth(value):
    x=max(0.,min(1.,value));return x*x*(3-2*x)

def tip(t):
    # 50 degrees at the existing 1.8 s handoff; continue to a resting side pose
    # only for the shared physics-budget fallback.
    if t<=.3:return 0.
    if t<=1.8:
        x=(t-.3)/1.5
        return math.radians(50.)*x*x
    if t<2.65:
        x=(t-1.8)/.85
        # Hermite interpolation retains handoff angular velocity and settles to zero.
        return math.radians(50.)*(2*x**3-3*x*x+1)+math.radians(66.6666667)*.85*(x**3-2*x*x+x)+math.pi/2*(-2*x**3+3*x*x)
    return math.pi/2

reset();action=bpy.data.actions.new('A_M14_Death_v02');action.use_fake_user=True
rig.animation_data.action=action
scene.render.fps=30;scene.frame_start=0;scene.frame_end=90
for frame in range(91):
    reset();t=frame/30.;angle=-tip(t)
    base=rig.pose.bones['base']
    axis=base.bone.matrix_local.to_3x3().inverted()@Vector((1,0,0))
    base.rotation_quaternion=Quaternion(axis,angle)
    # One continuous rigid motion through the shared base avoids weight discontinuities.
    # Local scale, mouth, membrane, chain and all root branches remain at their rest offsets.
    y=points[:,1]-pivot[1];z=points[:,2]-pivot[2]
    surface_z=y*math.sin(angle)+z*math.cos(angle)+pivot[2]
    floor_offset=-float(surface_z.min())+.01*smooth(t/.3)
    delta=Vector((0,.20*smooth(t/2.65),floor_offset))
    base.location=base.bone.matrix_local.to_3x3().inverted()@delta
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
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
export=OUT/'Exports/A_M14_Death_v02.fbx'
bpy.ops.export_scene.fbx(filepath=str(export),object_types={'ARMATURE'},use_selection=True,
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_UNITS',axis_forward='-Z',axis_up='Y',
    add_leaf_bones=False,use_armature_deform_only=True,armature_nodetype='NULL',path_mode='STRIP',
    use_mesh_modifiers=False,bake_anim=True,bake_anim_use_all_actions=False,
    bake_anim_use_nla_strips=False,bake_anim_simplify_factor=0.)
rig['display_name']='螺柱 M-14'
rig['runtime_walk_speed_cm_s']=56.;rig['source_walk_speed_cm_s']=28.
rig['runtime_move_play_rate']=2.;rig['runtime_move_cycle_seconds']=1.2
rig.animation_data.action=None;reset();scene.frame_set(0)
blend=OUT/'Authoring/M14_Rigged_Animated_v02.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend),compress=True)
receipt=dict(display_name='螺柱 M-14',source_blend=str(ROOT/'ProductionV01/Authoring/M14_Rigged_Animated_v01.blend'),
    blend=str(blend),death_fbx=str(export),death_seconds=3.,handoff_seconds=1.8,handoff_degrees=50.,
    death='One base-driven tilt; fixed local offsets and unit scale for all subordinate bones; source-surface floor clearance.',
    walk_speed_cm_s=56.,animation_source_speed_cm_s=28.,runtime_move_rate=2.,runtime_move_period_seconds=1.2,
    topology_changed=False,weights_changed=False,other_source_actions_changed=False,rendered=False,tested=False)
(OUT/'Records/authoring.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print('M14_V02_DEATH_AUTHORED',flush=True)
