"""Author icon inputs from the two currently installed, joined runtime meshes."""
from pathlib import Path
import bpy, hashlib, json, sys
from mathutils import Vector

P = Path(__file__).resolve().parent
R = P.parents[2]
sys.path.insert(0, 'C:/Users/allan/.codex/skills/ue5-weapon-workflow/scripts')
from apply_modification_icon_grayscale import apply_grayscale, neutral_output

items = [
    dict(id='static_field_grip', name='静电场', revision='StaticFieldGripV3Game',
         blend='StaticField_Editable.blend', mesh='SM_ThunderGodHammer_grip_static_field_V3Game'),
    dict(id='coil_grip', name='线圈', revision='CoilGripV1',
         blend='Coil_Editable.blend', mesh='SM_ThunderGodHammer_grip_coil'),
]
for row in items:
    source = P.parent / row['revision'] / row['blend']
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version = 0
    subject = bpy.data.objects[row['mesh']]
    for obj in list(bpy.data.objects):
        if obj != subject:
            bpy.data.objects.remove(obj, do_unlink=True)
    subject.hide_render = False
    subject.hide_set(False)
    corners = [subject.matrix_world @ Vector(v) for v in subject.bound_box]
    low = Vector(tuple(min(v[i] for v in corners) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in corners) for i in range(3)))
    center = (low + high) / 2
    subject.location -= center
    materials = apply_grayscale([subject])
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 64
    scene.cycles.use_denoising = True
    scene.render.resolution_x = scene.render.resolution_y = 1024
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = True
    scene.world = bpy.data.worlds.new('GripIconNeutralStudio')
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get('Background')
    background.inputs[0].default_value = (.16, .16, .16, 1)
    background.inputs[1].default_value = .4
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'
    scene.view_settings.exposure = -2.2
    neutral_output(scene)
    def light(name, position, energy, size):
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = energy, 'DISK', size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = position
        obj.rotation_euler = (-obj.location).to_track_quat('-Z', 'Y').to_euler()
    light('Key', (-.35, -.45, .4), 18, .45)
    light('Rim', (.3, .15, .12), 24, .35)
    light('Fill', (.45, -.4, -.25), 7, .35)
    data = bpy.data.cameras.new('GripIconCamera')
    data.type = 'ORTHO'
    data.ortho_scale = (high.z - low.z) / .88
    camera = bpy.data.objects.new('GripIconCamera', data)
    scene.collection.objects.link(camera)
    camera.location = (.28, -1, 0)
    camera.rotation_euler = (-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = camera
    scene.render.filepath = str(P / (row['id'] + '_source.png'))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(P / (row['id'] + '_icon.blend')))
    bpy.ops.render.render(write_still=True)
    row.update(source_blend=str(source), object=row['mesh'],
               runtime_mesh='/Game/Weapons/ThunderGodHammer20261028/'+row['revision']+'/Meshes/'+row['mesh'],
               source_render=scene.render.filepath, source_dimensions_m=list(high-low),
               frame_reference=str(R / 'SourceAssets/FirearmFramedIcons20260930/muzzle_brake_framed_v2.png'),
               key='ue_thunder_god_hammer_grip_'+row['id'],
               camera=dict(type='ORTHO', position=list(camera.location), scale=data.ortho_scale,
                           up='+Z', mechanical_axis='+Z', view='front, 15.6 degrees around shaft; level'),
               grayscale_materials=materials)
    baseline = []
    icon_dir = R / 'Content/ColdSteelData/AttachmentIcons20260913'
    for suffix in ('.png', '.uasset', '.uexp', '.ubulk'):
        old = icon_dir / (row['key'] + suffix)
        if old.is_file():
            baseline.append(dict(path=str(old), bytes=old.stat().st_size,
                                 sha256=hashlib.sha256(old.read_bytes()).hexdigest()))
    row['baseline'] = baseline
    print('GRIP_ICON_INPUT_AUTHORED', row['id'], flush=True)
(P / 'mapping.json').write_text(json.dumps(dict(revision='GripIcons20261101',
    resolution=[1024,1024], items=items, runtime_tested=False), ensure_ascii=False, indent=2), encoding='utf-8')
