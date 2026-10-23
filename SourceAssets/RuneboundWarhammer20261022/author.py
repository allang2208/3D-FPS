"""Fit the supplied Meshy hammer to the live warhammer grip; share all motion assets."""
import bpy
import hashlib
import json
import shutil
import struct
from pathlib import Path
import numpy as np
from mathutils import Matrix

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
for folder in ('Original', 'Textures', 'Export'):
    (P / folder).mkdir(exist_ok=True)
src = Path(r'C:\Users\allan\Downloads\Meshy_AI_Runebound_Warhammer_1022125957_texture.glb')
original = P / 'Original' / src.name
if not original.exists():
    shutil.copy2(src, original)
raw = original.read_bytes()
size = struct.unpack_from('<I', raw, 12)[0]
gltf = json.loads(raw[20:20 + size])
buffer_start = 20 + size + 8
material = gltf['materials'][0]
texture_indices = {
    'BaseColor': material['pbrMetallicRoughness']['baseColorTexture']['index'],
    'MetallicRoughness': material['pbrMetallicRoughness']['metallicRoughnessTexture']['index'],
    'Normal': material['normalTexture']['index'],
}
for key, index in texture_indices.items():
    image = gltf['images'][gltf['textures'][index]['source']]
    view = gltf['bufferViews'][image['bufferView']]
    start = buffer_start + view.get('byteOffset', 0)
    (P / 'Textures' / (key + '.jpg')).write_bytes(raw[start:start + view['byteLength']])

# Read the existing accepted grip in the exact WPN_root author frame.
donor = ROOT / 'SourceAssets/SteelWarhammer20261014/SprintDragV1/RigSource/SteelWarhammer_Editable.blend'
bpy.ops.wm.open_mainfile(filepath=str(donor))
bpy.context.preferences.filepaths.save_version = 0
old = bpy.data.objects['SM_SteelWarhammer']
rig = old.parent
to_local = rig.data.bones['WPN_root'].matrix_local.inverted() @ rig.matrix_world.inverted() @ old.matrix_world
old_points = np.array([tuple(to_local @ v.co) for v in old.data.vertices])
base = float(old_points[:, 2].min())
band = old_points[(old_points[:, 2] > .08) & (old_points[:, 2] < .37)]
target_center = (band[:, :2].min(0) + band[:, :2].max(0)) * .5
target_width = np.ptp(band[:, :2], axis=0)
for obj in list(bpy.context.scene.objects):
    bpy.data.objects.remove(obj, do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(original))
hammer = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
hammer.data.transform(hammer.matrix_world)
hammer.matrix_world = Matrix.Identity(4)
points = np.array([tuple(v.co) for v in hammer.data.vertices])
# Blender glTF axes (X,-Z,Y) -> hammer axes (Z,-Y,X), preserving handedness.
rotation = np.array([[0., -1., 0.], [0., 0., -1.], [1., 0., 0.]])
points = points @ rotation.T
scale = 1.15 / np.ptp(points[:, 2])
points *= scale
points[:, 2] += base - points[:, 2].min()
grip = points[(points[:, 2] > .08) & (points[:, 2] < .37)]
center = (grip[:, :2].min(0) + grip[:, :2].max(0)) * .5
points[:, :2] -= center
radial_fit = target_width / np.ptp(grip[:, :2], axis=0)

def fit(p):
    q = p.copy()
    # Keep both accepted hand contacts; smoothly release the fit before the head.
    t = np.clip((q[:, 2] - .40) / .29, 0., 1.)
    t = t * t * (3. - 2. * t)
    q[:, :2] *= radial_fit[None, :] * (1. - t[:, None]) + t[:, None]
    q[:, :2] += target_center
    return q

normals = np.array([tuple(n.vector) for n in hammer.data.corner_normals]) @ rotation.T
jacobian = np.empty((len(points), 3, 3))
for k in range(3):
    shift = np.zeros(3)
    shift[k] = 1.e-5
    jacobian[:, :, k] = (fit(points + shift) - fit(points - shift)) / 2.e-5
loop_indices = np.array([loop.vertex_index for loop in hammer.data.loops])
normal_maps = np.linalg.inv(jacobian).transpose(0, 2, 1)
normals = np.einsum('nij,nj->ni', normal_maps[loop_indices], normals)
normals /= np.maximum(np.linalg.norm(normals, axis=1, keepdims=True), 1.e-10)
hammer.data.vertices.foreach_set('co', fit(points).astype(np.float32).ravel())
hammer.data.update()
hammer.data.normals_split_custom_set(normals.tolist())
hammer.name = 'SM_RuneboundWarhammer'
hammer.data.materials[0].name = 'M_RuneboundWarhammerSurface'
bpy.ops.object.select_all(action='DESELECT')
hammer.select_set(True)
bpy.context.view_layer.objects.active = hammer
bpy.ops.export_scene.fbx(filepath=str(P / 'Export/SM_RuneboundWarhammer.fbx'),
    use_selection=True, object_types={'MESH'}, axis_forward='-Y', axis_up='Z',
    bake_anim=False, mesh_smooth_type='FACE', use_tspace=True, path_mode='STRIP')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'RuneboundWarhammer_Editable.blend'))
hammer.data.calc_loop_triangles()
(P / 'authored.json').write_text(json.dumps({
    'source': str(original), 'source_sha256': hashlib.sha256(raw).hexdigest(),
    'vertices': len(hammer.data.vertices), 'triangles': len(hammer.data.loop_triangles),
    'length_cm': 115, 'grip_radial_fit': radial_fit.tolist(),
    'grip_center_m': target_center.tolist(), 'base_m': base,
    'shared_arms': '/Game/Weapons/SteelWarhammer20261014/SprintDragV1/SK_Warhammer_BareArmsSprintV1',
    'animation_policy': 'Live shared warhammer first/third-person sequences and clearance profile; no sequence copies',
    'tested': False,
}, indent=2), encoding='utf-8')
print('RUNEBBOUND_WARHAMMER_AUTHORED', flush=True)
