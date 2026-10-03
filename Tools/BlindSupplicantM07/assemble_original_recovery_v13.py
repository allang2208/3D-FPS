"""Compose original-surface V13 repairs and lower-budget gill construction.

Production only. No rendering, cloth playback, game launch or acceptance run.
The visible leaves descend from the original Meshy surface, retaining UVs.
"""
import copy
import json
import sys
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
OUT = ROOT/'RecoveryOriginalV13'
sys.path.insert(0, str(Path(__file__).parent))
import author_hands_arms_v11 as skin
import author_original_surfaces_v08 as surfaces
import author_running_v12 as running
import author_motion_v04 as motion


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def surface_transfer(target, source, names):
    """Transfer through an actual surface triangle, never a reduced integer ID."""
    points, faces = skin.mesh_arrays(source)
    tree = BVHTree.FromPolygons(points.tolist(), faces.tolist(), all_triangles=True)
    weights = skin.sparse_field(source, names)
    field = np.empty((len(target.data.vertices), len(names)), np.float32)
    normal = np.empty((len(target.data.vertices), 3), np.float32)
    for vertex in target.data.vertices:
        hit, n, face, _ = tree.find_nearest(vertex.co)
        a, b, c = points[faces[face]]
        ab, ac, q = b-a, c-a, np.asarray(hit)-a
        aa, bb, cc = float(ab@ab), float(ab@ac), float(ac@ac)
        den = aa*cc-bb*bb
        if abs(den) < 1.e-12:
            w = np.array([1., 0., 0.])
        else:
            v = (cc*float(q@ab)-bb*float(q@ac))/den
            z = (aa*float(q@ac)-bb*float(q@ab))/den
            w = np.maximum([1.-v-z, v, z], 0.)
            w /= max(float(w.sum()), 1.e-12)
        field[vertex.index] = (weights[faces[face]]*w[:, None]).sum(axis=0)
        normal[vertex.index] = n
    ids, values = skin.strongest(field)
    surfaces.assign(target, names, ids, values)
    target.data.normals_split_custom_set_from_vertices(normal.tolist())


def reduce_mesh(obj, triangle_budget, weld=False):
    for mod in list(obj.modifiers):
        obj.modifiers.remove(mod)
    if weld:
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.002)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(obj.data)
        bm.free()
    bpy.context.view_layer.objects.active = obj
    obj.hide_set(False)
    obj.hide_viewport = False
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    modifier = obj.modifiers.new('V13OriginalSurfaceReduction', 'DECIMATE')
    modifier.ratio = min(1., triangle_budget/len(obj.data.polygons))
    modifier.use_collapse_triangulate = True
    modifier.delimit = {'UV', 'MATERIAL', 'SEAM'} if not weld else set()
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.update()


def compose_actions(rig):
    base = json.loads((ROOT/'RecoveryHandsV11/rig_motion/motion_manifest_v11.json').read_text(encoding='utf-8'))
    legs = json.loads((ROOT/'RecoveryV13Legs/motion_manifest_v13.json').read_text(encoding='utf-8'))
    arms = json.loads((ROOT/'RecoveryV13Arms/attack_arm_manifest_v13.json').read_text(encoding='utf-8'))
    arm_names = [v['action'] for v in arms['clips'].values()]
    with bpy.data.libraries.load(arms['source'], link=False) as (available, loaded):
        loaded.actions = [name for name in available.actions if name in arm_names]
    entries = copy.deepcopy(base['clips'])
    entries.update(copy.deepcopy(legs['clips']))
    entries.update(copy.deepcopy(arms['clips']))
    rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    ordered = sorted(rig.pose.bones, key=lambda p: len(p.bone.parent_recursive))
    hidden = {o.name: o.hide_viewport for o in bpy.data.objects if o.type == 'MESH'}
    for name in hidden:
        bpy.data.objects[name].hide_viewport = True
    actions = {}
    # Apply the same minimum leg rotation to attacks/reactions as locomotion.
    # Preserve existing pelvis, hip/knee/ankle targets and event timing.
    for role, entry in entries.items():
        source = bpy.data.actions[entry['action']]
        motion.activate(rig, source)
        cache = []
        for frame in range(1, entry['frames']+1):
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            cache.append({p.name: p.matrix.copy() for p in ordered})
        action = bpy.data.actions.new('A_M07_'+role+'_OriginalV13')
        action.use_fake_user = True
        motion.activate(rig, action)
        previous = {}
        for index, target in enumerate(cache):
            frame = index+1
            bpy.context.scene.frame_set(frame)
            pelvis = target['pelvis'].to_quaternion() @ rest['pelvis'].to_quaternion().inverted()
            for side in ('l', 'r'):
                for bone, child in (('thigh', 'calf'), ('calf', 'foot')):
                    name, end = bone+'_'+side, child+'_'+side
                    reference = (rest[end].translation-rest[name].translation).normalized()
                    direction = (target[end].translation-target[name].translation).normalized()
                    rotation = (pelvis @ reference).rotation_difference(direction) @ pelvis @ rest[name].to_quaternion()
                    target[name] = Matrix.LocRotScale(target[name].translation, rotation, Vector((1., 1., 1.)))
            running.insert_frame(rig, target, rest, ordered, frame, previous)
        bpy.context.scene.frame_set(0)
        for p in ordered:
            p.matrix_basis = Matrix.Identity(4)
            for prop in ('location', 'rotation_quaternion', 'scale'):
                p.keyframe_insert(data_path=prop, frame=0, group=p.name)
        for curve in running.curves(action):
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        actions[role] = action
        entry.update({'action': action.name, 'file': str(OUT/'rig_motion'/('A_M07_'+role+'.fbx')),
                      'asset': '/Game/Monsters/BlindSupplicantM07/AnimationsOriginalV13/A_M07_'+role,
                      'leg_orientation': 'Pelvis transported minimum segment rotation; no reverse hinge axial flip'})
        print('M07_V13_COMPOSED_ACTION '+role, flush=True)
    for name, value in hidden.items():
        bpy.data.objects[name].hide_viewport = value
    manifest = dict(base, revision='OriginalV13', source=str(OUT/'M07_Original_Recovery_V13.blend'),
                    clips=entries, legs_source=legs['source'], attacks_source=arms['source'],
                    reference_pose_modified=False, runtime_tested=False, tested=False, rendered=False)
    return actions, manifest


