"""Rebuild the single-hand axe viewmodel with the battle axe geometry.

Blender --background --python <this> -- <blend> <fitted.fbx> <grip_z> <out_dir> <tag> --render
Blender --background --python <this> -- <blend> <fitted.fbx> ---candidates <out_dir>

Keeps the accepted rig, arms and five clips; swaps only the tool mesh. The tool grip
section at grip_z is centered on the origin, then placed by WPN_root's rest transform,
exactly like the 2026-09-13 authoring. Diagnostic renders only, no acceptance claims.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

args = sys.argv[sys.argv.index('--') + 1:]
blend = Path(args[0])
fitted = Path(args[1])
out_dir = Path(args[2])
out_dir.mkdir(parents=True, exist_ok=True)
do_render = '--render' in args


def load():
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    scene = bpy.context.scene
    scene.frame_set(0)
    return scene, bpy.data.objects['SK_Harvest_Axe_Rig'], bpy.data.objects['SK_Manny_Arms_Export']


def remove_tool(scene):
    for obj in list(scene.objects):
        if obj.type == 'MESH' and obj.name.startswith('Harvest_Axe'):
            bpy.data.objects.remove(obj, do_unlink=True)


def add_tool(scene, rig, grip_z, report_entry):
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    bpy.ops.import_scene.fbx(filepath=str(fitted))
    tool = next(o for o in scene.objects if o.type == 'MESH' and o.name.startswith('SM_BattleAxe'))
    tool.data.transform(tool.matrix_world)
    tool.matrix_world = Matrix.Identity(4)
    # The hand wraps about 6 cm above the grip point (palm offset); keep that section on bare wood.
    section = [v.co for v in tool.data.vertices if abs(v.co.z - grip_z) < .06]
    center = Vector(((min(v.x for v in section) + max(v.x for v in section)) * .5,
                     (min(v.y for v in section) + max(v.y for v in section)) * .5, grip_z))
    tool.data.transform(Matrix.Translation(-center))
    tool.data.materials.clear()
    tool.data.materials.append(bpy.data.materials.new('M_Harvest_Axe'))
    tool.data.transform(rest['WPN_root'])
    tool.parent = rig
    group = tool.vertex_groups.new(name='WPN_root')
    group.add(list(range(len(tool.data.vertices))), 1., 'REPLACE')
    modifier = tool.modifiers.new('Rigid tool to shared grip motion', 'ARMATURE')
    modifier.object = rig
    tool.name = 'Harvest_Axe'
    report_entry.update({
        'grip_z': grip_z, 'section_vertices': len(section),
        'grip_center_before_place': [round(v, 4) for v in center],
        'triangles': sum(len(p.vertices) - 2 for p in tool.data.polygons),
    })
    return tool, rest


def render_views(scene, rig, tag):
    camera_data = bpy.data.cameras.new('GripCheck')
    camera = bpy.data.objects.new('GripCheck', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'TEXTURE'
    scene.render.resolution_x = 700
    scene.render.resolution_y = 700
    hand = (rig.matrix_world @ rig.pose.bones['WPN_root'].matrix).translation
    views = [
        ('side', hand + Vector((.55, 0, .04)), .52),
        ('front', hand + Vector((0, .55, .06)), .52),
        ('top', hand + Vector((0, .02, .55)), .52),
        ('quarter', hand + Vector((.42, -.42, .22)), .52),
        ('full', hand + Vector((.62, -.52, .18)), 1.55),
    ]
    for name, location, ortho in views:
        camera.location = location
        camera.rotation_euler = (hand - location).to_track_quat('-Z', 'Y').to_euler()
        camera_data.ortho_scale = ortho
        scene.render.filepath = str(out_dir / f'{tag}_{name}.png')
        bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(camera, do_unlink=True)
    print('RENDERED', tag, flush=True)


if '--candidates' in args:
    scene, rig, arms = load()
    if do_render:
        render_views(scene, rig, 'old')
    report = {'candidates': []}
    for text in args[3:]:
        if text.startswith('--'):
            continue
        entry = {'grip_z': float(text)}
        remove_tool(scene)
        add_tool(scene, rig, float(text), entry)
        bpy.context.view_layer.update()
        render_views(scene, rig, 'cand' + text.replace('.', 'p').replace('-', 'm'))
        report['candidates'].append(entry)
    (out_dir / 'candidate_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
else:
    grip_z = float(args[3])
    tag = args[4]
    export = out_dir / 'Export'
    export.mkdir(parents=True, exist_ok=True)
    scene, rig, arms = load()
    entry = {}
    remove_tool(scene)
    tool, rest = add_tool(scene, rig, grip_z, entry)
    bpy.context.view_layer.update()
    if do_render:
        render_views(scene, rig, tag)
    scene.frame_set(0)
    rig.data.pose_position = 'REST'
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [arms, tool, rig]:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(export / 'SK_Harvest_Axe.fbx'), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, axis_forward='-Y', axis_up='Z',
        add_leaf_bones=False, bake_anim=False, mesh_smooth_type='FACE', use_tspace=True)
    rig.data.pose_position = 'POSE'
    blend_out = out_dir / 'BattleAxe_SingleHand_Editable.blend'
    # The imported FBX points its images at a .fbm folder the ZIP does not contain and the
    # tool material is replaced anyway; drop the leftovers so the file packs cleanly.
    for material in list(bpy.data.materials):
        if material.users == 0:
            bpy.data.materials.remove(material)
    for image in list(bpy.data.images):
        if image.users == 0 or '.fbm' in (image.filepath or ''):
            bpy.data.images.remove(image)
    try:
        bpy.ops.file.pack_all()
    except RuntimeError as error:
        print('PACK_SKIPPED', error, flush=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_out))
    entry['export'] = str(export / 'SK_Harvest_Axe.fbx')
    entry['blend'] = str(blend_out)
    (out_dir / f'{tag}-rebuild.json').write_text(json.dumps(entry, indent=2), encoding='utf-8')
    print(json.dumps(entry, indent=2))