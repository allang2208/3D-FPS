"""Read the requested legacy runner visually and export its actual gameplay clip."""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).parent
(ROOT / 'prepared').mkdir(exist_ok=True)
(ROOT / 'source_preview').mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=str(ROOT / 'sources/runner_zombie_v02.glb'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
rig.name = 'GodotRunnerRoot'
meshes = [o for o in bpy.data.objects if o.type == 'MESH'
          and any(m.type == 'ARMATURE' and m.object == rig for m in o.modifiers)]
for bone in rig.data.bones:
    bone.name = bone.name.replace(' ', '_')
action = bpy.data.actions['Walk']
rig.animation_data_create()
rig.animation_data.action = action
rig.animation_data.action_slot = action.slots[0]
for track in rig.animation_data.nla_tracks:
    track.mute = True
start, end = action.frame_range
scene.frame_start = round(start)
scene.frame_end = round(end)
scene.frame_set(scene.frame_start)
bpy.context.view_layer.update()
points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
lo = Vector(tuple(min(p[i] for p in points) for i in range(3)))
hi = Vector(tuple(max(p[i] for p in points) for i in range(3)))
center = (lo + hi) / 2
height = hi.z - lo.z
report = {'action': action.name, 'frames': [start, end], 'seconds': (end-start)/30,
          'mesh_bounds': [list(lo), list(hi)], 'rig_matrix': [list(r) for r in rig.matrix_world],
          'bones': {b.name: {'parent': b.parent.name if b.parent else None,
                           'head_world': list(rig.matrix_world @ b.head_local)} for b in rig.data.bones}}
(ROOT / 'source_rig.json').write_text(json.dumps(report, indent=2), encoding='utf-8')

def select_source():
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [rig] + meshes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = rig

options = dict(use_selection=True, object_types={'ARMATURE','MESH'},
               add_leaf_bones=False, use_armature_deform_only=False,
               bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
               bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
               axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
               apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE', path_mode='STRIP')
select_source()
rig.data.pose_position = 'REST'
bpy.ops.export_scene.fbx(filepath=str(ROOT/'prepared/SK_GodotRunner.fbx'), bake_anim=False, **options)
rig.data.pose_position = 'POSE'
select_source()
bpy.ops.export_scene.fbx(filepath=str(ROOT/'prepared/A_GodotRunner_Run.fbx'), bake_anim=True, **options)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'GodotRunner_Source.blend'))
if '--preview' not in sys.argv:
    print('GODOT_RUNNER_SOURCE_PREPARED', flush=True)
    sys.exit(0)

# The user requested looking at this old animation. These are source references,
# not an acceptance render of the new Mutant3 result.
scene.render.engine = 'BLENDER_WORKBENCH'
scene.render.resolution_x = 320
scene.render.resolution_y = 400
scene.render.resolution_percentage = 100
scene.display.shading.light = 'STUDIO'
scene.display.shading.color_type = 'MATERIAL'
scene.display.shading.show_shadows = True
scene.display.shading.show_cavity = True
scene.display.shading.background_type = 'WORLD'
if scene.world is None:
    scene.world = bpy.data.worlds.new('ReferenceWorld')
scene.world.color = (.16,.16,.16)
camera = bpy.data.cameras.new('SourceCamera')
ob = bpy.data.objects.new('SourceCamera',camera)
scene.collection.objects.link(ob)
ob.location = center + Vector((height*2.2, -height*3.5, height*.7))
ob.rotation_euler = (center-ob.location).to_track_quat('-Z','Y').to_euler()
camera.type = 'ORTHO'
camera.ortho_scale = height*1.5
scene.camera = ob
for i in range(8):
    frame = start+(end-start)*i/8
    scene.frame_set(math.floor(frame), subframe=frame%1)
    scene.render.filepath = str(ROOT/'source_preview'/f'run_{i:02d}.png')
    bpy.ops.render.render(write_still=True)
print('GODOT_RUNNER_SOURCE_PREPARED', flush=True)
