"""Author original-surface gill spacing and UV-matched PBR for M07 V07.

Production only: this script does not launch Blender/UE, simulate, render or
run an acceptance check. All original triangles and body coordinates survive.
The positional edit is a small tapered separation of existing original folds,
not replacement leaf geometry. Original source UVs remain unchanged.
"""
import json
from pathlib import Path

import numpy as np

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryOriginalV07'/'gills'
OLD = ROOT/'RecoveryOriginalV06'


def smoothstep(value):
    value = np.clip(value, 0, 1)
    return value*value*(3-2*value)


def texture_sources():
    from PIL import Image, ImageFilter
    from scipy.ndimage import gaussian_filter
    target = OUT/'Textures'
    target.mkdir(parents=True, exist_ok=True)
    source_rgb = np.asarray(Image.open(ROOT/'Textures/M07_basecolor_source.jpg').convert('RGB'), dtype=np.float32)/255
    luma = source_rgb @ np.asarray([.2126, .7152, .0722], dtype=np.float32)
    # Extract only the existing blue-gray branching marks. No new branches,
    # fabricated high-frequency pattern or enlarged source texture is used.
    bluegray = smoothstep((source_rgb[:, :, 2]-source_rgb[:, :, 0]+.01)/.14)
    dark = smoothstep((.67-luma)/.32)
    veins = gaussian_filter(bluegray*dark, .55).astype(np.float32)
    sharp = np.asarray(Image.fromarray(np.rint(source_rgb*255).astype(np.uint8)).filter(
        ImageFilter.UnsharpMask(radius=.7, percent=35, threshold=2)), dtype=np.float32)/255
    sharpened = source_rgb*.7+sharp*.3
    base = np.clip(sharpened*(1-.045*veins[:, :, None]), 0, 1)
    paths = {}

    def write(name, data):
        filename = target/('M07_OriginalGills_V07_'+name+'.png')
        Image.fromarray(np.rint(np.clip(data, 0, 1)*255).astype(np.uint8)).save(filename)
        paths[name] = str(filename)

    write('BaseColor', base)
    rough = np.asarray(Image.open(ROOT/'Textures/M07_roughness.png').convert('L'), dtype=np.float32)/255
    write('Roughness', np.clip(rough*.82+.11+veins*.025, .34, .76))
    metal = np.asarray(Image.open(ROOT/'Textures/M07_metallic.png').convert('L'), dtype=np.float32)/255
    write('Metallic', np.minimum(metal, .035))
    source_normal = np.asarray(Image.open(ROOT/'Textures/M07_normal_source.jpg').convert('RGB'), dtype=np.float32)/255*2-1
    # A bounded relief adjustment follows actual source texture marks. It
    # retains source tangent orientation and resolution; this is not recovery
    # of missing 4K detail. Green stays OpenGL here; UE flips it on import.
    dy, dx = np.gradient(gaussian_filter(veins, .8))
    source_normal[:, :, 0] -= np.clip(dx*1.2, -.07, .07)
    source_normal[:, :, 1] += np.clip(dy*1.2, -.07, .07)
    source_normal /= np.maximum(np.linalg.norm(source_normal, axis=2, keepdims=True), 1e-8)
    write('Normal', source_normal*.5+.5)
    write('VeinMask', veins)
    write('Thickness', np.clip(.21+veins*.43+(1-luma)*.16, .15, .80))
    return paths, {'resolution': list(source_rgb.shape[1::-1]),
        'uv_contract': 'Original GLB UVs unchanged; Blender flips V once during source assembly',
        'basecolor': 'Original blue-gray venation selectively clarified at native 2048 resolution',
        'normal': 'Original tangent normal with source-venation bounded relief, OpenGL green',
        'detail_recovery_or_upscale_claimed': False}


