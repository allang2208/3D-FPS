"""Author the user-selected GLB against the live Zhenyue rigid-length reference."""
import bpy, json, shutil, struct
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

P = Path(__file__).resolve().parent
ROOT = P.parents[1]
SOURCE = Path(r'C:\Users\allan\Downloads\Meshy_AI_Crimson_Crescent_Blad_1017171549_texture.glb')
REFERENCE = ROOT / 'SourceAssets/XuanChiZhenYue20261004/BladeV3/XuanChi_BladeV3_Editable.blend'
for folder in ['Original', 'Textures', 'Export']:
    (P / folder).mkdir(parents=True, exist_ok=True)
original = P / 'Original' / SOURCE.name
if not original.exists():
    shutil.copy2(SOURCE, original)

# Read the actual authored meshes used by the live BladeV3 catalog. The flexible
# tassel is excluded from weapon length; it is not a blade or a rigid handle.
bpy.ops.wm.open_mainfile(filepath=str(REFERENCE))
names = ['SM_XuanChi_Blade_V3', 'SM_XuanChi_Guard_V3', 'SM_XuanChi_Grip', 'SM_XuanChi_Pommel']
reference_points = [bpy.data.objects[n].matrix_world @ v.co for n in names for v in bpy.data.objects[n].data.vertices]
ref_min = min(v.z for v in reference_points)
ref_max = max(v.z for v in reference_points)
grip = bpy.data.objects['SM_XuanChi_Grip']
grip_points = np.array([tuple(grip.matrix_world @ v.co) for v in grip.data.vertices])
reference = {'source': str(REFERENCE), 'meshes': names, 'rigid_min_z_cm': ref_min*100,
             'rigid_max_z_cm': ref_max*100, 'rigid_length_cm': (ref_max-ref_min)*100,
             'grip_min_cm': (grip_points.min(axis=0)*100).tolist(), 'grip_max_cm': (grip_points.max(axis=0)*100).tolist(),
             'tassel_included': False}

raw = original.read_bytes()
json_length = struct.unpack_from('<I', raw, 12)[0]
gltf = json.loads(raw[20:20+json_length])
binary_start = 20+json_length+8
material = gltf['materials'][0]
pbr = material['pbrMetallicRoughness']
for channel, texture in [('BaseColor', pbr['baseColorTexture']), ('MetallicRoughness', pbr['metallicRoughnessTexture']), ('Normal', material['normalTexture'])]:
    im = gltf['images'][gltf['textures'][texture['index']]['source']]
    view = gltf['bufferViews'][im['bufferView']]
    offset = binary_start + view.get('byteOffset', 0)
    (P/'Textures'/('Zhanmadao_'+channel+'.jpg')).write_bytes(raw[offset:offset+view['byteLength']])

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.context.scene.unit_settings.system = 'METRIC'
bpy.context.scene.unit_settings.scale_length = 1
bpy.ops.import_scene.gltf(filepath=str(original))
obj = next(o for o in bpy.context.scene.objects if o.type == 'MESH')
mesh = obj.data
source_points = np.array([tuple(obj.matrix_world @ v.co) for v in mesh.vertices])
min_x, max_x = float(source_points[:,0].min()), float(source_points[:,0].max())
scale = (ref_max-ref_min)/(max_x-min_x)
# glTF X is blade length, negative X is the tip. Blender has converted the
# glTF width Y into Z and thickness Z into -Y. This is a proper rotation.
rotation = Matrix(((0,0,-1),(0,-1,0),(-1,0,0)))
old_normals = [rotation @ (obj.matrix_world.to_3x3() @ n.vector) for n in mesh.corner_normals]
for vertex, co in zip(mesh.vertices, source_points):
    v = rotation @ Vector(co)
    vertex.co = Vector(((v.x-.0025)*scale, (v.y+.0004)*scale, ref_max-(co[0]-min_x)*scale))
obj.matrix_world = Matrix.Identity(4)
obj.name = 'SM_Zhanmadao_Complete_V1'
mesh.name = obj.name
mesh.update()
for poly in mesh.polygons:
    poly.use_smooth = True
mesh.normals_split_custom_set([tuple(n.normalized()) for n in old_normals])
mesh.materials[0].name = 'M_Zhanmadao_Surface_V1'

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(P/'Zhanmadao_Fitted_Editable.blend'))
result = {'definition':'ue_zhanmadao', 'reference':reference, 'source_glb':str(original),
          'source_length_m':max_x-min_x, 'uniform_scale':scale,
          'source_axis':'glTF -X tip / +X pommel', 'target_axis':'+Z tip / -Z pommel / X width / Y thickness',
          'blade_tip_cm':ref_max*100, 'pommel_end_cm':ref_min*100,
          'source_cuts_x':{'blade_guard':.390, 'guard_grip':.490, 'grip_pommel':.886},
          'cuts_z_cm':{k:(ref_max-(x-min_x)*scale)*100 for k,x in [('blade_guard',.390),('guard_grip',.490),('grip_pommel',.886)]},
          'source_triangles':sum(len(f.vertices)-2 for f in mesh.polygons),
          'game_tested':False, 'visual_accepted':False}
(P/'fit_manifest.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('ZHANMADAO_FITTED '+json.dumps(result,ensure_ascii=False),flush=True)
