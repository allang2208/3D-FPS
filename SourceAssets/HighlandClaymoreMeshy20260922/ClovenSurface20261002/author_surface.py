"""Author only the V5 cloven wings; preserve junction, normals and inlay clocks."""
import json
import subprocess
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector, kdtree

P = Path(__file__).resolve().parent
BASE = P.parent
NAME = 'SM_Highland_Guard_Cloven_JunctionV5'
SURFACE = 'M_ClovenWingSurface20261002'
(P / 'Export').mkdir(exist_ok=True)
(P / 'Textures').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.open_mainfile(filepath=str(BASE / 'JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend'))
obj = bpy.data.objects[NAME]
mesh = obj.data
saved_normals = [n.vector[:] for n in mesh.corner_normals]
points = np.array([v.co[:] for v in mesh.vertices], dtype=np.float64)
old_uv = np.array([d.uv[:] for d in mesh.uv_layers[0].data], dtype=np.float64)
original = mesh.uv_layers.get('OriginalAtlas') or mesh.uv_layers.new(name='OriginalAtlas')
original.data.foreach_set('uv', old_uv.astype(np.float32).ravel())

# Surface coordinates follow arc length around the bent horns and the actual
# cross section. UV0 carries the new tangent frame; OriginalAtlas retains UVs
# used to transfer the existing decorative border during texture authoring.
t = np.linspace(0., 1., 1201)
center = np.column_stack((.055 + .234*t - .102*t**3, .008 + .027*t + .105*t*t))
arc = np.r_[0., np.cumsum(np.linalg.norm(np.diff(center, axis=0), axis=1))]
arc /= arc[-1]
tree = kdtree.KDTree(len(t))
for index, p in enumerate(center):
    tree.insert(Vector((float(p[0]), 0., float(p[1]))), index)
tree.balance()
idx = np.array([tree.find(Vector((abs(p[0]), 0., p[2])))[1] for p in points])
dx, dz = .234-.306*t*t, .027+.21*t
length = np.sqrt(dx*dx+dz*dz)
radial = ((np.abs(points[:, 0])-center[idx, 0])*(-dz[idx]) +
          (points[:, 2]-center[idx, 1])*dx[idx]) / length[idx]
sections = json.loads((BASE / 'ClovenGuard20260922/source_guard.json').read_text(encoding='utf-8'))['sections']
stations = np.array([r['x']+.005 for r in sections])
widths = np.array([(r['z'][1]-r['z'][0])/2 for r in sections])
depths = np.array([max(abs(r['y'][0]), abs(r['y'][1])) for r in sections])
source_x = .055+.123*t[idx]
half_width = np.maximum(.0012, np.interp(source_x, stations, widths)*(1+.5*np.sin(np.pi*t[idx])))
half_depth = np.maximum(.001, np.interp(source_x, stations, depths)*(1+.32*(1-.5*t[idx])))
theta = np.arctan2(radial/half_width, points[:, 1]/half_depth)
v = (theta/(2*np.pi)+1.) % 1.
u = .025 + .45*arc[idx] + np.where(points[:, 0] > 0, .5, 0.)
new_uv = old_uv.copy()
wing_mat = bpy.data.materials.new(SURFACE)
wing_mat.use_nodes = True
mesh.materials.append(wing_mat)
wing_index = len(mesh.materials)-1
mesh.calc_loop_triangles()
body_slots = {i for i, mat in enumerate(mesh.materials) if mat and mat.name.split('.')[0] == 'M_HighlandClaymoreSurface'}
triangles, source_triangles, positions, blend, ornament = [], [], [], [], []
for face in mesh.polygons:
    if face.material_index not in body_slots:
        continue
    face_points = points[list(face.vertices)]
    if np.mean(np.abs(face_points[:, 0])) <= .056:
        continue
    face.material_index = wing_index
    loops = list(face.loop_indices)
    verts = np.array([mesh.loops[li].vertex_index for li in loops])
    values = np.column_stack((u[verts], v[verts]))
    if np.ptp(values[:, 1]) > .5:
        values[values[:, 1] < .5, 1] += 1.
    new_uv[loops] = values
    mix = np.clip((np.abs(face_points[:, 0])-.056)/.027, 0., 1.)
    mix = mix*mix*(3-2*mix)
    # Preserve the established ornamental borders, not the stretched wing field.
    rim = np.clip((np.abs(radial[verts])/half_width[verts]-.66)/.20, 0., 1.)
    rim = rim*rim*(3-2*rim)
    for n in range(1, len(loops)-1):
        take = [0, n, n+1]
        triangles.append(values[take])
        source_triangles.append(old_uv[np.array(loops)[take]])
        positions.append(face_points[take])
        blend.append(mix[take])
        ornament.append(rim[take])
