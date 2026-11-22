"""Fit the selected Meshy sword to the existing WPN_root grip frame."""
import json
import os
import shutil
import struct
from pathlib import Path

import bpy
from mathutils import Matrix

project = Path(__file__).resolve().parent
for folder in ('Original', 'Textures', 'Export'):
    (project / folder).mkdir(exist_ok=True)
original = project / 'Original/Meshy_AI_Silver_Longsword_1120084541_texture.glb'
if not original.exists():
    source = os.environ.get('FPSGAME_FORGED_SWORD_GLB')
    if not source:
        raise FileNotFoundError(f'Place the selected model at {original} or set FPSGAME_FORGED_SWORD_GLB')
    shutil.copy2(Path(source), original)

data = original.read_bytes()
json_size, = struct.unpack_from('<I', data, 12)
gltf = json.loads(data[20:20 + json_size])
payload = 28 + json_size
material = gltf['materials'][0]
pbr = material['pbrMetallicRoughness']
channels = {'BaseColor': pbr['baseColorTexture'], 'MetallicRoughness': pbr['metallicRoughnessTexture'],
            'Normal': material['normalTexture']}
for channel, texture in channels.items():
    image = gltf['images'][gltf['textures'][texture['index']]['source']]
    view = gltf['bufferViews'][image['bufferView']]
    start = payload + view.get('byteOffset', 0)
    (project / 'Textures' / f'ForgedSteelGreatsword_{channel}.jpg').write_bytes(data[start:start + view['byteLength']])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.ops.import_scene.gltf(filepath=str(original))
sword, = (obj for obj in bpy.context.scene.objects if obj.type == 'MESH')
# The original grip spans these two rings. Uniform fitting preserves the blade-to-hilt ratio.
grip_top, grip_bottom = -0.548, -0.837
scale = 0.177 / (grip_top - grip_bottom)
def fitted_z(height):
    return (height - grip_top) * scale - 0.05

translation = Matrix.Translation((0.00045 * scale, -0.0005 * scale, fitted_z(0)))
sword.data.transform(translation @ Matrix.Scale(scale, 4) @ sword.matrix_world)
sword.matrix_world = Matrix.Identity(4)
sword.name = 'SM_ForgedSteelGreatsword_Complete_V1'
sword.data.name = sword.name
sword.data.materials[0].name = 'M_ForgedSteelGreatsword_Surface_V1'
heights = [v.co.z * 100 for v in sword.data.vertices]
cuts = {'blade_guard': -0.406, 'guard_grip': grip_top, 'grip_pommel': grip_bottom}
fit = {'definition': 'ue_forged_steel_greatsword', 'source_glb': original.relative_to(project).as_posix(),
       'uniform_scale': scale, 'blade_tip_cm': max(heights), 'pommel_end_cm': min(heights),
       'cuts_z_cm': {k: fitted_z(v) * 100 for k, v in cuts.items()}}
(project / 'fit_manifest.json').write_text(json.dumps(fit, indent=2) + '\n', encoding='utf-8')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(project / 'ForgedSteelGreatsword_Fitted_Editable.blend'))
