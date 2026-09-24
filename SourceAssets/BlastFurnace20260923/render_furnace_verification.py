"""Verification renders for the blast furnace: clay pass and textured pass.

    & blender.exe --background SourceAssets/BlastFurnace20260923/Authored/BlastFurnace.blend \
        --python SourceAssets/BlastFurnace20260923/render_furnace_verification.py

Every view is rendered twice from the same camera and lighting:

* ``*_clay.png``    — a view-layer ``material_override`` replaces all seven
                      materials with one matte clay shader, so silhouette,
                      proportions, hard edges and the boolean cut openings are
                      judged without texture help;
* ``*_textured.png``— the authored PBR materials, same camera.

Blender only, headless, CPU. Nothing touches UE and no PIE is started. These
are the images the user asked for; the final call on the asset is still theirs.
"""
import json
from pathlib import Path

import bpy
from mathutils import Vector

HERE = Path(bpy.data.filepath).resolve().parent
OUT = HERE / 'Verify'
OUT.mkdir(parents=True, exist_ok=True)

scene = bpy.context.scene
view_layer = bpy.context.view_layer
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 56
scene.cycles.use_denoising = True
scene.render.resolution_x = 1000
scene.render.resolution_y = 1000
scene.render.image_settings.file_format = 'PNG'
available = [v.identifier for v in scene.view_settings.bl_rna.properties['view_transform'].enum_items]
for preferred in ('AgX', 'Filmic', 'Standard'):
    if preferred in available:
        scene.view_settings.view_transform = preferred
        break
scene.view_settings.exposure = -1.1

# --- clay override material -------------------------------------------
clay = bpy.data.materials.new('VerifyClay')
clay.use_nodes = True
clay_bsdf = next(n for n in clay.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
# Mid grey rather than white: pure white clips the top faces and hides the
# very banding the clay pass is meant to reveal.
clay_bsdf.inputs['Base Color'].default_value = (0.58, 0.575, 0.565, 1.0)
clay_bsdf.inputs['Roughness'].default_value = 0.62
clay_bsdf.inputs['Metallic'].default_value = 0.0
clay_bsdf.inputs['Specular IOR Level'].default_value = 0.30

# --- lighting ----------------------------------------------------------
world = bpy.data.worlds.new('VerifyWorld')
scene.world = world
world.use_nodes = True
background = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
background.inputs['Color'].default_value = (0.055, 0.06, 0.07, 1)
background.inputs['Strength'].default_value = 1.0


def area_light(name, location, energy, size, color=(1, 1, 1)):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy
    data.size = size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (Vector((0, 0, 1.1)) - Vector(location)).to_track_quat('-Z', 'Y').to_euler()
    return obj


area_light('Key', (3.6, 3.0, 4.2), 900, 3.0, (1.0, 0.96, 0.90))
area_light('Fill', (-3.4, 2.6, 1.8), 320, 3.5, (0.85, 0.90, 1.0))
area_light('Rim', (-1.6, -3.8, 3.0), 480, 2.5, (1.0, 0.92, 0.82))

ground = bpy.data.meshes.new('Ground')
ground.from_pydata([(-14, -14, 0), (14, -14, 0), (14, 14, 0), (-14, 14, 0)], [], [(0, 1, 2, 3)])
ground.update()
ground_obj = bpy.data.objects.new('Ground', ground)
bpy.context.collection.objects.link(ground_obj)
ground_mat = bpy.data.materials.new('VerifyGround')
ground_mat.use_nodes = True
ground_bsdf = next(n for n in ground_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
ground_bsdf.inputs['Base Color'].default_value = (0.10, 0.10, 0.105, 1)
ground_bsdf.inputs['Roughness'].default_value = 0.85
ground.materials.append(ground_mat)

camera_data = bpy.data.cameras.new('VerifyCamera')
camera = bpy.data.objects.new('VerifyCamera', camera_data)
bpy.context.collection.objects.link(camera)
scene.camera = camera

TARGET = Vector((0.0, 0.0, 1.10))
SHOTS = [
    ('01_front_tap_face', Vector((4.55, 0.25, 1.60)), TARGET, 62),
    ('02_three_quarter', Vector((3.25, 3.05, 1.95)), TARGET, 62),
    ('03_blast_side', Vector((0.30, 4.35, 1.70)), TARGET, 62),
    ('04_back_ash_door', Vector((-3.45, -3.05, 1.85)), TARGET, 62),
    ('05_mouth_from_above', Vector((1.45, 1.30, 4.30)), Vector((0.0, 0.0, 1.80)), 62),
    ('06_forehearth_closeup', Vector((2.05, 1.30, 0.80)), Vector((0.28, 0.0, 0.34)), 85),
]

manifest = {'views': [], 'samples': scene.cycles.samples, 'resolution': 1000,
            'clay_base_color': [0.58, 0.575, 0.565], 'rendered': True, 'runtime_tested': False}

for name, position, target, lens in SHOTS:
    camera_data.lens = lens
    camera.location = position
    camera.rotation_euler = (target - position).to_track_quat('-Z', 'Y').to_euler()
    for pass_name, override in (('clay', clay), ('textured', None)):
        view_layer.material_override = override
        scene.render.filepath = str(OUT / ('%s_%s.png' % (name, pass_name)))
        bpy.ops.render.render(write_still=True)
        print('FURNACE_VERIFY_SHOT %s %s' % (name, pass_name), flush=True)
    manifest['views'].append({'view': name, 'lens_mm': lens,
                              'camera_m': [round(c, 3) for c in position],
                              'target_m': [round(c, 3) for c in target],
                              'files': ['%s_clay.png' % name, '%s_textured.png' % name]})

view_layer.material_override = None
(OUT / 'verify-render.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('FURNACE_VERIFY_DONE ' + str(OUT), flush=True)