mesh.uv_layers[0].data.foreach_set('uv', new_uv.astype(np.float32).ravel())
mesh.uv_layers.active_index = 0
mesh.uv_layers[0].active_render = True
mesh.update()
mesh.normals_split_custom_set(saved_normals)
np.savez_compressed(P / 'surface_transfer.npz', uv=np.array(triangles),
                    old_uv=np.array(source_triangles), points=np.array(positions),
                    blend=np.array(blend), ornament=np.array(ornament))
subprocess.run(['py', '-3.11', str(P / 'author_textures.py')], check=True)

# Store an editable PBR source matching the new UE material. Original slots and
# their UV0 remain untouched on the central seat, gemstone and pulse ribbons.
nt = wing_mat.node_tree
bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
for key, socket in [('BaseColor', 'Base Color'), ('Normal', 'Normal'), ('ORM', None)]:
    image = bpy.data.images.load(str(P / 'Textures' / ('T_ClovenWing_'+key+'.png')))
    image.colorspace_settings.name = 'sRGB' if key == 'BaseColor' else 'Non-Color'
    sample = nt.nodes.new('ShaderNodeTexImage')
    sample.image = image
    uv_node = nt.nodes.new('ShaderNodeUVMap')
    uv_node.uv_map = mesh.uv_layers[0].name
    nt.links.new(uv_node.outputs['UV'], sample.inputs['Vector'])
    if key == 'Normal':
        normal = nt.nodes.new('ShaderNodeNormalMap')
        normal.uv_map = mesh.uv_layers[0].name
        nt.links.new(sample.outputs['Color'], normal.inputs['Color'])
        nt.links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
    elif key == 'ORM':
        channels = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(sample.outputs['Color'], channels.inputs['Color'])
        nt.links.new(channels.outputs['Green'], bsdf.inputs['Roughness'])
        nt.links.new(channels.outputs['Blue'], bsdf.inputs['Metallic'])
    else:
        nt.links.new(sample.outputs['Color'], bsdf.inputs[socket])
    image.pack()
obj['ClovenSurfaceRevision'] = 'ArcUV_PBR_20261002'
obj['surface_scope'] = 'Wing field only; V5 center, gem, custom normals and pulse ribbons preserved'
for other in list(bpy.context.scene.objects):
    if other != obj:
        bpy.data.objects.remove(other, do_unlink=True)
obj.hide_set(False)
obj.hide_render = False
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
fbx = P / 'Export/SM_Highland_Guard_Cloven_ArcSurface20261002.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True, object_types={'MESH'},
                         axis_forward='-Y', axis_up='Z', add_leaf_bones=False,
                         bake_anim=False, mesh_smooth_type='FACE', use_tspace=False)
bpy.ops.wm.save_as_mainfile(filepath=str(P / 'Highland_ClovenGuard_ArcSurface20261002_Editable.blend'))
receipt = {'revision': 'ArcUV_PBR_20261002', 'source': str(BASE / 'JunctionBlendV5_20260927/Highland_ContinuousJunctionV5_Editable.blend'),
           'source_object': NAME, 'fbx': str(fbx), 'new_material': SURFACE,
           'wing_triangles': len(triangles), 'geometry_modified': False,
           'preserved_slots': [m.name for m in mesh.materials if m != wing_mat],
           'uv0': 'Arc-length horn coordinates on wing steel; unchanged elsewhere',
           'uv1': 'Original atlas retained for editing', 'tested': False}
(P / 'author_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('CLOVEN_SURFACE_AUTHORED '+str(fbx), flush=True)