def author():
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import dijkstra
    OUT.mkdir(parents=True, exist_ok=True)
    source = np.load(ROOT/'Authoring/source_mesh.npz')
    regions = np.load(OLD/'regions/source_regions_original_v06.npz')
    original = source['positions'].astype(np.float64)
    faces = source['indices'].reshape(-1, 3)
    labels = regions['face_labels'].copy()
    weld = regions['source_welded_vertex_ids']
    unique, first = np.unique(weld, return_index=True)
    wc = int(weld.max())+1
    centres = np.zeros((wc, 3), np.float64)
    centres[unique] = original[first]
    wf = weld[faces]
    # Semantic part incidence is derived from original triangle IDs. Any
    # body/shared fold seam remains fixed so editing a leaf cannot crack the
    # original shoulder attachment or UV duplicate border.
    incidence = np.zeros(wc, np.uint8)
    for label in range(7):
        ids = np.unique(wf[labels == label])
        incidence[ids] |= 1 << label
    body = (incidence & 1) != 0
    single = np.zeros(wc, np.int8)
    for label in range(1, 7):
        single[incidence == (1 << label)] = label
    delta = np.zeros((wc, 3), np.float64)
    distances = np.full((wc, 7), np.inf, np.float32)
    guides = json.loads((OLD/'gill_reference_guides_source.json').read_text(encoding='utf-8'))
    arrays = {key: regions[key].copy() for key in regions.files}
    panels = []
    scale_cm = 310/float(original[:, 1].max()-original[:, 1].min())
    offsets_cm = [3.0, 1.4, .25]
    side_offsets_cm = [.35, .16, .04]
    max_cloth_cm = [2.5, 1.8, 1.1]
    for label in range(1, 7):
        selected = np.flatnonzero(labels == label)
        panel_welds = np.unique(wf[selected])
        panel_faces = wf[selected]
        edges = np.concatenate([panel_faces[:, [0, 1]], panel_faces[:, [1, 2]], panel_faces[:, [2, 0]]])
        edges.sort(axis=1)
        edges = np.unique(edges[edges[:, 0] != edges[:, 1]], axis=0)
        length = np.linalg.norm(centres[edges[:, 0]]-centres[edges[:, 1]], axis=1)*scale_cm
        graph = coo_matrix((np.r_[length, length],
            (np.r_[edges[:, 0], edges[:, 1]], np.r_[edges[:, 1], edges[:, 0]])), shape=(wc, wc)).tocsr()
        boundary = panel_welds[single[panel_welds] != label]
        root_source_id = int(guides[str(label)]['root_source_vertex_id'])
        # Multi-source original-edge geodesic never bridges neighboring
        # sheets by nearest-position alone, unlike planar proxy rebuilding.
        seeds = np.unique(np.r_[boundary, weld[root_source_id]])
        distance = dijkstra(graph, directed=False, indices=seeds, min_only=True)
        distances[:, label] = distance.astype(np.float32)
        free = smoothstep(distance/7.5)
        free[~np.isfinite(distance)] = 0
        own = single == label
        layer = (label-1) % 3
        sign = 1 if label <= 3 else -1
        # Raw -Z is the back direction of this original GLB. Heights stay
        # untouched. The existing curved shell is lifted by at most 3 cm,
        # with every shared source seam fixed and a smooth 7.5 cm transition.
        delta[own, 2] = -offsets_cm[layer]/scale_cm*free[own]
        delta[own, 0] = sign*side_offsets_cm[layer]/scale_cm*free[own]
        source_ids = np.unique(faces[selected])
        arrays[f'gill_{label:02d}_source_vertex_ids'] = source_ids.astype(np.int32)
        arrays[f'gill_{label:02d}_root_distance_cm'] = distance[weld[source_ids]].astype(np.float32)
        guide = dict(guides[str(label)])
        guide['id'] = f'{label:02d}'
        guide['rest_depth_offset_cm'] = offsets_cm[layer]
        guide['maximum_free_cloth_distance_cm'] = max_cloth_cm[layer]
        guide['source_face_count'] = len(selected)
        guide['source_vertex_count'] = len(source_ids)
        guide['source_face_ids_array'] = f'gill_{label:02d}_source_face_ids'
        guide['source_vertex_ids_array'] = f'gill_{label:02d}_source_vertex_ids'
        guide['root_and_shared_fold_seams_fixed'] = True
        guide['display_triangle_budget'] = 65000
        guide['retained_original_triangles_only'] = True
        panels.append(guide)
        print(f'Authored original gill {label}: {len(selected)} source faces; tapered rest lift {offsets_cm[layer]} cm', flush=True)
    repaired = (original+delta[weld]).astype(np.float32)
    arrays['positions_source_original'] = original.astype(np.float32)
    arrays['positions_source_repaired'] = repaired
    arrays['displacement_source'] = delta[weld].astype(np.float32)
    arrays['uvs_source_unchanged'] = source['uvs'].copy()
    arrays['source_normals'] = source['normals'].copy()
    arrays['original_indices_unchanged'] = source['indices'].copy()
    arrays['fixed_body_welded_vertices'] = np.flatnonzero(body).astype(np.int32)
    arrays['vertex_single_panel_owner'] = single[weld]
    arrays['fold_seam_distance_cm'] = distances[weld]
    filename = OUT/'gill_surface_arrays_original_v07.npz'
    np.savez_compressed(filename, **arrays)
    textures, texture_record = texture_sources()
    recipe = {'revision': 'OriginalV07', 'stage': 'original gill production data and native-resolution PBR authored; untested',
        'original_model': str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'arrays': str(filename), 'positions_array': 'positions_source_repaired',
        'face_labels_array': 'face_labels', 'source_uvs_array': 'uvs_source_unchanged',
        'source_face_count': len(faces), 'body_source_face_count': int((labels == 0).sum()),
        'source_vertex_count': len(original), 'source_triangles_removed': 0,
        'body_positions_modified': False, 'body_face_labels_modified': False,
        'visible_gills_reconstructed': False, 'visible_gill_edit': 'Small original-shell rest-layer spacing; unchanged triangle IDs and UVs',
        'panels': panels, 'textures': textures, 'texture_production': texture_record,
        'material': {'slot_name': 'M07_Gills', 'asset_name': 'M07_Gills_OriginalV07',
            'asset_path': '/Game/Monsters/BlindSupplicantM07/Materials/M07_Gills_OriginalV07',
            'one_shared_original_uv_material': True, 'blend_mode': 'Opaque',
            'shading_model': 'TwoSidedFoliage', 'two_sided': True,
            'thin_organic_backlighting_scale': .34, 'opacity': 1.0,
            'flip_green_on_ue_import': True, 'old_reconstructed_leaf_atlas_reused': False},
        'cloth': {'self_collision_cm': .8, 'collision_min_distance_cm': 1.0,
            'max_distance_policy': 'Per original layer 2.5/1.8/1.1 cm; taper original attachment geodesic',
            'simulation_proxy': 'Retain one original 3D outer shell per leaf; use repaired positions for all queries',
            'hidden_proxy_display_export_excluded': True},
        'integration': {'assembly': 'Use repaired source positions before constructing original parts and hidden proxy BVHs',
            'uv': 'Keep original source UVs, V-flip exactly once; do not use V02 reconstructed-leaf atlas',
            'display': 'Raise each original gill display budget to 65000; keep body budget unchanged',
            'material': 'Fresh OriginalV07 material; never delete expressions in rooted prior materials'},
        'source_cause': {'v06_import': 'import_original_v06.py reused Materials/M07_Gills without rebuilding its texture graph',
            'atlas_history': 'import_fragment_repair_v02.py assigned M07_Gills_V02 atlas for newly lofted leaf UVs',
            'opacity_history': 'Entire prior gill material was translucent at TissueOpacity 0.78',
            'severity': 'Original V06 UV coordinates cannot address the unrelated V02 reconstructed atlas correctly'},
        'tested': False, 'rendered': False, 'ue_imported': False, 'user_accepted': False}
    (OUT/'gill_surface_recipe_v07.json').write_text(json.dumps(recipe, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M07_ORIGINAL_GILL_V07_SOURCE_AND_UV_MATCHED_PBR_AUTHORED', flush=True)


def recipe():
    return json.loads((OUT/'gill_surface_recipe_v07.json').read_text(encoding='utf-8'))


def apply_display(obj, panel):
    """Blender assembly hook, called after reduction/binding; no simulation."""
    obj['original_gill_revision'] = 'OriginalV07'
    obj['original_uv_preserved'] = True
    obj['source_texture_atlas'] = 'Original GLB UV texture, not V02 leaf atlas'
    obj['panel_id'] = int(panel)
    obj['cloth_max_distance_cm'] = [2.5, 1.8, 1.1][(int(panel)-1) % 3]


def blender_material(name='M07_Gills'):
    """Return fresh Blender material with same original-UV source as UE."""
    import bpy
    record = recipe()
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    material.use_backface_culling = False
    shader = next(node for node in material.node_tree.nodes if node.type == 'BSDF_PRINCIPLED')
    for semantic, socket in [('BaseColor', 'Base Color'), ('Roughness', 'Roughness'), ('Metallic', 'Metallic')]:
        tex = material.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = bpy.data.images.load(record['textures'][semantic], check_existing=True)
        tex.image.colorspace_settings.name = 'sRGB' if semantic == 'BaseColor' else 'Non-Color'
        material.node_tree.links.new(tex.outputs['Color'], shader.inputs[socket])
    texture = material.node_tree.nodes.new('ShaderNodeTexImage')
    texture.image = bpy.data.images.load(record['textures']['Normal'], check_existing=True)
    texture.image.colorspace_settings.name = 'Non-Color'
    normal = material.node_tree.nodes.new('ShaderNodeNormalMap')
    material.node_tree.links.new(texture.outputs['Color'], normal.inputs['Color'])
    material.node_tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
    shader.inputs['Alpha'].default_value = 1
    shader.inputs['Transmission Weight'].default_value = 0
    shader.inputs['Subsurface Weight'].default_value = .14
    shader.inputs['Subsurface Radius'].default_value = (.18, .25, .31)
    material['thin_organic_backlighting'] = 'UE uses opaque TwoSidedFoliage; no whole-shell layered translucency'
    return material


if __name__ == '__main__':
    author()