def author():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'rig_motion').mkdir(exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/'RecoveryV13Legs/M07_Original_LegRepair_V13.blend'))
    rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    names = [b.name for b in rig.data.bones]
    actions, manifest = compose_actions(rig)
    rig.animation_data_clear()
    rig.data.pose_position = 'REST'
    for p in rig.pose.bones:
        p.matrix_basis = Matrix.Identity(4)
    bpy.context.scene.frame_set(0)
    cloth = json.loads((ROOT/'RecoveryHandsV11/cloth_ue_manifest_original_v11.json').read_text(encoding='utf-8'))
    body = bpy.data.objects['M07_OriginalBody_Display']
    display, proxies, parts = [body], [], []
    palette = [(1, 0, 0, 1), (0, 1, 0, 1), (0, 0, 1, 1), (1, 1, 0, 1), (1, 0, 1, 1), (0, 1, 1, 1)]
    for label in range(1, 7):
        leaf = bpy.data.objects[f'M07_OriginalGill_{label:02d}_Display']
        proxy = bpy.data.objects[f'M07_OriginalGill_{label:02d}_Simulation']
        leaf_source = leaf.copy()
        leaf_source.data = leaf.data.copy()
        proxy_source = proxy.copy()
        proxy_source.data = proxy.data.copy()
        before = [len(leaf.data.polygons), len(proxy.data.vertices), len(proxy.data.polygons)]
        reduce_mesh(leaf, 8000)
        surface_transfer(leaf, leaf_source, names)
        surfaces.bind(leaf, rig)
        for old in list(leaf.data.color_attributes):
            leaf.data.color_attributes.remove(old)
        colors = leaf.data.color_attributes.new(name='M07LeafIdentity', type='BYTE_COLOR', domain='CORNER')
        colors.data.foreach_set('color', list(palette[label-1])*len(leaf.data.loops))
        leaf.data.color_attributes.active_color = colors
        reduce_mesh(proxy, 240, weld=True)
        surface_transfer(proxy, proxy_source, names)
        surfaces.bind(proxy, rig)
        positions = np.asarray([v.co[:] for v in proxy.data.vertices])
        panel = cloth['panels'][label-1]
        prior = np.asarray(panel['vertices_cm'], dtype=float)
        prior[:, 1] *= -1
        kd = KDTree(len(prior))
        for i, p in enumerate(prior):
            kd.insert(Vector(p), i)
        kd.balance()
        nearest = np.array([kd.find(v.co)[1] for v in proxy.data.vertices])
        mobility = np.clip(np.asarray(panel['max_distance_cm'])[nearest]/(2.5, 1.8, 1.1)[(label-1)%3], 0., 1.)
        # Only lower side panels receive arm clearance. Common folded roots
        # remain fixed; folded upper organization remains lightly skin-driven.
        side = np.clip((np.abs(positions[:, 0])-25.)/18., 0., 1.)
        low = np.clip((255.-positions[:, 2])/35., 0., 1.)
        limit = 1.5 + ((16., 12., 8.)[(label-1)%3]-1.5)*side*low
        maximum = mobility*limit
        panel.update({'vertices_cm': np.c_[positions[:, 0], -positions[:, 1], positions[:, 2]].tolist(),
                      'max_distance_cm': maximum.tolist(), 'pin_weights': (1.-mobility).tolist(),
                      'vertex_count': len(positions), 'triangle_count': len(proxy.data.polygons),
                      'proxy_revision': 'Original shell welded and reduced; same leaf identities, bounded lower-side arm clearance'})
        for key in ('source_original_vertices',):
            panel.pop(key, None)
        parts.append({'panel': label, 'before_display_triangles': before[0],
                      'display_triangles': len(leaf.data.polygons), 'before_sim_vertices': before[1],
                      'simulation_vertices': len(proxy.data.vertices), 'simulation_triangles': len(proxy.data.polygons),
                      'max_distance_cm': float(maximum.max())})
        display.append(leaf)
        proxies.append(proxy)
        bpy.data.objects.remove(leaf_source)
        bpy.data.objects.remove(proxy_source)
        print('M07_V13_ORIGINAL_LEAF_REDUCED '+json.dumps(parts[-1]), flush=True)
    old_collision = json.loads((ROOT/'ArmGillCollisionV12/cloth_ue_manifest_original_v12.json').read_text(encoding='utf-8'))
    keep = {'pelvis', 'ribcage', 'upper_chest', 'shoulder_span', 'upperarm', 'forearm',
            'elbow_joint', 'wrist_metal_cuff', 'palm_index', 'palm_pinky', 'thumb_phalanx_1', 'thigh', 'shin'}
    shapes = [copy.deepcopy(s) for s in old_collision['collision_capsules'] if s['region'] in keep]
    # One broader hand-owned envelope covers four long fingers, rather than
    # thirty small independently animated phalanx collision shapes.
    for side in ('l', 'r'):
        a = rig.data.bones['middle_01_'+side].head_local
        b = rig.data.bones['middle_03_'+side].tail_local
        shapes.append({'bone': 'hand_'+side, 'a_reference_cm': [a.x, -a.y, a.z],
                       'b_reference_cm': [b.x, -b.y, b.z], 'a_cm': [0, 0, 0], 'b_cm': [0, 0, 0],
                       'radius_cm': 5.2, 'region': 'four_finger_envelope'})
    cloth.update({'revision': 'OriginalV13', 'reference_revision': 'OriginalV11', 'collision_capsules': shapes,
                  'method': 'Original surface reduced with UV retained; six welded low-density shell proxies; bounded lower-side travel; body/palm/finger-envelope collision, sparse sphere repulsion',
                  'solver_substeps': 1, 'solver_iterations': 4, 'solver_max_iterations': 6,
                  'particle_face_self_collision': False, 'sphere_self_repulsion': True,
                  'runtime_tested': False, 'tested': False, 'rendered': False})
    surfaces.export(OUT/'SK_M07_Display_OriginalV13.fbx', rig, display)
    surfaces.export(OUT/'SK_M07_ClothBuildSource_OriginalV13.fbx', rig, display+proxies)
    write(OUT/'cloth_ue_manifest_original_v13.json', cloth)
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.render.fps_base = 1.
    rig.data.pose_position = 'POSE'
    bpy.ops.object.select_all(action='DESELECT')
    rig.hide_set(False)
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    for role, entry in manifest['clips'].items():
        motion.activate(rig, actions[role])
        scene.frame_start, scene.frame_end = 1, entry['frames']
        scene.frame_set(0)
        bpy.ops.export_scene.fbx(filepath=entry['file'], use_selection=True, object_types={'ARMATURE'},
            add_leaf_bones=False, use_armature_deform_only=False, armature_nodetype='NULL',
            bake_anim=True, bake_anim_use_all_bones=True, bake_anim_use_all_actions=False,
            bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True, bake_anim_step=1,
            bake_anim_simplify_factor=0., axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS')
    write(OUT/'motion_manifest_v13.json', manifest)
    motion.activate(rig, actions['Idle'])
    scene.frame_start, scene.frame_end = 1, manifest['clips']['Idle']['frames']
    scene.frame_set(0)
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and (obj.name.endswith('_High') or obj.name.endswith('_Simulation')):
            obj.hide_set(True)
            obj.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=manifest['source'], compress=True)
    write(OUT/'source_delivery_v13.json', {'revision': 'OriginalV13', 'saved_source': manifest['source'],
        'original_body_geometry_unchanged': True, 'original_visible_gills_reconstructed': False,
        'original_uv_retained': True, 'body_leg_weights': 'OriginalV13Legs body-only true-surface projection',
        'attacks': 'OriginalV13Arms new minimum-twist choreography', 'reference_pose_changed': False,
        'bone_count': len(rig.data.bones), 'display_triangles': sum(len(o.data.polygons) for o in display),
        'simulation_vertices': sum(len(o.data.vertices) for o in proxies),
        'simulation_triangles': sum(len(o.data.polygons) for o in proxies), 'collision_capsules': len(shapes),
        'parts': parts, 'clips': list(manifest['clips']), 'runtime_tested': False, 'tested': False, 'rendered': False})
    print('M07_V13_ORIGINAL_RECOVERY_MASTER_AND_EXPORTS_SAVED', flush=True)


if __name__ == '__main__':
    author()
