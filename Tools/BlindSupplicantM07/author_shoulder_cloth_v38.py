"""Anchor anatomical shoulder/arm surfaces while retaining V36 hanging cloth."""
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
PREVIOUS = ROOT/'WitchClothV36'
OUT = ROOT/'ShoulderClothV38'

def smooth(x):
    x = np.clip(x, 0., 1.)
    return x*x*(3.-2.*x)

def segment_distance(p, start, end):
    axis = end-start
    t = np.clip((p-start)@axis/max(float(axis@axis), 1.e-10), 0., 1.)
    return np.linalg.norm(p-start-t[:, None]*axis, axis=1)

def solve():
    from scipy.spatial import cKDTree
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    OUT.mkdir(parents=True, exist_ok=True)
    source = np.load(ROOT/'MembraneSkinV35/surface_input.npz')
    skin = np.load(ROOT/'MembraneSkinV35/skin_solution.npz')
    previous = np.load(PREVIOUS/'cloth_source.npz')
    ref = json.loads((ROOT/'MembraneSkinV35/rig_input.json').read_text())
    p, labels, names = source['p'], source['labels'], source['names'].tolist()
    arm_indices = [i for i, n in enumerate(names) if n.startswith(('clavicle_', 'upperarm_', 'lowerarm_', 'hand_'))]
    arm_weight = skin['weights'][:, arm_indices].sum(axis=1)
    shoulder_distance = np.full(len(p), np.inf)
    for side in ('l', 'r'):
        clavicle, shoulder, elbow = [np.asarray(ref[n+'_'+side]['head']) for n in ('clavicle', 'upperarm', 'lowerarm')]
        shoulder_distance = np.minimum(shoulder_distance, segment_distance(p, clavicle, shoulder)-19.)
        shoulder_distance = np.minimum(shoulder_distance, segment_distance(p, shoulder, elbow)-20.)
    # Material/leaf membership is not anatomy: leaf 03/06 includes shoulder caps.
    # Retain the original V35 skin for the caps and every arm-driven attachment.
    protected = (labels > 0) & (p[:, 2] > 205.) & ((arm_weight > .15) | (shoulder_distance <= 3.))
    _, first, weld = np.unique(np.round(p/.001).astype(np.int32), axis=0, return_index=True, return_inverse=True)
    fixed = np.zeros(len(first), bool)
    np.logical_or.at(fixed, weld, protected)
    points = p[first]
    edges = np.unique(np.sort(weld[source['e']], axis=1), axis=0)
    edges = edges[edges[:, 0] != edges[:, 1]]
    a, b = edges.T
    length = np.linalg.norm(points[a]-points[b], axis=1)
    graph = coo_matrix((np.r_[length, length], (np.r_[a, b], np.r_[b, a])), shape=(len(points), len(points))).tocsr()
    # A fixed margin and surface-distance release prevent a hard shoulder hinge.
    distance = dijkstra(graph, directed=False, indices=np.flatnonzero(fixed), min_only=True)
    release = smooth((distance[weld]-5.)/25.)
    alpha = np.rint(previous['alpha']*release).astype(np.uint8)
    manifest = json.loads((PREVIOUS/'cloth_manifest_v36.json').read_text())
    nearest = cKDTree(p[protected])
    for panel in manifest['panels']:
        proxy = np.asarray(panel['vertices_cm'])*[1., -1., 1.]
        d = nearest.query(proxy)[0]
        travel = np.asarray(panel['max_distance_cm'])*smooth((d-6.)/24.)
        panel['max_distance_cm'] = travel.tolist()
        panel['fixed_vertices'] = int((travel == 0).sum())
    np.savez_compressed(OUT/'shoulder_capture_v38.npz', alpha=alpha, offsets=source['offsets'])
    manifest.update(revision='ShoulderClothV38', display_source=str(OUT/'M07_ShoulderClothV38.blend'),
        previous_display_source=str(PREVIOUS/'M07_WitchClothV36.blend'),
        shoulder_original_skin_vertices=int(protected.sum()), shoulder_fixed_margin_cm=5., shoulder_release_cm=25.,
        newly_fixed_display_vertices=int(((previous['alpha'] > 0) & (alpha == 0)).sum()),
        display_blend_vertex_count=int((alpha > 0).sum()),
        physical_fixed_vertices=sum(x['fixed_vertices'] for x in manifest['panels']),
        visible_geometry_modified=False, skin_weights_modified=False, uv_modified=False,
        material_slots_modified=False, runtime_tested=False, rendered=False)
    (OUT/'cloth_manifest_v38.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    print('M07_V38_SHOULDER_FIELD_AUTHORED '+json.dumps({k:manifest[k] for k in (
        'shoulder_original_skin_vertices','newly_fixed_display_vertices','display_blend_vertex_count','physical_fixed_vertices')}), flush=True)

def author():
    import bpy
    from mathutils import Matrix
    sys.path.insert(0, str(Path(__file__).parent))
    import author_original_surfaces_v08 as surfaces
    subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe', str(Path(__file__).resolve()), '--solve'], check=True)
    data = np.load(OUT/'shoulder_capture_v38.npz')
    bpy.ops.wm.open_mainfile(filepath=str(PREVIOUS/'M07_WitchClothV36.blend'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    for bone in rig.pose.bones:
        bone.matrix_basis = Matrix.Identity(4)
    display = [bpy.data.objects['M07_OriginalBody_Display']]+[bpy.data.objects[f'M07_OriginalGill_{i:02d}_Display'] for i in range(1, 7)]
    for label, obj in enumerate(display):
        mesh = obj.data
        color = mesh.color_attributes.active_color
        values = np.empty((len(mesh.loops), 4), np.float32)
        color.data.foreach_get('color', values.ravel())
        vertices = np.empty(len(mesh.loops), np.int32)
        mesh.loops.foreach_get('vertex_index', vertices)
        start = int(data['offsets'][label])
        values[:, 3] = data['alpha'][start+vertices]/255.
        color.data.foreach_set('color', values.ravel())
        obj['membrane_capture_revision'] = 'V38 protected shoulder and upper-arm skin, graded cloth release'
    proxy = bpy.data.objects['M07_ContinuousDrapesV36']
    surfaces.export(OUT/'SK_M07_ClothProxyV38.fbx', rig, [proxy])
    surfaces.export(OUT/'SK_M07_Display_ShoulderV38.fbx', rig, display)
    proxy.hide_render = True
    proxy.hide_set(True)
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M07_ShoulderClothV38.blend'), compress=True)
    print('M07_V38_SHOULDER_SOURCE_EXPORTED', flush=True)

if __name__ == '__main__':
    if '--solve' in sys.argv:
        solve()
    else:
        author()
