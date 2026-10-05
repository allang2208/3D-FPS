"""Author sac-compression spit and mirrored root sweeps on the preserved M14 rig."""
from pathlib import Path
import json, math, bpy
from mathutils import Vector, Quaternion

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/SpiralPillarM14Meshy20261004')
OUT = ROOT/'ProductionV05'
for folder in ('Authoring', 'Exports', 'Records'):
    (OUT/folder).mkdir(parents=True, exist_ok=True)
source = ROOT/'ProductionV03/Authoring/M14_Rigged_Animated_v03.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
rig = bpy.data.objects['M14_Rig']
scene = bpy.context.scene
scene.render.fps = 30
rig.animation_data_create()
rig.animation_data.action = None

def ease(value):
    value = max(0., min(1., value))
    return value*value*(3.-2.*value)

def pulse(t, start, peak, end):
    return ease((t-start)/(peak-start)) if t < peak else 1.-ease((t-peak)/(end-peak))

def reset():
    for bone in rig.pose.bones:
        bone.location = (0, 0, 0)
        bone.rotation_mode = 'QUATERNION'
        bone.rotation_quaternion = (1, 0, 0, 0)
        bone.scale = (1, 1, 1)

def shift(name, delta):
    bone = rig.pose.bones[name]
    bone.location = bone.bone.matrix_local.to_3x3().inverted() @ Vector(delta)

def turn(name, axis, angle):
    bone = rig.pose.bones[name]
    local = bone.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
    bone.rotation_quaternion = Quaternion(local, angle) @ bone.rotation_quaternion

clips = {}
for role, duration in [('Spit', 2.4), ('RootSweep_PosX', 2.2), ('RootSweep_NegX', 2.2)]:
    name = 'A_M14_'+role+'_v05'
    action = bpy.data.actions.new(name)
    action.use_fake_user = True
    rig.animation_data.action = action
    scene.frame_start = 0
    scene.frame_end = round(duration*30)
    for frame in range(scene.frame_end+1):
        scene.frame_set(frame)
        reset()
        t = frame/30.
        if role == 'Spit':
            pressure = pulse(t, 0., .70, 1.30)
            expel = pulse(t, .80, 1.10, 1.65)
            recoil = pulse(t, 1.10, 1.30, 2.25)
            for k in range(1, 6):
                turn(f'spine_{k:02d}', (1,0,0), -.022*pressure+.012*expel-.010*recoil)
                turn(f'spine_{k:02d}', (0,0,1), (-1)**k*.028*pressure)
            shift('maw', (0, .045*pressure-.23*expel, .04*expel))
            gape = pulse(t, .28, .93, 1.65)
            for k in range(8):
                angle = 2*math.pi*k/8
                shift(f'jaw_{k:02d}', (.046*math.cos(angle)*gape, -.014*gape, .052*math.sin(angle)*gape))
            for side, sign in [('L',1), ('R',-1)]:
                delayed = pulse(t, .06 if side == 'R' else 0., .72, 1.32)
                squeeze = 1.+.11*delayed-.075*expel
                rig.pose.bones['sac_'+side].scale = (squeeze, 1.-.04*delayed+.03*expel, squeeze)
                turn('sac_'+side, (1,0,0), -.065*pressure+.10*recoil)
                for k in range(3):
                    sway = sign*(.022*pressure-.025*recoil)*(k+1)/3
                    turn(f'mem_{side}_{k}', (0,1,0), sway)
                    turn(f'chain_{side}_{k}', (0,1,0), sway*.45)
        else:
            sign = 1 if role.endswith('PosX') else -1
            wind = pulse(t, 0., .70, 1.75)
            reach = ease((t-.50)/.30)*(1.-ease((t-1.22)/.65))
            lift = ease((t-.10)/.55)*(1.-ease((t-1.23)/.75))
            travel = ease((t-.80)/.40)
            settle = 1.-ease((t-1.20)/.95)
            sweep_angle = (.48*wind*(1.-travel)-.78*travel)*settle
            for k in range(1,6):
                turn(f'spine_{k:02d}', (0,0,1), sign*(.028*wind-.045*travel*settle))
            # Three neighboring fans move together with a smooth angular envelope.
            # Other-side roots and the base remain planted. No bone scaling.
            for k in range(8):
                angle = 2*math.pi*k/8
                side_weight = max(0., sign*math.cos(angle))
                radial = Vector((math.cos(angle), math.sin(angle), 0))
                turn(f'rootfan_{k:02d}', (0,0,1), sign*sweep_angle*side_weight)
                shift(f'rootfan_{k:02d}', radial*(.07*reach*side_weight)+Vector((0,0,.035*lift*side_weight)))
                shift(f'roottoe_{k:02d}', radial*(.90*reach*side_weight-.06*wind*side_weight)+Vector((0,0,.24*lift*side_weight)))
            for side, sac_sign in [('L',1), ('R',-1)]:
                sway = pulse(t, .25, 1.16, 2.2)
                turn('sac_'+side, (0,1,0), sign*.10*sway)
                for k in range(3):
                    turn(f'mem_{side}_{k}', (0,1,0), sign*.018*sway*(k+1)/3)
                    turn(f'chain_{side}_{k}', (0,1,0), sign*.008*sway)
        for bone in rig.pose.bones:
            bone.keyframe_insert('location', frame=frame, group=bone.name)
            bone.keyframe_insert('rotation_quaternion', frame=frame, group=bone.name)
            bone.keyframe_insert('scale', frame=frame, group=bone.name)
    for slot in action.slots:
        for layer in action.layers:
            for strip in layer.strips:
                bag = strip.channelbag(slot)
                if bag:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    filename = OUT/'Exports'/(name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(filename), object_types={'ARMATURE'}, use_selection=True,
        apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS', axis_forward='-Z', axis_up='Y',
        add_leaf_bones=False, use_armature_deform_only=True, armature_nodetype='NULL', path_mode='STRIP',
        use_mesh_modifiers=False, bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.)
    clips[role] = dict(file=str(filename), action=name, duration_seconds=duration)
    print('M14_V05_AUTHORED', role, flush=True)
rig.animation_data.action = None
reset()
scene.frame_set(0)
blend = OUT/'Authoring/M14_Rigged_Animated_v05.blend'
bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
record = dict(source_blend=str(source), blend=str(blend), clips=clips, fps=30,
    spit_aim_lock_seconds=.65, spit_release_seconds=1.10, sweep_contact_window_seconds=[.80,1.20],
    sweep_toe_tail_cm=46., sweep_toe_tail_drop_cm=8.5,
    positive_x_root_indices=[7,0,1], negative_x_root_indices=[3,4,5],
    mesh_skin_and_existing_actions_preserved=True, tested=False, rendered=False)
(OUT/'Records/authoring.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
print('M14_V05_AUTHORING_SAVED', flush=True)
