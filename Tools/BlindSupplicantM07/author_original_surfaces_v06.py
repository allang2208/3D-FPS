"""Keep original M07 display surfaces; author skin and hidden cloth sources.

The display geometry always descends from original triangles. Simulation uses
an open decimated side of each original shell in 3D, never a flat Delaunay loft.
Production only; no playback, simulation, rendering or runtime testing.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree
from mathutils.bvhtree import BVHTree

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryOriginalV06'


def make_mesh(name, points, faces, mat, collection, uv=None, normals=None, ids=None, face_ids=None):
    mesh = bpy.data.meshes.new(name)
    mesh.vertices.add(len(points))
    mesh.vertices.foreach_set('co', np.asarray(points, dtype=np.float32).ravel())
    mesh.loops.add(faces.size)
    mesh.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
    mesh.polygons.add(len(faces))
    mesh.polygons.foreach_set('loop_start', np.arange(len(faces), dtype=np.int32)*3)
    mesh.polygons.foreach_set('loop_total', np.full(len(faces), 3, dtype=np.int32))
    mesh.polygons.foreach_set('use_smooth', np.ones(len(faces), dtype=bool))
    mesh.update()
    if uv is not None:
        mesh.uv_layers.new(name='UVMap').data.foreach_set('uv', uv[faces.ravel()].astype(np.float32).ravel())
    if normals is not None:
        mesh.normals_split_custom_set_from_vertices(normals.tolist())
    if ids is not None:
        mesh.attributes.new(name='source_vertex_id', type='INT', domain='POINT').data.foreach_set('value', ids.astype(np.int32))
    if face_ids is not None:
        mesh.attributes.new(name='source_face_id', type='INT', domain='FACE').data.foreach_set('value', face_ids.astype(np.int32))
    mesh.materials.append(mat)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj['visible_surface_source'] = 'Original Meshy GLB'
    return obj


def assign(obj, bone_names, indices, weights):
    obj.vertex_groups.clear()
    groups = [obj.vertex_groups.new(name=n) for n in bone_names]
    q = np.rint(weights*255).astype(np.int16)
    q[:, 0] += 255-q.sum(axis=1)
    vertices = np.repeat(np.arange(len(indices)), indices.shape[1])
    bones = indices.ravel()
    values = q.ravel()
    positive = values > 0
    keys = bones[positive].astype(np.int64)*256+values[positive]
    vertices = vertices[positive]
    order = np.argsort(keys)
    keys, vertices = keys[order], vertices[order]
    split = np.r_[0, np.flatnonzero(np.diff(keys))+1, len(keys)]
    for a, b in zip(split[:-1], split[1:]):
        key = int(keys[a])
        groups[key//256].add(vertices[a:b].tolist(), (key % 256)/255, 'REPLACE')


def bind(obj, rig):
    obj.parent = rig
    obj.matrix_parent_inverse = Matrix.Identity(4)
    obj.matrix_basis = Matrix.Identity(4)
    mod = obj.modifiers.new('M07_OriginalSkin', 'ARMATURE')
    mod.object = rig


def reduce_copy(original, name, budget, collection):
    obj = original.copy()
    obj.data = original.data.copy()
    obj.name = name
    collection.objects.link(obj)
    for mod in list(obj.modifiers):
        obj.modifiers.remove(mod)
    bpy.context.view_layer.objects.active = obj
    if len(obj.data.polygons) > budget:
        modifier = obj.modifiers.new('OriginalSurfaceReduction', 'DECIMATE')
        modifier.decimate_type = 'COLLAPSE'
        modifier.ratio = budget/len(obj.data.polygons)
        modifier.use_collapse_triangulate = True
        modifier.delimit = {'UV', 'MATERIAL', 'SEAM'}
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj['production_reduction'] = 'Original surface edge collapse with retained UV/material delimiters; no replacement anatomy'
    return obj


def material(name, membrane=False):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    result.use_backface_culling = False
    shader = next((n for n in result.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if shader is None:
        shader = result.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        output = next((n for n in result.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if output is None:
            output = result.node_tree.nodes.new('ShaderNodeOutputMaterial')
        result.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
    for filename, socket, is_data in [('M07_basecolor_source.jpg', 'Base Color', False),
                                       ('M07_roughness.png', 'Roughness', True),
                                       ('M07_metallic.png', 'Metallic', True)]:
        node = result.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = bpy.data.images.load(str(ROOT/'Textures'/filename), check_existing=True)
        if is_data:
            node.image.colorspace_settings.name = 'Non-Color'
        result.node_tree.links.new(node.outputs['Color'], shader.inputs[socket])
    n = result.node_tree.nodes.new('ShaderNodeTexImage')
    n.image = bpy.data.images.load(str(ROOT/'Textures/M07_normal_source.jpg'), check_existing=True)
    n.image.colorspace_settings.name = 'Non-Color'
    normal = result.node_tree.nodes.new('ShaderNodeNormalMap')
    result.node_tree.links.new(n.outputs['Color'], normal.inputs['Color'])
    result.node_tree.links.new(normal.outputs['Normal'], shader.inputs['Normal'])
    if membrane:
        shader.inputs['Alpha'].default_value = .88
        shader.inputs['Transmission Weight'].default_value = .12
        result.surface_render_method = 'DITHERED'
    return result


def export(path, rig, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [rig, *objects]:
        obj.hide_set(False)
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True, object_types={'ARMATURE', 'MESH'},
        add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
        bake_anim=False, axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS', use_mesh_modifiers=True, path_mode='COPY', embed_textures=False)


def author(regions_path, rig_path):
    source = np.load(ROOT/'Authoring/source_mesh.npz')
    labels = np.load(regions_path)['face_labels']
    skin = np.load(OUT/'original_skin_weights_v06.npz')
    skin_record = json.loads((OUT/'original_skin_weights_v06.json').read_text(encoding='utf-8'))
    bone_names = skin_record['bone_names']
    raw = source['positions']
    scale = 310/float(raw[:, 1].max()-raw[:, 1].min())
    points = np.c_[raw[:, 0], -raw[:, 2], raw[:, 1]-raw[:, 1].min()]*scale
    normals = source['normals']
    normals = np.c_[normals[:, 0], -normals[:, 2], normals[:, 1]]
    uv = source['uvs'].copy()
    uv[:, 1] = 1-uv[:, 1]
    faces = source['indices'].reshape(-1, 3)
    bpy.ops.wm.open_mainfile(filepath=str(rig_path))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    rig.name = 'Armature'
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    for pb in rig.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = .01
    scene.frame_set(0)

    def collection(name):
        result = bpy.data.collections.new(name)
        scene.collection.children.link(result)
        return result

    high_collection = collection('M07_OriginalSplitHighMaster')
    display_collection = collection('M07_OriginalGameDisplay')
    proxy_collection = collection('M07_OriginalHiddenCloth')
    body_material, gill_material = material('M07_Body'), material('M07_Gills', True)
    simulation_material = bpy.data.materials.new('M07_GillSimulation')
    high, display, proxies, panels = [], [], [], []
    for label in range(7):
        source_faces = np.flatnonzero(labels == label)
        ff = faces[source_faces]
        used, remapped = np.unique(ff.ravel(), return_inverse=True)
        local_faces = remapped.reshape(-1, 3)
        part = make_mesh('M07_OriginalBody_High' if label == 0 else f'M07_OriginalGill_{label:02d}_High',
            points[used], local_faces, body_material if label == 0 else gill_material,
            high_collection, uv[used], normals[used], used, source_faces)
        assign(part, bone_names, skin['bone_indices'][used], skin['bone_weights'][used])
        bind(part, rig)
        high.append(part)
        game = reduce_copy(part, 'M07_OriginalBody_Display' if label == 0 else f'M07_OriginalGill_{label:02d}_Display',
                           160000 if label == 0 else 26000, display_collection)
        bind(game, rig)
        game['panel_id'] = label
        display.append(game)
        if not label:
            continue

        # Open one side of THIS original leaf using its own shell normals.
        # The original 3D triangle adjacency remains the simulation topology.
        face_normals = normals[used][local_faces].mean(axis=1)
        outside = face_normals[:, 1] > .15
        outer_faces = local_faces[outside]
        outer_used, outer_remap = np.unique(outer_faces.ravel(), return_inverse=True)
        proxy = make_mesh(f'M07_OriginalGill_{label:02d}_SimulationProxy', points[used[outer_used]],
            outer_remap.reshape(-1, 3), simulation_material, proxy_collection)
        bm = bmesh.new()
        bm.from_mesh(proxy.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.025)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=.005)
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(proxy.data)
        bm.free()
        proxy = reduce_copy(proxy, f'M07_OriginalGill_{label:02d}_Simulation', 1100, proxy_collection)
        # Fused source folds can produce nonmanifold edges after reduction.
        # Remove only redundant low-area faces from the HIDDEN simulation
        # sheet; the original display surface is never involved in this edit.
        bm = bmesh.new()
        bm.from_mesh(proxy.data)
        redundant = set()
        seen = {}
        for face in bm.faces:
            key = tuple(sorted(v.index for v in face.verts))
            if key in seen:
                redundant.add(face)
            else:
                seen[key] = face
        for edge in bm.edges:
            linked = [f for f in edge.link_faces if f not in redundant]
            if len(linked) > 2:
                redundant.update(sorted(linked, key=lambda f: f.calc_area())[:-2])
        if redundant:
            bmesh.ops.delete(bm, geom=list(redundant), context='FACES')
        loose = [v for v in bm.verts if not v.link_faces]
        if loose:
            bmesh.ops.delete(bm, geom=loose, context='VERTS')
        bm.to_mesh(proxy.data)
        bm.free()
        # Remove the unbound staging sheet, which must never reach export.
        staging = bpy.data.objects.get(f'M07_OriginalGill_{label:02d}_SimulationProxy')
        if staging:
            bpy.data.objects.remove(staging, do_unlink=True)
        proxy.data.update()
        bvh = BVHTree.FromPolygons(points[used].tolist(), local_faces.tolist(), all_triangles=True)
        tree = KDTree(len(used))
        for j, source_id in enumerate(used):
            tree.insert(Vector(points[source_id]), j)
        tree.balance()
        nearest = []
        for vertex in proxy.data.vertices:
            _, local_id, _ = tree.find(vertex.co)
            source_id = used[local_id]
            nearest.append(source_id)
            normal = Vector(normals[source_id])
            hit, hit_normal, _, distance = bvh.ray_cast(vertex.co-normal*.03, -normal, 5.0)
            if hit is not None and distance > .04 and hit_normal.dot(normal) < -.2:
                vertex.co = (vertex.co+hit)*.5
        nearest = np.asarray(nearest, dtype=np.int32)
        assign(proxy, bone_names, skin['bone_indices'][nearest], skin['bone_weights'][nearest])
        bind(proxy, rig)
        geodesic = skin['attachment_distance_cm'][nearest, label]
        free = np.clip((geodesic-2.0)/35, 0, 1)
        free = free*free*(3-2*free)
        max_distance = 8.0*free
        pin = 1-free
        group = proxy.vertex_groups.new(name='M07_Pin')
        for j, weight in enumerate(pin):
            if weight > 0:
                group.add([j], float(weight), 'REPLACE')
        cloth_modifier = proxy.modifiers.new('M07_ClothAuthoring_Disabled', 'CLOTH')
        cloth_modifier.settings.vertex_group_mass = 'M07_Pin'
        cloth_modifier.settings.mass = .22
        cloth_modifier.settings.quality = 6
        cloth_modifier.settings.air_damping = 3
        cloth_modifier.settings.tension_stiffness = 18
        cloth_modifier.settings.compression_stiffness = 18
        cloth_modifier.settings.shear_stiffness = 12
        cloth_modifier.settings.bending_stiffness = .65
        cloth_modifier.collision_settings.use_collision = True
        cloth_modifier.collision_settings.distance_min = 1.2
        cloth_modifier.collision_settings.use_self_collision = True
        cloth_modifier.collision_settings.self_distance_min = 1.0
        cloth_modifier.show_viewport = False
        cloth_modifier.show_render = False
        # Native UE uses skin plus simulated displacement. The optional Blender
        # authoring view uses EITHER display skin OR complete proxy deformation,
        # preventing the two full skeletal transforms being applied twice.
        surface = game.modifiers.new('M07_ProxyAuthoring_Disabled', 'SURFACE_DEFORM')
        surface.target = proxy
        bpy.context.view_layer.objects.active = game
        proxy.hide_set(False)
        bpy.ops.object.surfacedeform_bind(modifier=surface.name)
        game['surface_deform_bound'] = bool(surface.is_bound)
        surface.show_viewport = False
        surface.show_render = False
        game['cloth_authoring_instructions'] = 'To author cloth, disable display OriginalSkin and enable ProxyAuthoring; enable proxy ClothAuthoring. Default view uses OriginalSkin alone.'
        position = np.asarray([v.co[:] for v in proxy.data.vertices])
        proxy['panel_id'] = label
        proxy['display_export_excluded'] = True
        proxy['topology_source'] = 'Original leaf outer shell in 3D, locally paired midpoints and edge collapse'
        proxy.hide_render = True
        proxy.hide_set(True)
        proxies.append(proxy)
        panel = {'id': f'{label:02d}', 'vertices_cm': np.c_[position[:, 0], -position[:, 1], position[:, 2]].tolist(),
            'max_distance_cm': max_distance.tolist(), 'pin_weights': pin.tolist(),
            'vertex_count': len(position), 'triangle_count': len(proxy.data.polygons),
            'source_region': label, 'source_original_vertices': nearest.tolist(),
            'root_world_m': (position[np.argmin(geodesic)]/100).tolist(),
            'tip_world_m': (position[np.argmax(geodesic)]/100).tolist()}
        panels.append(panel)
        print(f'Authored original panel {label}: high={len(part.data.polygons)}, game={len(game.data.polygons)}, proxy={len(position)}', flush=True)

    # Shared collision source is derived from the same original-fitted bones.
    collision = []
    for a, b, radius in [('pelvis', 'spine_02', 18), ('spine_02', 'spine_05', 19), ('neck_01', 'head', 11)]+[
        (a+'_'+s, b+'_'+s, r) for s in ('l', 'r') for a, b, r in (
            ('upperarm', 'lowerarm', 7), ('lowerarm', 'hand', 6), ('thigh', 'calf', 10), ('calf', 'foot', 7))]:
        bone = rig.data.bones[a]
        inv = bone.matrix_local.inverted()
        p, q = inv@bone.head_local, inv@rig.data.bones[b].head_local
        collision.append({'bone': a, 'a_cm': [p.x, -p.y, p.z], 'b_cm': [q.x, -q.y, q.z], 'radius_cm': radius})
    manifest = {'panels': panels, 'collision_capsules': collision,
        'coordinate_frame': 'FBX/UE reference mesh centimeters; Blender Y reflected',
        'method': 'Original leaf 3D shell topology, local opposite-shell midpoint, hidden reduced proxy; original geodesic pinned seam',
        'inter_panel_collision': True, 'tested': False}
    (OUT/'cloth_ue_manifest_original_v06.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    export(OUT/'SK_M07_Display_OriginalV06.fbx', rig, display)
    export(OUT/'SK_M07_ClothBuildSource_OriginalV06.fbx', rig, [*display, *proxies])
    for obj in high:
        obj.hide_set(True)
        obj.hide_render = True
    for obj in proxies:
        obj.hide_set(True)
        obj.hide_render = True
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    rig.data.pose_position = 'POSE'
    motion_manifest_path = OUT/'rig_motion/motion_manifest.json'
    motion_record = json.loads(motion_manifest_path.read_text(encoding='utf-8'))
    idle = bpy.data.actions.get(motion_record['clips']['Idle']['action'])
    if idle is not None:
        rig.animation_data_create()
        rig.animation_data.action = idle
        if idle.slots:
            rig.animation_data.action_slot = idle.slots[0]
    scene.render.fps = motion_record['fps']
    scene.frame_start = 1
    scene.frame_end = motion_record['clips']['Idle']['frames']
    scene.frame_set(0)
    scene['m07_original_geometry_only'] = True
    scene['m07_tested'] = False
    destination = OUT/'M07_Original_Skinned_Master_V06.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(destination), compress=True)
    record = {'revision': 'OriginalV06', 'stage': 'original geometry skin and cloth construction source authored; untested',
        'original_source': str(ROOT/'Original/Meshy_AI_Veilwing_07_1001123357_texture.glb'),
        'saved_blend': str(destination), 'source_high_master_triangles': len(faces),
        'all_original_faces_retained_in_high_master': True, 'donor_body_geometry_used': False,
        'visible_gills_reconstructed': False, 'display_parts': [o.name for o in display],
        'display_triangles': sum(len(o.data.polygons) for o in display),
        'game_surface_reduced_from_original': True, 'bone_count': len(rig.data.bones),
        'blender_cloth_modifier_configured': True,
        'blender_surface_deform_bindings': sum(bool(o.get('surface_deform_bound', False)) for o in display),
        'blender_cloth_simulation_played': False, 'blender_cloth_view_enabled_by_default': False,
        'gill_proxies': [{'id': p['id'], 'vertices': p['vertex_count'], 'triangles': p['triangle_count']} for p in panels],
        'display_fbx': str(OUT/'SK_M07_Display_OriginalV06.fbx'),
        'cloth_source_fbx': str(OUT/'SK_M07_ClothBuildSource_OriginalV06.fbx'),
        'cloth_manifest': str(OUT/'cloth_ue_manifest_original_v06.json'),
        'reference_units': 'centimeter vertices and bones, scene scale_length 0.01, identity transforms',
        'ue_imported': False, 'tested': False, 'user_accepted': False}
    (OUT/'anatomy_delivery.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print('M07_ORIGINAL_VISIBLE_SURFACES_AND_HIDDEN_CLOTH_SOURCE_SAVED', flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--regions', required=True)
    p.add_argument('--rig', required=True)
    args = p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    author(Path(args.regions), Path(args.rig))
