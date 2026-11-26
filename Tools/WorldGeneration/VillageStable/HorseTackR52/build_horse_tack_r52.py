"""AAA HorseTackR52b Blender 5.1 procedural modeler, Warhorse rig skinner & 512px studio icon renderer.

Builds the cohesive 4-piece 'East-Gate Cavalry Tack Suite':
  Standalone StaticMeshes (3 LODs + box collision + Z=0 pivot, for world drops & studio icons):
    1. SM_Tack_Horseshoes         (4-shoe leather-bound bundle + brass ring)
    2. SM_Tack_Saddle             (deep cavalry saddle + crimson/gold blanket + stirrups)
    3. SM_Tack_Barding            (gothic steel chanfron + ear guards + jaw straps)
    4. SM_Tack_Saddlebags         (twin oiled-leather pouches + crimson/gold rolled bedroll)

  Skinned Mounted SkeletalMeshes (sharing SK_StableWarhorse_Skeleton via SetLeaderPoseComponent):
    1. SK_Tack_Horseshoes_Mounted (all 4 proud horseshoes + toe/quarter clips weighted to finger_L/R, toe_L/R)
    2. SK_Tack_Saddle_Mounted     (saddle + blanket + skinned breastplate + dynamic stirrups L/R)
    3. SK_Tack_Barding_Mounted    (chanfron on head + articulated steel ear guards on ear_L/R)
    4. SK_Tack_Saddlebags_Mounted (croup-following bridge yoke + rigid-weighted pouches & bedroll)

Also renders 4 transparent-background 512x512 studio icons directly from the real 3A models into
Content/ColdSteelData/Icons/HorseTack/stable_{horseshoes,saddle,barding,saddlebags}.png.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Euler, Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
PROPS_DIR = PROJECT / 'Tools/WorldGeneration/VillageStable/PropsR43'
sys.path.insert(0, str(PROPS_DIR))

import props_geom  # noqa: E402
from props_geom import AssetBuilder, cm  # noqa: E402

WARHORSE_GLB = PROJECT / 'SourceAssets/HillsVillageStable/HorsesR7/Originals/WarhorseLite.glb'
WARHORSE_FBX = PROJECT / 'SourceAssets/HillsVillageStable/HorsesR7/Exchange/SK_StableWarhorse.fbx'
SRC_ROOT = PROJECT / 'SourceAssets/HillsVillageStable/HorseTackR52'
TEX_DIR = SRC_ROOT / 'Textures'
EXCHANGE_DIR = SRC_ROOT / 'Exchange'
BLEND_OUT = SRC_ROOT / 'HorseTackR52.blend'
MANIFEST_OUT = SRC_ROOT / 'model-manifest.json'
ICONS_DIR = PROJECT / 'Content/ColdSteelData/Icons/HorseTack'
REVIEW_DIR = Path(r'F:\FPSGAMEData\ArtReviews\HillsVillageStable\HorseTackR52-20261126')

props_geom.UV_SCALES_M.update({
    'TackSteel': 0.34,
    'TackLeather': 0.38,
    'TackLeatherDark': 0.34,
    'TackBlanket': 0.56,
})
props_geom.PREVIEW_COLORS.update({
    'TackSteel': (0.28, 0.27, 0.26),
    'TackLeather': (0.28, 0.115, 0.048),
    'TackLeatherDark': (0.11, 0.052, 0.028),
    'TackBlanket': (0.28, 0.055, 0.048),
})


def ue_from_bl(v: Vector) -> Vector:
    """Blender metres (X, Y, Z) -> UE cm (X*100, -Y*100, Z*100)."""
    return Vector((v.x * 100.0, -v.y * 100.0, v.z * 100.0))


def bl_from_ue(p) -> Vector:
    """UE cm (x, y, z) -> Blender metres (x/100, -y/100, z/100)."""
    return Vector((p[0] / 100.0, -p[1] / 100.0, p[2] / 100.0))


class WarhorseRef:
    """Loaded authoritative WarhorseLite.glb rig, geometry, BVH projector & barycentric skin weight sampler."""

    def __init__(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.unit_settings.system = 'METRIC'
        if WARHORSE_GLB.exists():
            bpy.ops.import_scene.gltf(filepath=str(WARHORSE_GLB))
        else:
            bpy.ops.import_scene.fbx(filepath=str(WARHORSE_FBX))
        self.arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        self.mesh_obj = next(o for o in bpy.data.objects if o.type == 'MESH' and o.find_armature() == self.arm)
        self.arm.animation_data_clear()
        for pb in self.arm.pose.bones:
            pb.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()
        for o in list(bpy.data.objects):
            if o not in (self.arm, self.mesh_obj):
                bpy.data.objects.remove(o, do_unlink=True)

        # Build world-space BVHTree (Blender metres) + store polygon vertex indices for exact weight sampling
        me = self.mesh_obj.data
        mw = self.mesh_obj.matrix_world
        self.world_coords = [mw @ v.co for v in me.vertices]
        self.polys = [tuple(p.vertices) for p in me.polygons]
        self.bvh = BVHTree.FromPolygons(self.world_coords, self.polys)
        self.vg_names = {g.index: g.name for g in self.mesh_obj.vertex_groups}

        # Precompute per-vertex weight dicts on Warhorse mesh
        self.vert_weights = []
        for v in me.vertices:
            w = {}
            for g in v.groups:
                if g.weight > 1e-4:
                    w[self.vg_names[g.group]] = g.weight
            self.vert_weights.append(w)

        # Cache bone heads/tails in UE cm
        self.bones_ue = {}
        for b in self.arm.data.bones:
            h_w = self.arm.matrix_world @ b.head_local
            t_w = self.arm.matrix_world @ b.tail_local
            self.bones_ue[b.name] = (ue_from_bl(h_w), ue_from_bl(t_w))

        # Cache per-bone vertex groups in UE cm
        self.vg_pts_ue = {}
        for vg in self.mesh_obj.vertex_groups:
            pts = []
            for vi, w in enumerate(self.vert_weights):
                if w.get(vg.name, 0.0) >= 0.35:
                    pts.append(ue_from_bl(self.world_coords[vi]))
            if pts:
                self.vg_pts_ue[vg.name] = pts

    def ray_surface_ue(self, origin_ue, dir_ue, max_dist_cm=80.0):
        o_bl = bl_from_ue(origin_ue)
        d_bl = Vector((dir_ue[0], -dir_ue[1], dir_ue[2])).normalized()
        hit = self.bvh.ray_cast(o_bl, d_bl, max_dist_cm / 100.0)
        if hit[0] is None:
            return None
        p_ue = ue_from_bl(hit[0])
        n_bl = hit[1]
        n_ue = Vector((n_bl.x, -n_bl.y, n_bl.z)).normalized()
        return p_ue, n_ue, hit[3] * 100.0

    def sample_weights_bl(self, p_bl: Vector, exclude_bones=('stirrup_L', 'stirrup_R', 'tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05')):
        """Barycentric skin weight transfer from nearest Warhorse surface polygon (max 4 influences)."""
        loc, _, face_idx, _ = self.bvh.find_nearest(p_bl)
        if loc is None or face_idx is None:
            return {'spine_01': 1.0}
        ids = self.polys[face_idx]
        if len(ids) >= 3:
            # Project onto triangle (or average polygon vertices by inverse distance)
            a, b, c = self.world_coords[ids[0]], self.world_coords[ids[1]], self.world_coords[ids[2]]
            v0, v1, v2 = b - a, c - a, loc - a
            d00, d01, d11 = v0.dot(v0), v0.dot(v1), v1.dot(v1)
            d20, d21 = v2.dot(v0), v2.dot(v1)
            den = max(1e-12, d00 * d11 - d01 * d01)
            v = (d11 * d20 - d01 * d21) / den
            w = (d00 * d21 - d01 * d20) / den
            u = 1.0 - v - w
            barys = [(ids[0], max(0.0, u)), (ids[1], max(0.0, v)), (ids[2], max(0.0, w))]
        else:
            barys = [(i, 1.0 / len(ids)) for i in ids]
        accum = {}
        for vi, bw in barys:
            if bw <= 0.0:
                continue
            for bname, gw in self.vert_weights[vi].items():
                if bname in exclude_bones:
                    continue
                accum[bname] = accum.get(bname, 0.0) + bw * gw
        if not accum:
            return {'spine_01': 1.0}
        kept = sorted(accum.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(val for _, val in kept)
        return {k: val / tot for k, val in kept if val > 1e-4}

    def sample_weights_ue(self, p_ue, exclude_bones=('stirrup_L', 'stirrup_R', 'tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05')):
        return self.sample_weights_bl(bl_from_ue(p_ue), exclude_bones=exclude_bones)

    def hide_for_export(self, hidden=True):
        self.mesh_obj.hide_set(hidden)
        self.mesh_obj.hide_viewport = hidden
        self.arm.hide_set(hidden)
        self.arm.hide_viewport = hidden


def _blend_weight_dicts(w_a: dict, w_b: dict, alpha_b: float) -> dict:
    """Linearly blend two bone weight dicts, keeping top-4 normalized influences."""
    a = max(0.0, min(1.0, float(alpha_b)))
    out = {}
    for k, v in w_a.items():
        out[k] = out.get(k, 0.0) + v * (1.0 - a)
    for k, v in w_b.items():
        out[k] = out.get(k, 0.0) + v * a
    kept = sorted(out.items(), key=lambda kv: -kv[1])[:4]
    tot = sum(val for _, val in kept)
    if tot <= 1e-6:
        return {'spine_01': 1.0}
    return {k: val / tot for k, val in kept if val > 1e-4}


def finish_skinned_tack(builder: AssetBuilder, ref: WarhorseRef, weight_fn, lod_ratios=(1.0, 0.52, 0.25)):
    """Join parts, bake VertexColor weathering, assign Warhorse skeleton weights & export skinned FBX LOD0..LOD2."""
    # Pre-tag every part's vertex group weights BEFORE join so each sub-part name can drive exact hybrid rigging!
    arm = ref.arm
    bone_names = [b.name for b in arm.data.bones]
    for obj in builder.parts:
        part_name = obj.name
        mw = obj.matrix_world
        vg_map = {bn: obj.vertex_groups.new(name=bn) for bn in bone_names}
        for v in obj.data.vertices:
            p_bl = mw @ v.co
            p_ue = ue_from_bl(p_bl)
            wdict = weight_fn(part_name, p_ue, p_bl)
            for bn, wval in wdict.items():
                if bn in vg_map and wval > 1e-4:
                    vg_map[bn].add([v.index], float(wval), 'REPLACE')

    # Join all parts cleanly (Blender preserves per-vertex vertex_groups + UVs + materials!)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in builder.parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = builder.parts[0]
    if len(builder.parts) > 1:
        bpy.ops.object.join()
    hero = bpy.context.active_object
    hero.name = builder.name
    hero.data.name = builder.name
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # Ensure single active UV0 layer and compact material slots
    for layer in list(hero.data.uv_layers):
        if layer.name != 'UV0':
            hero.data.uv_layers.remove(layer)
    uv0 = hero.data.uv_layers.get('UV0') or hero.data.uv_layers.new(name='UV0')
    uv0.active_render = True
    hero.data.uv_layers.active = uv0

    slot_names = [m.name for m in hero.data.materials]
    face_names = [slot_names[p.material_index] for p in hero.data.polygons]
    used_order = list(dict.fromkeys(face_names))
    hero.data.materials.clear()
    for mname in used_order:
        hero.data.materials.append(builder.mats[mname])
    new_idx = {mname: i for i, mname in enumerate(used_order)}
    for poly, mname in zip(hero.data.polygons, face_names):
        poly.material_index = new_idx[mname]

    # Bake exact 3D VertexColor weathering (R=crevice grime, G=ground mud, B=convex edge burnish)
    props_geom.bake_weathering_vcol(hero, ground_mud_height_cm=builder.ground_mud_cm, is_wall_mounted=builder.is_wall_mounted)

    # Triangulate preserving custom normals and vertex weights
    tri = hero.modifiers.new('Triangulate', 'TRIANGULATE')
    tri.keep_custom_normals = True
    bpy.ops.object.select_all(action='DESELECT')
    hero.select_set(True)
    bpy.context.view_layer.objects.active = hero
    bpy.ops.object.modifier_apply(modifier=tri.name)

    # Clean topology stats (open edges, bounds, materials)
    bm = bmesh.new()
    bm.from_mesh(hero.data)
    open_edges = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    bm.free()

    xs = [v.co.x * 100.0 for v in hero.data.vertices]
    ys = [-v.co.y * 100.0 for v in hero.data.vertices]
    zs = [v.co.z * 100.0 for v in hero.data.vertices]
    size_cm = [round(max(xs) - min(xs), 2), round(max(ys) - min(ys), 2), round(max(zs) - min(zs), 2)]
    mats = [m.name for m in hero.data.materials if m]

    # Bind to authoritative Warhorse Armature identically to author_mane.py
    arm.hide_set(False)
    arm.hide_viewport = False
    arm.name = 'Armature'
    hero.parent = arm
    hero.matrix_world = Matrix.Identity(4)
    mod = hero.modifiers.new('WarhorseRig', 'ARMATURE')
    mod.object = arm

    def export_sk_fbx(target_obj, path: Path):
        bpy.ops.object.select_all(action='DESELECT')
        arm.select_set(True)
        target_obj.select_set(True)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.export_scene.fbx(
            filepath=str(path),
            use_selection=True,
            add_leaf_bones=False,
            use_armature_deform_only=False,
            apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_UNITS',
            axis_forward='-Y',
            axis_up='Z',
            use_mesh_modifiers=False,
            path_mode='STRIP',
            bake_anim=False,
            mesh_smooth_type='FACE',
            use_tspace=True,
            colors_type='LINEAR',
        )

    lods = []
    for lvl, ratio in enumerate(lod_ratios):
        suffix = '' if lvl == 0 else f'_LOD{lvl}'
        out_fbx = EXCHANGE_DIR / f'{builder.name}{suffix}.fbx'
        if lvl == 0:
            tri_cnt = sum(max(0, len(p.vertices) - 2) for p in hero.data.polygons)
            export_sk_fbx(hero, out_fbx)
            lods.append(dict(level=0, file=str(out_fbx), triangles=int(tri_cnt)))
        else:
            dup = hero.copy()
            dup.data = hero.data.copy()
            dup.name = f'{builder.name}_LOD{lvl}'
            bpy.context.collection.objects.link(dup)
            dup.parent = arm
            dup.matrix_world = Matrix.Identity(4)
            # Keep ARMATURE modifier intact; decimate mesh BEFORE armature export!
            dup.modifiers.clear()
            dec = dup.modifiers.new('Decimate', 'DECIMATE')
            dec.ratio = float(ratio)
            dec.delimit = {'MATERIAL', 'UV'}
            dec.use_collapse_triangulate = True
            bpy.ops.object.select_all(action='DESELECT')
            dup.select_set(True)
            bpy.context.view_layer.objects.active = dup
            bpy.ops.object.modifier_apply(modifier='Decimate')
            arm_m = dup.modifiers.new('WarhorseRig', 'ARMATURE')
            arm_m.object = arm
            tri_cnt = sum(max(0, len(p.vertices) - 2) for p in dup.data.polygons)
            export_sk_fbx(dup, out_fbx)
            lods.append(dict(level=lvl, file=str(out_fbx), triangles=int(tri_cnt)))
            bpy.data.objects.remove(dup, do_unlink=True)

    ref.hide_for_export(True)
    return dict(
        name=builder.name,
        kind='skeletal_mounted',
        lods=lods,
        size_cm=size_cm,
        open_edges=int(open_edges),
        materials=mats,
        colliders=[],
    )


# ---------------------------------------------------------------------------
# Shared 3A Craft Hardware Primitives (consolidated to TackSteel / Brass / Leather / Blanket / WaxedThread)
# ---------------------------------------------------------------------------

def add_3d_buckle(b: AssetBuilder, prefix, center_cm, w_cm, h_cm, t_cm,
                  frame_mat='Brass', pin_mat='TackSteel', rot_deg=(0, 0, 0)):
    b.push_xform(center_cm, rot_deg)
    hw, hh = w_cm * 0.5, h_cm * 0.5
    bar = max(0.28, min(w_cm, h_cm) * 0.17)
    b.block(prefix + '_Top', (0.0, 0.0, hh - bar * 0.5), (w_cm, t_cm, bar), mat=frame_mat, bevel_cm=0.08)
    b.block(prefix + '_Bot', (0.0, 0.0, -hh + bar * 0.5), (w_cm, t_cm, bar), mat=frame_mat, bevel_cm=0.08)
    b.block(prefix + '_L', (-hw + bar * 0.5, 0.0, 0.0), (bar, t_cm, h_cm), mat=frame_mat, bevel_cm=0.08)
    b.block(prefix + '_R', (hw - bar * 0.5, 0.0, 0.0), (bar, t_cm, h_cm), mat=frame_mat, bevel_cm=0.08)
    b.block(prefix + '_PinBar', (0.0, -t_cm * 0.08, 0.0), (w_cm - bar * 1.1, t_cm * 0.68, bar * 0.72),
            mat=pin_mat, bevel_cm=0.05)
    b.beam(prefix + '_Prong', (0.0, 0.0, 0.0), (0.0, t_cm * 0.34, -hh + bar * 0.35),
           bar * 0.52, bar * 0.52, mat=pin_mat, wear=0.0, endgrain=False)
    b.pop_xform()


def add_box_x_stitch(b: AssetBuilder, prefix, center_cm, w_cm, h_cm, normal_axis='Y',
                     normal_sign=1.0, rot_deg=(0, 0, 0)):
    b.push_xform(center_cm, rot_deg)
    hw, hh = w_cm * 0.40, h_cm * 0.40
    off = 0.08 * normal_sign
    if normal_axis == 'Y':
        pts_box = [(-hw, off, -hh), (hw, off, -hh), (hw, off, hh), (-hw, off, hh)]
        d1 = [(-hw, off, -hh), (hw, off, hh)]
        d2 = [(hw, off, -hh), (-hw, off, hh)]
    else:
        pts_box = [(off, -hw, -hh), (off, hw, -hh), (off, hw, hh), (off, -hw, hh)]
        d1 = [(off, -hw, -hh), (off, hw, hh)]
        d2 = [(off, hw, -hh), (off, -hw, hh)]
    b.tube(prefix + '_Box', pts_box, 0.13, mat='WaxedThread', sides=6, cyclic=True)
    b.tube(prefix + '_X1', d1, 0.12, mat='WaxedThread', sides=6)
    b.tube(prefix + '_X2', d2, 0.12, mat='WaxedThread', sides=6)
    b.pop_xform()


def add_horseshoe_geometry(b: AssetBuilder, prefix, rx_cm=7.2, ry_cm=8.1, web_w=2.15, thick_z=1.18,
                           toe_clip=True, quarter_clips=False, nails=True, mat='TackSteel'):
    """3A hand-forged medieval horseshoe centered on XY, sitting flat with Z in [0, thick_z]."""
    n_arc = 34
    pts, secs = [], []
    for i in range(n_arc):
        u = i / (n_arc - 1)
        th = -2.38 + u * (2.0 * 2.38)
        heel_taper = 1.0 - 0.14 * (abs(th) / 2.38) ** 2.2
        x = math.sin(th) * rx_cm * heel_taper
        y = math.cos(th) * ry_cm
        caulk = 0.28 * max(0.0, (abs(th) - 2.02) / 0.36) ** 1.6
        pts.append((x, y, thick_z * 0.5 + caulk * 0.35))

        w = web_w * (1.0 - 0.22 * (abs(th) / 2.38) ** 1.7)
        h = thick_z + caulk
        hw, hh = w * 0.5, h * 0.5
        g_w, g_d = hw * 0.34, hh * 0.28
        secs.append([
            (-hw * 0.88, -hh), (-g_w, -hh), (-g_w * 0.65, -hh + g_d), (g_w * 0.65, -hh + g_d),
            (g_w, -hh), (hw * 0.85, -hh), (hw, -hh * 0.45), (hw * 0.90, hh * 0.65),
            (hw * 0.58, hh), (-hw * 0.72, hh), (-hw, hh * 0.45), (-hw, -hh * 0.45),
        ])
    b.sweep_section(prefix + '_Body', pts, secs, mat=mat, cyclic=False, up_hint=(0, 0, 1))

    if toe_clip:
        clip_h = 3.25 if quarter_clips else 2.25
        clip_grid = []
        for iu in range(5):
            u = iu / 4.0
            hw_c = (2.15 if quarter_clips else 1.65) * (1.0 - 0.64 * (u ** 1.4))
            z_c = thick_z * 0.72 + u * clip_h
            y_in = ry_cm + web_w * 0.38 - u * 0.85
            clip_grid.append([(v * hw_c, y_in - 0.22 * (v * v), z_c)
                              for v in ((jv / 4.0) * 2.0 - 1.0 for jv in range(5))])
        b.thick_grid(prefix + '_ToeClip', clip_grid, thick_cm=0.46, mat=mat)

    if quarter_clips:
        # Twin raised armored quarter clips hugging outer left/right hoof walls for unmistakable 3A silhouette!
        for sx in (-1, 1):
            q_grid = []
            for iu in range(5):
                u = iu / 4.0
                hw_q = 1.85 * (1.0 - 0.62 * (u ** 1.4))
                z_q = thick_z * 0.72 + u * 2.65
                x_q = sx * (rx_cm * 0.94 + web_w * 0.36 - u * 0.72)
                q_grid.append([(x_q - sx * 0.16 * (v * v), 1.8 + v * hw_q, z_q)
                               for v in ((jv / 4.0) * 2.0 - 1.0 for jv in range(5))])
            b.thick_grid(f'{prefix}_QClip_{sx}', q_grid, thick_cm=0.42, mat=mat)

    if nails:
        nail_angles = (-1.68, -1.16, -0.62, 0.0, 0.62, 1.16, 1.68)
        for ni, th in enumerate(nail_angles):
            heel_taper = 1.0 - 0.14 * (abs(th) / 2.38) ** 2.2
            nx = math.sin(th) * (rx_cm * heel_taper + 0.10)
            ny = math.cos(th) * (ry_cm + 0.10)
            deg_z = -math.degrees(th)
            b.block(f'{prefix}_NailSeat_{ni}', (nx, ny, thick_z * 0.92), (0.66, 0.86, 0.36),
                    mat='TackSteel', rot_deg=(0, 0, deg_z), bevel_cm=0.06)
            b.block(f'{prefix}_NailHead_{ni}', (nx, ny, thick_z * 1.10), (0.46, 0.60, 0.28),
                    mat='Brass', rot_deg=(0, 0, deg_z), bevel_cm=0.05)


# ---------------------------------------------------------------------------
# 1. HORSESHOES: Standalone 4-Shoe Bundle + Single Skinned 4-Hoof SkeletalMesh
# ---------------------------------------------------------------------------

def build_horseshoes_standalone():
    b = AssetBuilder('SM_Tack_Horseshoes', seed=5201, ground_mud_cm=10.0)
    b.push_xform((-4.8, -0.6, 0.0), (0.0, 0.0, 14.0))
    add_horseshoe_geometry(b, 'Shoe0', rx_cm=6.8, ry_cm=7.7, web_w=2.15, thick_z=1.22)
    b.pop_xform()
    b.push_xform((5.2, 0.8, 0.0), (0.0, 0.0, -162.0))
    add_horseshoe_geometry(b, 'Shoe1', rx_cm=6.8, ry_cm=7.7, web_w=2.15, thick_z=1.22)
    b.pop_xform()
    b.push_xform((-3.2, 0.5, 1.42), (3.5, -2.0, -24.0))
    add_horseshoe_geometry(b, 'Shoe2', rx_cm=6.6, ry_cm=7.5, web_w=2.10, thick_z=1.20)
    b.pop_xform()
    b.push_xform((3.8, -0.7, 1.46), (-3.0, 2.5, 148.0))
    add_horseshoe_geometry(b, 'Shoe3', rx_cm=6.6, ry_cm=7.5, web_w=2.10, thick_z=1.20)
    b.pop_xform()

    b.strap('BindStrapA', [(-2.2, -2.5, 0.45), (-2.5, 2.2, 1.88), (-0.4, 3.2, 3.45),
                           (2.4, 1.8, 3.55), (2.6, -1.8, 2.24), (0.8, -3.1, 0.55)],
            1.48, 0.38, mat='TackLeatherDark', cyclic=True, up_hint=(0, 0, 1))
    b.strap('BindStrapB', [(-1.4, -1.8, 0.55), (-0.8, 2.4, 3.55), (1.8, 1.0, 3.65), (1.6, -2.2, 0.65)],
            1.28, 0.35, mat='TackLeather', cyclic=True, up_hint=(0, 0, 1))
    b.ring_torus('BindBrassRing', (0.2, 3.5, 3.55), 1.75, 0.34, mat='Brass', axis='Z', rot_deg=(24, 8, 0), major_segs=18)
    b.strap('BindTag', [(0.2, 5.0, 3.05), (0.5, 7.6, 2.15), (0.7, 9.8, 0.72)], 1.18, 0.30, mat='TackLeatherDark', up_hint=(0, 0, 1))

    b.add_collider((0.0, 0.0, 2.5), (24.0, 20.0, 5.2))
    return b.finish(EXCHANGE_DIR, lod_ratios=(1.0, 0.52, 0.25))


def build_horseshoes_mounted_skinned(ref: WarhorseRef):
    """Single skinned SkeletalMesh containing all 4 proud armored horseshoes weighted to finger_L/R, toe_L/R."""
    b = AssetBuilder('SK_Tack_Horseshoes_Mounted', seed=5202, ground_mud_cm=7.0, is_wall_mounted=True)
    hoof_specs = [
        ('FL', 'finger_L'),
        ('FR', 'finger_R'),
        ('RL', 'toe_L'),
        ('RR', 'toe_R'),
    ]
    for tag, bone in hoof_specs:
        pts = [p for p in ref.vg_pts_ue[bone] if p.z < 6.0]
        cx = 0.5 * (min(p.x for p in pts) + max(p.x for p in pts))
        cy = 0.5 * (min(p.y for p in pts) + max(p.y for p in pts))
        rx = 0.5 * (max(p.x for p in pts) - min(p.x for p in pts))
        ry = 0.5 * (max(p.y for p in pts) - min(p.y for p in pts))
        z_min = max(0.28, min(p.z for p in pts) + 0.15)

        # Proud +0.95 cm outside hoof rim + 2.1 cm forged thickness + front toe clip & twin quarter clips + brass clinches!
        b.push_xform((cx, cy + 0.45, z_min), (0.0, 0.0, 0.0))
        add_horseshoe_geometry(b, f'{tag}_Rim', rx_cm=rx * 0.94 + 0.95, ry_cm=ry * 0.92 + 0.85,
                               web_w=2.45, thick_z=2.05, toe_clip=True, quarter_clips=True, nails=True, mat='TackSteel')
        for ni, th in enumerate((-1.58, -1.05, -0.52, 0.52, 1.05, 1.58)):
            hr = rx * 0.98 + 1.15
            hy = ry * 0.95 + 1.00
            px = math.sin(th) * hr
            py = math.cos(th) * hy
            b.rivet((px, py, 3.05), axis='X' if abs(math.sin(th)) > 0.55 else 'Y',
                    radius_cm=0.48, height_cm=0.38, mat='Brass')
            # Rename last created rivet part with tag prefix for exact bone weighting
            b.parts[-1].name = f'{tag}_Clinch_{ni}'
        b.pop_xform()

    bone_by_tag = {t: bn for t, bn in hoof_specs}

    def weight_fn(part_name, p_ue, p_bl):
        tag = part_name.split('_')[0]
        return {bone_by_tag.get(tag, 'finger_L'): 1.0}

    return finish_skinned_tack(b, ref, weight_fn, lod_ratios=(1.0, 0.52, 0.28))


# ---------------------------------------------------------------------------
# 2. SADDLE: Standalone StaticMesh + Single Skinned Saddle+Blanket+Breastplate+Stirrups SkeletalMesh
# ---------------------------------------------------------------------------

def _add_forged_stirrup_iron(b: AssetBuilder, prefix, eye_cm, yaw_deg=90.0, scale_s=1.0, arch_rad=0.88):
    b.push_xform(eye_cm, (0.0, 0.0, yaw_deg))
    b.block(prefix + '_Eye', (0.0, 0.0, 0.4 * scale_s), (4.6 * scale_s, 1.85 * scale_s, 2.4 * scale_s),
            mat='TackSteel', bevel_cm=0.18)
    arch_pts = []
    for k in range(19):
        u = k / 18.0
        th = -math.pi * 0.88 + u * (math.pi * 1.76)
        x = math.sin(th) * 7.2 * scale_s * (0.86 + 0.14 * abs(math.cos(th)))
        z = (-7.8 + math.cos(th) * 8.0) * scale_s
        arch_pts.append((x, 0.0, z))
    b.tube(prefix + '_Arch', arch_pts, arch_rad * scale_s, mat='TackSteel', sides=10)
    b.block(prefix + '_Tread', (0.0, 0.0, -15.0 * scale_s), (14.2 * scale_s, 5.4 * scale_s, 1.65 * scale_s),
            mat='TackSteel', bevel_cm=0.18)
    for rx in (-3.8, 0.0, 3.8):
        b.block(f'{prefix}_Grip_{rx:.0f}', (rx * scale_s, 0.0, -14.05 * scale_s),
                (0.75 * scale_s, 4.4 * scale_s, 0.42 * scale_s), mat='Brass', bevel_cm=0.05)
    b.pop_xform()


def _build_saddle_core(b: AssetBuilder, ref: WarhorseRef | None, origin_y_cm=0.0, seat_z_cm=166.0,
                       include_stirrups=True, include_breastplate=False):
    """Build 3A East-Gate Cavalry Saddle (used for standalone SM and skinned SK)."""
    nu_b, nv_b = 26, 30
    pad_grid = []
    for i in range(nu_b):
        u = i / (nu_b - 1)
        y = origin_y_cm - 36.0 + u * 68.0
        row = []
        for j in range(nv_b):
            v = (j / (nv_b - 1)) * 2.0 - 1.0
            av = abs(v)
            sgn = -1.0 if v < 0 else 1.0
            if ref is not None:
                ang = v * math.radians(94.0)
                barrel_c_z = seat_z_cm - 34.0
                ray_o = (sgn * 66.0 * math.sin(abs(ang)), y, barrel_c_z + 66.0 * math.cos(ang))
                ray_d = (-sgn * math.sin(abs(ang)), 0.0, -math.cos(ang))
                hit = ref.ray_surface_ue(ray_o, ray_d, 72.0)
                if hit is not None:
                    p_h, n_h, _ = hit
                    clr = 1.25 + 0.45 * (av ** 1.2)
                    out_dir = Vector((sgn * math.sin(abs(ang)), 0.0, math.cos(abs(ang)))).normalized()
                    p_out = p_h + out_dir * clr
                    if p_out.z < seat_z_cm - 47.0:
                        p_out.z = seat_z_cm - 47.0
                    row.append((p_out.x, p_out.y, p_out.z))
                    continue
            if av < 0.34:
                ang = (av / 0.34) * (math.pi * 0.46)
                x = sgn * (17.5 * math.sin(ang))
                z = seat_z_cm - 11.5 + 12.0 * math.cos(ang)
            else:
                td = (av - 0.34) / 0.66
                x = sgn * (17.3 + 9.2 * math.sin(td * math.pi * 0.55) + 0.8 * td)
                z = seat_z_cm - 10.0 - 33.5 * td
            fold = math.sin(u * math.pi * 4.0 + v * 2.0) * 0.45 * (av ** 1.5)
            row.append((x + sgn * fold, y, z))
        pad_grid.append(row)

    if ref is not None:
        for _ in range(3):
            nxt = [[pad_grid[i][j] for j in range(nv_b)] for i in range(nu_b)]
            for i in range(1, nu_b - 1):
                for j in range(1, nv_b - 1):
                    px = (pad_grid[i-1][j][0] + pad_grid[i+1][j][0] + pad_grid[i][j-1][0] + pad_grid[i][j+1][0]) * 0.25
                    py = (pad_grid[i-1][j][1] + pad_grid[i+1][j][1] + pad_grid[i][j-1][1] + pad_grid[i][j+1][1]) * 0.25
                    pz = (pad_grid[i-1][j][2] + pad_grid[i+1][j][2] + pad_grid[i][j-1][2] + pad_grid[i][j+1][2]) * 0.25
                    cur = pad_grid[i][j]
                    sx_c = -1.0 if cur[0] < 0 else 1.0
                    nx_c = cur[0] * 0.55 + px * 0.45
                    if abs(nx_c) < abs(cur[0]):
                        nx_c = sx_c * (abs(cur[0]) * 0.85 + abs(nx_c) * 0.15)
                    nxt[i][j] = (nx_c, cur[1] * 0.55 + py * 0.45, max(cur[2], cur[2] * 0.55 + pz * 0.45))
            pad_grid = nxt

    b.thick_grid('CavalryBlanket', pad_grid, thick_cm=1.30, mat='TackBlanket', rim_mat='TackLeatherDark')
    for side_idx in (0, nv_b - 1):
        hem_pts = [pad_grid[i][side_idx] for i in range(nu_b)]
        b.tube(f'BlanketPiping_{side_idx}', hem_pts, 0.50, mat='TackLeatherDark', sides=8)
        for i in range(2, nu_b - 2, 3):
            p = pad_grid[i][side_idx]
            sgn_f = -1.0 if p[0] < 0 else 1.0
            b.tube(f'BlanketTassel_{side_idx}_{i}',
                   [(p[0], p[1], p[2] + 0.1), (p[0] + sgn_f * 0.25, p[1], p[2] - 1.3),
                    (p[0] + sgn_f * 0.35, p[1], p[2] - 2.5)], 0.28, mat='TackBlanket', sides=6)

    nu_s, nv_s = 28, 22
    seat_grid = []
    for i in range(nu_s):
        u = i / (nu_s - 1)
        y = origin_y_cm - 26.0 + u * 50.0
        cantle_rise = 14.5 * max(0.0, (0.35 - u) / 0.35) ** 1.85
        pommel_rise = 12.2 * max(0.0, (u - 0.65) / 0.35) ** 1.75
        pocket_dip = -3.8 * math.sin(max(0.0, min(1.0, (u - 0.12) / 0.70)) * math.pi)
        half_w = (20.0 if ref is not None else 17.5) * (0.72 + 0.32 * math.sin(u * math.pi) - 0.20 * max(0.0, (u - 0.66) / 0.34))
        row = []
        for j in range(nv_s):
            v = (j / (nv_s - 1)) * 2.0 - 1.0
            av = abs(v)
            y_wrap = y + (6.2 * (av ** 1.75) if u < 0.36 else -4.0 * (av ** 1.75) * max(0.0, (u - 0.62) / 0.38))
            x = v * half_w
            arch_drop = -12.8 * (av ** 1.92)
            cantle_bowl = cantle_rise * (1.0 - 0.48 * (av ** 2.0))
            pommel_arch = pommel_rise * (1.0 - 0.56 * (av ** 1.85))
            z = seat_z_cm + 3.0 + pocket_dip + cantle_bowl + pommel_arch + arch_drop
            if ref is not None:
                hit = ref.ray_surface_ue((x, y_wrap, z + 26.0), (0.0, 0.0, -1.0), 42.0)
                if hit is not None:
                    min_z = hit[0].z + (0.60 if (0.28 < u < 0.66 and av < 0.45) else 1.40)
                    z = max(z, min_z)
            row.append((x, y_wrap, z))
        seat_grid.append(row)
    b.thick_grid('SaddleTree', seat_grid, thick_cm=2.1, mat='TackLeather', rim_mat='TackLeatherDark')

    pom_base = seat_grid[-1][nv_s // 2]
    horn_pts = [
        (0.0, pom_base[1] - 1.4, pom_base[2] - 0.6),
        (0.0, pom_base[1] + 0.6, pom_base[2] + 3.0),
        (0.0, pom_base[1] + 3.2, pom_base[2] + 5.2),
        (0.0, pom_base[1] + 6.2, pom_base[2] + 5.8),
    ]
    horn_secs = [[(rw * math.cos(a * math.tau / 14), rh * math.sin(a * math.tau / 14)) for a in range(14)]
                 for rw, rh in ((4.8, 3.6), (3.8, 2.8), (4.4, 2.3), (5.0, 1.7))]
    b.sweep_section('PommelHorn', horn_pts, horn_secs, mat='TackLeather', up_hint=(0, 0, 1))
    b.lathe('PommelHornCap', (0.0, pom_base[1] + 5.1, pom_base[2] + 5.7),
            [(0.0, 2.35), (0.35, 2.45), (0.85, 1.80), (1.15, 0.0)], mat='Brass', axis='Y', rot_deg=(18, 0, 0), sides=16)
    b.lathe('PommelGulletBoss', (0.0, pom_base[1] + 2.0, pom_base[2] - 0.4),
            [(0.0, 1.75), (0.35, 1.82), (0.72, 1.25), (0.95, 0.0)], mat='Brass', axis='Y', rot_deg=(-18, 0, 0), sides=14)

    nu_c, nv_c = 16, 14
    cush_grid = []
    for i in range(nu_c):
        u = i / (nu_c - 1)
        row = []
        for j in range(nv_c):
            v = (j / (nv_c - 1)) * 2.0 - 1.0
            si = int(round((0.14 + u * 0.62) * (nu_s - 1)))
            sj = int(round(((v * 0.68) * 0.5 + 0.5) * (nv_s - 1)))
            base_p = seat_grid[si][sj]
            puff = 1.15 * math.sin(u * math.pi) * math.cos(v * math.pi * 0.5)
            row.append((base_p[0], base_p[1], base_p[2] + 0.70 + puff))
        cush_grid.append(row)
    b.thick_grid('SeatCushion', cush_grid, thick_cm=1.5, mat='TackLeather', rim_mat='TackLeatherDark')

    for tag, row_idx, dy_welt, dy_st in (('Cantle', 0, -0.5, 1.35), ('Pommel', -1, 0.5, -1.35)):
        rim_pts = [(seat_grid[row_idx][j][0], seat_grid[row_idx][j][1] + dy_welt, seat_grid[row_idx][j][2] + 0.85)
                   for j in range(nv_s)]
        b.tube(f'{tag}RimRoll', rim_pts, 1.35, mat='TackLeatherDark', sides=12)
        for st_k, mult in enumerate((1.0, 1.60)):
            st_pts = [(p[0] * 0.93, p[1] + dy_st * mult, p[2] - 0.42) for p in rim_pts[1:-1]]
            b.tube(f'{tag}Stitch_{st_k}', st_pts, 0.20, mat='WaxedThread', sides=6)

    for sx in (-1, 1):
        def sample_pad_side(u_norm, v_drop_norm):
            iu_f = max(0.0, min(1.0, u_norm)) * (nu_b - 1)
            iu0 = min(nu_b - 2, int(iu_f))
            fu = iu_f - iu0
            half_j = (nv_b - 1) * 0.5
            jv_f = max(0.0, min(nv_b - 1.0001, half_j + sx * (0.28 + 0.62 * max(0.0, min(1.0, v_drop_norm))) * half_j))
            jv0 = int(jv_f)
            fv = jv_f - jv0
            p00, p10 = Vector(pad_grid[iu0][jv0]), Vector(pad_grid[iu0 + 1][jv0])
            p01, p11 = Vector(pad_grid[iu0][jv0 + 1]), Vector(pad_grid[iu0 + 1][jv0 + 1])
            return p00.lerp(p10, fu).lerp(p01.lerp(p11, fu), fv)

        nu_u, nv_u = 16, 12
        under_grid = []
        for i in range(nu_u):
            u = i / (nu_u - 1)
            env = math.sin(u * math.pi) ** 0.52
            u_pad = 0.14 + u * 0.72
            row = []
            for j in range(nv_u):
                v = j / (nv_u - 1)
                p = sample_pad_side(u_pad + 0.04 * (0.5 - u) * v, v * (0.64 + 0.34 * env))
                row.append((sx * (abs(p.x) + 1.55), p.y, p.z + 0.4 * (1.0 - v)))
            under_grid.append(row)
        b.thick_grid(f'UnderSkirt_{sx}', under_grid, thick_cm=0.95, mat='TackLeatherDark')

        nu_f, nv_f = 18, 12
        flap_grid = []
        for i in range(nu_f):
            u = i / (nu_f - 1)
            env = math.sin(u * math.pi) ** 0.58
            u_pad = 0.19 + u * 0.64
            row = []
            for j in range(nv_f):
                v = j / (nv_f - 1)
                p = sample_pad_side(u_pad + 0.05 * (u - 0.35) * v, v * (0.56 + 0.34 * env))
                knee_bulge = 1.85 * math.exp(-(((u - 0.74) / 0.18) ** 2 + ((v - 0.48) / 0.28) ** 2))
                row.append((sx * (abs(p.x) + 2.85 + knee_bulge), p.y, p.z + 0.5 * (1.0 - v)))
            flap_grid.append(row)
        b.thick_grid(f'MainFlap_{sx}', flap_grid, thick_cm=1.10, mat='TackLeather', rim_mat='TackLeatherDark')

        st_flap = [(flap_grid[i][-1][0] + sx * 0.48, flap_grid[i][-1][1], flap_grid[i][-1][2] + 1.0)
                   for i in range(1, nu_f - 1)]
        b.tube(f'FlapStitch_{sx}', st_flap, 0.19, mat='WaxedThread', sides=6)

        fr_p, rr_p = flap_grid[-3][1], flap_grid[2][1]
        b.block(f'FrontRigTab_{sx}', (fr_p[0] + sx * 0.4, fr_p[1] + 2.0, fr_p[2] + 1.2),
                (1.0, 3.4, 3.2), mat='TackLeatherDark', bevel_cm=0.10)
        b.ring_torus(f'FrontDRing_{sx}', (fr_p[0] + sx * 0.9, fr_p[1] + 3.0, fr_p[2] + 0.1),
                     1.65, 0.32, mat='Brass', axis='X', major_segs=16)
        b.rivet((fr_p[0] + sx * 0.95, fr_p[1] + 2.0, fr_p[2] + 2.0), axis='X', radius_cm=0.52, height_cm=0.36, mat='Brass')
        b.parts[-1].name = f'FrontRivet_{sx}'

        b.block(f'RearRigTab_{sx}', (rr_p[0] + sx * 0.4, rr_p[1] - 1.2, rr_p[2] + 1.4),
                (1.0, 3.0, 2.8), mat='TackLeatherDark', bevel_cm=0.10)
        b.ring_torus(f'RearDRing_{sx}', (rr_p[0] + sx * 0.85, rr_p[1] - 2.2, rr_p[2] + 0.3),
                     1.50, 0.30, mat='Brass', axis='X', major_segs=14)
        b.rivet((rr_p[0] + sx * 0.95, rr_p[1] - 1.2, rr_p[2] + 2.1), axis='X', radius_cm=0.50, height_cm=0.35, mat='Brass')
        b.parts[-1].name = f'RearRivet_{sx}'

        if include_stirrups:
            top_p = flap_grid[int(nu_f * 0.54)][1]
            mid_p = flap_grid[int(nu_f * 0.54)][nv_f - 2]
            st_x, st_y = abs(mid_p[0]) + 1.2, mid_p[1]
            st_top_z, st_bot_z = top_p[2] + 4.5, seat_z_cm - 56.0
            strap_pts = [
                (sx * (abs(top_p[0]) - 0.4), st_y + 1.5, st_top_z),
                (sx * (abs(top_p[0]) + 0.9), st_y + 0.6, st_top_z - 9.0),
                (sx * (st_x + 0.15), st_y, (st_top_z + st_bot_z) * 0.46),
                (sx * st_x, st_y, st_bot_z),
            ]
            b.strap(f'StirrupLeather_{sx}', strap_pts, 2.8, 0.58, mat='TackLeatherDark', up_hint=(0, 1, 0))
            bz = st_bot_z + 15.5
            add_3d_buckle(b, f'StirrupBuckle_{sx}', (sx * (st_x + 0.50), st_y, bz),
                          3.5, 4.0, 0.88, frame_mat='Brass', pin_mat='TackSteel', rot_deg=(0, 0, sx * 90))
            b.block(f'StirrupKeeper_{sx}', (sx * (st_x + 0.22), st_y, bz - 3.6),
                    (1.05, 3.3, 1.65), mat='TackLeather', bevel_cm=0.14)
            _add_forged_stirrup_iron(b, f'StirrupIron_{sx}', (sx * st_x, st_y, st_bot_z), yaw_deg=sx * 82.0)

    chest_medallion_center = None
    if include_breastplate and ref is not None:
        breast_pts = []
        for k in range(21):
            u = k / 20.0
            ang = (u - 0.5) * math.pi
            core = Vector((0.0, 22.0, 134.0 - 11.0 * math.cos(ang)))
            dir_out = Vector((-math.sin(ang), math.cos(ang) * 1.15, -0.14 * math.cos(ang))).normalized()
            hit = ref.ray_surface_ue(core + dir_out * 64.0, -dir_out, 62.0)
            if hit is not None and hit[0].y < 72.0 and hit[0].z < 164.0:
                p_out = hit[0] + dir_out * 1.45
                breast_pts.append((p_out.x, p_out.y, p_out.z))
        if len(breast_pts) >= 9:
            b.strap('BreastplateStrap', breast_pts, 8.6, 1.05, mat='TackLeatherDark', up_hint=(0, 0, 1))
            b.strap('BreastplateTrim', [(p[0] * 1.012, p[1] + 0.35, p[2]) for p in breast_pts[1:-1]],
                    5.0, 0.55, mat='TackLeather', up_hint=(0, 0, 1))
            for dz_st in (-3.0, 3.0):
                b.tube(f'BreastStitch_{dz_st:.0f}',
                       [(p[0] * 1.015, p[1] + 0.45, p[2] + dz_st) for p in breast_pts[1:-1]],
                       0.20, mat='WaxedThread', sides=6)
            for idx_r in range(2, len(breast_pts) - 2, 2):
                rp = breast_pts[idx_r]
                if idx_r == len(breast_pts) // 2:
                    continue
                b.rivet((rp[0] * 1.018, rp[1] + 0.55, rp[2]), axis='Y', radius_cm=0.58, height_cm=0.40, mat='Brass')
                b.parts[-1].name = f'BreastRivet_{idx_r}'
            mid_c = breast_pts[len(breast_pts) // 2]
            chest_medallion_center = Vector(mid_c)
            b.lathe('ChestBrassMedallion', (mid_c[0], mid_c[1] + 0.72, mid_c[2]),
                    [(0.0, 4.4), (0.5, 4.55), (1.10, 3.3), (1.5, 1.4), (1.80, 0.0)],
                    mat='Brass', axis='Y', sides=20)
            b.ring_torus('ChestBrassRing', (mid_c[0], mid_c[1] + 0.62, mid_c[2]),
                         4.65, 0.48, mat='TackSteel', axis='Y', major_segs=20)
    return chest_medallion_center


def build_saddle_standalone():
    b = AssetBuilder('SM_Tack_Saddle', seed=5210, ground_mud_cm=16.0)
    _build_saddle_core(b, ref=None, origin_y_cm=0.0, seat_z_cm=71.2, include_stirrups=True, include_breastplate=False)
    b.add_collider((0.0, 0.0, 44.0), (66.0, 72.0, 88.0))
    return b.finish(EXCHANGE_DIR, lod_ratios=(1.0, 0.50, 0.22))


def build_saddle_mounted_skinned(ref: WarhorseRef):
    """Single skinned SkeletalMesh combining Saddle + Blanket + Skinned Breastplate + Dynamic Stirrups L/R."""
    b = AssetBuilder('SK_Tack_Saddle_Mounted', seed=5211, ground_mud_cm=0.0, is_wall_mounted=True)
    medallion_ctr = _build_saddle_core(b, ref=ref, origin_y_cm=-4.5, seat_z_cm=166.5,
                                       include_stirrups=False, include_breastplate=True)

    # Add BOTH forged steel stirrups + buckled leather straps inside SK_Tack_Saddle_Mounted (weighted 100% to stirrup_L/R!)
    for tag, bone, sx in (('StirrupL', 'stirrup_L', 1), ('StirrupR', 'stirrup_R', -1)):
        pts = ref.vg_pts_ue[bone]
        z_min = min(p.z for p in pts)
        iron_pts = [p for p in pts if p.z <= z_min + 18.0] or pts
        cx = 0.5 * (min(p.x for p in iron_pts) + max(p.x for p in iron_pts))
        cy = 0.5 * (min(p.y for p in iron_pts) + max(p.y for p in iron_pts))
        iron_span_y = max(p.y for p in iron_pts) - min(p.y for p in iron_pts)
        scale_s = max(1.06, min(1.18, (iron_span_y + 2.2) / 14.2))
        eye_z = z_min + 15.6 * scale_s
        top_z = 128.0
        b.strap(f'{tag}_Leather', [(cx, cy, top_z), (cx + sx * 0.25, cy, eye_z)],
                3.3, 1.35, mat='TackLeatherDark', up_hint=(0, 1, 0))
        add_3d_buckle(b, f'{tag}_Buckle', (cx + sx * 0.85, cy, eye_z + 8.5),
                      3.9, 4.3, 1.1, frame_mat='Brass', pin_mat='TackSteel', rot_deg=(0, 0, sx * 90))
        b.block(f'{tag}_Keeper', (cx + sx * 0.55, cy, eye_z + 4.8), (1.45, 3.8, 1.8), mat='TackLeather', bevel_cm=0.12)
        _add_forged_stirrup_iron(b, f'{tag}_Iron', (cx, cy, eye_z), yaw_deg=sx * 90.0, scale_s=scale_s, arch_rad=1.18)

    medallion_w = ref.sample_weights_ue(medallion_ctr) if medallion_ctr is not None else {'spine_03': 1.0}
    saddle_rigid = {'saddle_socket': 1.0}

    def weight_fn(part_name, p_ue, p_bl):
        if part_name.startswith('StirrupL_'):
            return {'stirrup_L': 1.0}
        if part_name.startswith('StirrupR_'):
            return {'stirrup_R': 1.0}
        if part_name in ('ChestBrassMedallion', 'ChestBrassRing'):
            return medallion_w
        if part_name.startswith('Breast'):
            # Smoothly follow moving shoulders/chest/neck (scapula_L/R + upperarm + neck_01) with zero clipping!
            w_surf = ref.sample_weights_bl(p_bl)
            # Near rear saddle anchor (y < 30 cm), blend smoothly back to saddle_socket so strap stays anchored to saddle
            t_chest = max(0.0, min(1.0, (p_ue.y - 22.0) / 18.0))
            return _blend_weight_dicts(saddle_rigid, w_surf, t_chest)
        if part_name.startswith('CavalryBlanket') or part_name.startswith('Blanket'):
            # Top under saddle stays rigid on saddle_socket; lower skirt hem flexes gently with barrel!
            t_hem = max(0.0, min(1.0, (148.0 - p_ue.z) / 26.0)) * 0.45
            if t_hem > 0.02:
                return _blend_weight_dicts(saddle_rigid, ref.sample_weights_bl(p_bl), t_hem)
            return saddle_rigid
        return saddle_rigid

    return finish_skinned_tack(b, ref, weight_fn, lod_ratios=(1.0, 0.52, 0.25))


# ---------------------------------------------------------------------------
# 3. BARDING (STEEL CHANFRON): Standalone SM + Articulated Skinned SK (head + ear_L/R)
# ---------------------------------------------------------------------------

def _sample_head_chanfron_surface(ref: WarhorseRef):
    poll_c = Vector((0.0, 96.5, 195.5))
    muzzle_c = Vector((0.0, 125.2, 155.8))
    axis = (muzzle_c - poll_c).normalized()
    face_out = Vector((0.0, -axis.z, axis.y)).normalized()
    face_len = (muzzle_c - poll_c).length

    nu, nv = 28, 25
    grid = []
    for i in range(nu):
        u = i / (nu - 1)
        spine_c = poll_c + axis * (u * face_len)
        half_ang = math.radians(
            56.0
            + 16.0 * math.exp(-((u - 0.14) / 0.14) ** 2)
            - 21.0 * math.exp(-((u - 0.34) / 0.10) ** 2)
            + 22.0 * math.exp(-((u - 0.58) / 0.15) ** 2)
            - 16.0 * max(0.0, (u - 0.74) / 0.26)
        )
        row = []
        for j in range(nv):
            v = (j / (nv - 1)) * 2.0 - 1.0
            av = abs(v)
            ang = v * half_ang
            skull_ctr = spine_c - face_out * (9.5 - 3.0 * u)
            ray_dir_out = (face_out * math.cos(ang) + Vector((math.sin(ang), 0.0, 0.0))).normalized()
            hit = ref.ray_surface_ue(skull_ctr + ray_dir_out * 28.0, -ray_dir_out, 32.0)
            p_h = hit[0] if hit is not None else (skull_ctr + ray_dir_out * (9.2 - 2.4 * u))
            ridge = 1.55 * math.exp(-((av / 0.13) ** 2)) * (0.55 + 0.45 * math.sin(u * math.pi))
            brow_flare = 1.35 * math.exp(-((u - 0.21) / 0.07) ** 2) * math.exp(-((av - 0.50) / 0.32) ** 2)
            muzzle_flare = 0.75 * max(0.0, (u - 0.82) / 0.18) ** 1.4
            row.append(p_h + ray_dir_out * (1.20 + ridge + brow_flare + muzzle_flare))
        grid.append(row)

    for _ in range(3):
        nxt = [[grid[i][j] for j in range(nv)] for i in range(nu)]
        for i in range(1, nu - 1):
            for j in range(1, nv - 1):
                if j == nv // 2:
                    continue
                avg = (grid[i-1][j] + grid[i+1][j] + grid[i][j-1] + grid[i][j+1]) * 0.25
                nxt[i][j] = grid[i][j] * 0.58 + avg * 0.42
        grid = nxt
    return grid, axis, face_out, poll_c, muzzle_c


def _grid_bilerp(grid, u_norm, v_norm):
    nu, nv = len(grid), len(grid[0])
    fu = max(0.0, min(1.0, u_norm)) * (nu - 1)
    fv = max(0.0, min(1.0, v_norm)) * (nv - 1)
    i0, j0 = min(nu - 2, int(fu)), min(nv - 2, int(fv))
    tu, tv = fu - i0, fv - j0
    return grid[i0][j0].lerp(grid[i0 + 1][j0], tu).lerp(grid[i0][j0 + 1].lerp(grid[i0 + 1][j0 + 1], tu), tv)


def _add_chanfron_parts(b: AssetBuilder, ref: WarhorseRef, xform_fn=None):
    def mp(p):
        v = Vector(p)
        return tuple(xform_fn(v)) if xform_fn else (v.x, v.y, v.z)

    grid, axis, face_out, poll_c, muzzle_c = _sample_head_chanfron_surface(ref)
    nu, nv = len(grid), len(grid[0])

    b.thick_grid('ChanfronMainPlate', [[mp(grid[i][j]) for j in range(nv)] for i in range(nu)],
                 thick_cm=0.88, mat='TackSteel', rim_mat='Brass')

    g_liner = [[mp(_grid_bilerp(grid, 0.02 + (i / (nu - 1)) * 0.96, 0.03 + (j / (nv - 1)) * 0.94) - face_out * 0.62)
                for j in range(nv)] for i in range(nu)]
    b.thick_grid('ChanfronLeatherLiner', g_liner, thick_cm=0.52, mat='TackLeatherDark')

    spine_pts = [mp(_grid_bilerp(grid, i / 25.0, 0.5) + face_out * 0.58) for i in range(26)]
    spine_secs = []
    for i in range(26):
        u = i / 25.0
        w = 1.35 * (0.72 + 0.42 * math.sin(u * math.pi))
        h = 1.15 * (0.75 + 0.35 * math.sin(u * math.pi))
        spine_secs.append([(-w, -h * 0.4), (0.0, h), (w, -h * 0.4), (w * 0.68, -h), (-w * 0.68, -h)])
    b.sweep_section('ChanfronSpineRib', spine_pts, spine_secs, mat='TackSteel', up_hint=(0, 1, 1))

    ear_bases = {}
    for sx in (-1, 1):
        brow_pts = [mp(_grid_bilerp(grid, 0.16 + 0.11 * math.sin((k / 14.0) * math.pi * 0.82) + 0.03 * (k / 14.0),
                                    0.5 + sx * ((k / 14.0) * 0.49)) + face_out * (0.72 + 0.42 * math.sin((k / 14.0) * math.pi)))
                    for k in range(15)]
        b.strap(f'BrowFlange_{sx}', brow_pts, 2.25, 0.68, mat='TackSteel', up_hint=(0, 0, 1))

        edge_v = 0.99 if sx > 0 else 0.01
        edge_pts = []
        for k in range(28):
            uk = k / 27.0
            pe = _grid_bilerp(grid, uk, edge_v)
            eye_t = max(0.0, 1.0 - abs(uk - 0.34) / 0.11)
            eye_lip = math.sin(eye_t * math.pi * 0.5) ** 1.5
            pe = pe + face_out * (0.42 + 0.55 * eye_lip) + Vector((sx * 0.55 * eye_lip, 0.0, 0.0))
            edge_pts.append(mp(pe))
        b.tube(f'SideBorderRoll_{sx}', edge_pts, 0.66, mat='TackSteel', sides=10)

        ear_name = 'ear_L' if sx > 0 else 'ear_R'
        e_head, e_tail = ref.bones_ue[ear_name]
        e_dir = (e_tail - e_head).normalized()
        e_len = (e_tail - e_head).length * 0.90
        ear_bases[ear_name] = (e_head, e_dir, e_len)
        side_ax = e_dir.cross(Vector((0, 1, 0))).normalized()
        back_ax = side_ax.cross(e_dir).normalized()
        if back_ax.y > 0:
            back_ax = -back_ax
        ec_grid = []
        for iu_e in range(12):
            ue = iu_e / 11.0
            rad_e = 3.55 * ((1.0 - ue) ** 0.72) * (0.85 + 0.38 * math.sin(ue * math.pi)) + 0.18
            c_e = e_head + e_dir * (ue * e_len - 0.8)
            ec_grid.append([mp(c_e + (back_ax * math.cos(((jv_e / 10.0) * 2.0 - 1.0) * math.radians(105.0))
                                      + side_ax * math.sin(((jv_e / 10.0) * 2.0 - 1.0) * math.radians(105.0))) * rad_e)
                            for jv_e in range(11)])
        b.thick_grid(f'EarGuard_{ear_name}', ec_grid, thick_cm=0.52, mat='TackSteel', rim_mat='Brass')

        collar_pts = [mp(e_head + (back_ax * math.cos(k * math.tau / 16) + side_ax * math.sin(k * math.tau / 16)) * 3.65 - e_dir * 0.5)
                      for k in range(16)]
        b.tube(f'EarCollar_{ear_name}', collar_pts, 0.52, mat='TackSteel', sides=8, cyclic=True)

    b.tube('MuzzleRim', [mp(_grid_bilerp(grid, 1.0, j / 20.0) + face_out * 0.48) for j in range(21)], 0.62, mat='TackSteel', sides=10)
    b.tube('PollRim', [mp(_grid_bilerp(grid, 0.0, j / 20.0) + face_out * 0.48) for j in range(21)], 0.62, mat='TackSteel', sides=10)

    rivet_uvs = [(0.04, k / 8.0) for k in range(1, 8)] + [(0.95, k / 8.0) for k in range(1, 8)] + \
                [(k / 9.0, 0.07) for k in range(1, 9)] + [(k / 9.0, 0.93) for k in range(1, 9)]
    for ri, (ut, vt) in enumerate(rivet_uvs):
        b.rivet(mp(_grid_bilerp(grid, ut, vt) + face_out * 0.48), axis='Y', radius_cm=0.44, height_cm=0.34, mat='Brass')
        b.parts[-1].name = f'FaceRivet_{ri}'

    for idx_s, (u_anch, back_clear) in enumerate(((0.22, 16.0), (0.64, 13.0))):
        p_l, p_r = _grid_bilerp(grid, u_anch, 0.98), _grid_bilerp(grid, u_anch, 0.02)
        base_c = (p_l + p_r) * 0.5
        strap_loop = []
        for k in range(15):
            th = (k / 14.0 - 0.5) * math.pi
            pt = Vector((math.sin(th) * (abs(p_l.x) + 1.0), base_c.y, base_c.z)) - face_out * (math.cos(th) * back_clear) + axis * (1.0 * math.cos(th))
            hit = ref.ray_surface_ue(pt - face_out * 14.0, face_out, 18.0)
            if hit is not None and (hit[0] - pt).dot(face_out) < 0.0:
                pt = hit[0] - face_out * 1.10
            strap_loop.append(mp(pt))
        b.strap(f'JawStrap_{idx_s}', strap_loop, 2.20, 0.50, mat='TackLeatherDark', up_hint=(0, 0, 1))
        for sx in (-1, 1):
            bp = strap_loop[2 if sx < 0 else -3]
            add_3d_buckle(b, f'ChanfronBuckle_{idx_s}_{sx}', bp, 2.9, 2.7, 0.70,
                          frame_mat='Brass', pin_mat='TackSteel', rot_deg=(0, 0, sx * 85))
            if idx_s == 1:
                b.ring_torus(f'CheekBrassRing_{sx}', mp((p_l if sx > 0 else p_r) - face_out * 1.4),
                             1.45, 0.28, mat='Brass', axis='X', major_segs=14)
    return ear_bases


def build_barding_pair(ref: WarhorseRef):
    bm = AssetBuilder('SK_Tack_Barding_Mounted', seed=5220, ground_mud_cm=0.0, is_wall_mounted=True)
    ear_bases = _add_chanfron_parts(bm, ref, xform_fn=None)

    def weight_fn(part_name, p_ue, p_bl):
        if part_name.startswith('EarGuard_'):
            ename = part_name.replace('EarGuard_', '')
            e_head, e_dir, e_len = ear_bases[ename]
            t_e = max(0.0, min(1.0, (p_ue - e_head).dot(e_dir) / max(1.0, e_len * 0.45)))
            w_ear = 0.45 + 0.55 * t_e
            return {ename: w_ear, 'head': 1.0 - w_ear}
        if part_name.startswith('EarCollar_'):
            ename = part_name.replace('EarCollar_', '')
            return {'head': 0.72, ename: 0.28}
        return {'head': 1.0}

    m_mounted = finish_skinned_tack(bm, ref, weight_fn, lod_ratios=(1.0, 0.52, 0.25))

    pivot = Vector((0.0, 110.0, 178.0))
    rot_stand = Euler((math.radians(18.0), 0.0, 0.0), 'XYZ').to_matrix()
    bs = AssetBuilder('SM_Tack_Barding', seed=5221, ground_mud_cm=8.0)
    _add_chanfron_parts(bs, ref, xform_fn=lambda v: rot_stand @ (v - pivot) + Vector((0.0, 0.0, 26.5)))
    all_z_m = [min((p.matrix_world @ vv.co).z for vv in p.data.vertices) for p in bs.parts]
    z_shift = -min(all_z_m)
    for p in bs.parts:
        p.location.z += z_shift
    bs.add_collider((0.0, 0.0, 24.0), (30.0, 44.0, 48.0))
    m_stand = bs.finish(EXCHANGE_DIR, lod_ratios=(1.0, 0.52, 0.24))
    return m_stand, m_mounted


# ---------------------------------------------------------------------------
# 4. SADDLEBAGS: Standalone SM + Skinned Croup-Following SK
# ---------------------------------------------------------------------------

def _add_saddlebag_pouch(b: AssetBuilder, prefix, center_cm, sx, yaw_deg=0.0, tilt_deg=14.0):
    b.push_xform(center_cm, (0.0, sx * tilt_deg, yaw_deg))
    nu_p, nv_p = 14, 16
    hw_x, hy, hz = 6.4, 13.2, 12.6
    rings = []
    for i in range(nu_p):
        u = i / (nu_p - 1)
        z = (u * 2.0 - 1.0) * hz
        belly = 0.84 + 0.22 * math.sin(u * math.pi) - 0.14 * (u ** 2.2)
        z_round = math.sqrt(max(0.04, 1.0 - (abs(u * 2.0 - 1.0) ** 3.2)))
        row = []
        for j in range(nv_p):
            ang = j * math.tau / nv_p
            ca, sa = math.cos(ang), math.sin(ang)
            px = math.copysign(abs(ca) ** 0.72, ca) * hw_x * belly * z_round
            if px * sx < 0:
                px *= 0.60
            py = math.copysign(abs(sa) ** 0.65, sa) * hy * (0.94 + 0.08 * math.sin(u * math.pi)) * z_round
            sag = 0.32 * math.sin(u * math.pi * 3.0 + ang * 2.0) * (1.0 - u * 0.4)
            row.append((px + sx * sag, py, z))
        rings.append(row)

    verts, faces = [rings[i][j] for i in range(nu_p) for j in range(nv_p)], []
    for i in range(nu_p - 1):
        for j in range(nv_p):
            jn = (j + 1) % nv_p
            faces.append((i * nv_p + j, i * nv_p + jn, (i + 1) * nv_p + jn, (i + 1) * nv_p + j))
    bot_i, top_i = len(verts), len(verts) + 1
    verts.extend([(0.0, 0.0, -hz - 0.3), (0.0, 0.0, hz + 0.2)])
    for j in range(nv_p):
        jn = (j + 1) % nv_p
        faces.append((bot_i, jn, j))
        faces.append((top_i, (nu_p - 1) * nv_p + j, (nu_p - 1) * nv_p + jn))
    obj = b._new_mesh_obj(prefix + '_Body', verts, faces, 'TackLeather')
    b._bake_smooth(obj, 65.0)
    b._uv_box(obj, long_axis=2)

    pipe_pts = [(sx * (hw_x * 0.45), math.sin(k * math.tau / 20) * (hy + 0.35),
                 math.cos(k * math.tau / 20) * (hz + 0.15)) for k in range(20)]
    b.tube(prefix + '_Piping', pipe_pts, 0.46, mat='TackLeatherDark', sides=8, cyclic=True)

    nu_fl, nv_fl = 14, 14
    flap_grid = []
    for i in range(nu_fl):
        u = i / (nu_fl - 1)
        row = []
        for j in range(nv_fl):
            v = (j / (nv_fl - 1)) * 2.0 - 1.0
            y = v * (hy * 0.96)
            if u < 0.40:
                t = u / 0.40
                x = sx * (-hw_x * 0.45 + t * (hw_x * 1.50))
                z = hz + 1.0 - 1.15 * (t ** 2.4)
            else:
                t = (u - 0.40) / 0.60
                x = sx * (hw_x * 1.08 + 1.30 * math.sin(t * math.pi * 0.72))
                z = hz - 0.15 - t * 14.2 + 1.1 * (v * v) * t
            row.append((x, y, z))
        flap_grid.append(row)
    b.thick_grid(prefix + '_Flap', flap_grid, thick_cm=0.92, mat='TackLeather', rim_mat='TackLeatherDark')

    hem_st = [(flap_grid[-1][j][0] + sx * 0.40, flap_grid[-1][j][1] * 0.94, flap_grid[-1][j][2] + 0.85)
              for j in range(1, nv_fl - 1)]
    b.tube(prefix + '_FlapStitch', hem_st, 0.19, mat='WaxedThread', sides=6)

    for si, sy_off in enumerate((-6.6, 6.6)):
        b.strap(f'{prefix}_Strap_{si}',
                [(sx * (hw_x * 0.45), sy_off, hz + 1.30), (sx * (hw_x * 1.16), sy_off, hz + 0.20),
                 (sx * (hw_x * 1.34), sy_off, 2.1), (sx * (hw_x * 1.20), sy_off, -9.0)],
                2.55, 0.50, mat='TackLeatherDark', up_hint=(0, 1, 0))
        add_box_x_stitch(b, f'{prefix}_BoxX_{si}', (sx * (hw_x * 1.28), sy_off, 5.1),
                         2.0, 2.3, normal_axis='X', normal_sign=sx)
        add_3d_buckle(b, f'{prefix}_Buckle_{si}', (sx * (hw_x * 1.42), sy_off, -2.8),
                      3.5, 4.0, 0.92, frame_mat='TackSteel', pin_mat='Brass', rot_deg=(0, 0, sx * 90))
        b.block(f'{prefix}_Keeper_{si}', (sx * (hw_x * 1.32), sy_off, -6.1),
                (1.02, 3.1, 1.50), mat='TackLeather', bevel_cm=0.12)
        b.rivet((sx * (hw_x * 1.15), sy_off, hz + 0.80), axis='Z', radius_cm=0.44, height_cm=0.34, mat='Brass')
        b.parts[-1].name = f'{prefix}_Rivet_{si}'
    b.pop_xform()


def _add_saddlebags_assembly(b: AssetBuilder, ref: WarhorseRef | None, origin_y_cm=-40.0, top_z_cm=165.0):
    nu_br, nv_br = 12, 22
    bridge_grid = []
    for i in range(nu_br):
        u = i / (nu_br - 1)
        y = origin_y_cm - 10.8 + u * 21.6
        row = []
        for j in range(nv_br):
            v = (j / (nv_br - 1)) * 2.0 - 1.0
            av = abs(v)
            sgn = -1.0 if v < 0 else 1.0
            y_tap = origin_y_cm + (y - origin_y_cm) * (1.0 - 0.24 * (av ** 1.6))
            if ref is not None:
                ang = v * math.radians(60.0)
                ray_o = (sgn * 56.0 * math.sin(abs(ang)), y_tap, top_z_cm - 14.0 + 48.0 * math.cos(ang))
                ray_d = (-sgn * math.sin(abs(ang)), 0.0, -math.cos(ang))
                hit = ref.ray_surface_ue(ray_o, ray_d, 72.0)
                if hit is not None:
                    p_out = hit[0] + hit[1] * 1.15
                    row.append((p_out.x, p_out.y, p_out.z))
                    continue
            row.append((v * 17.8, y_tap, top_z_cm + 2.2 - 7.8 * (av ** 1.9)))
        bridge_grid.append(row)
    b.thick_grid('BridgeYoke', bridge_grid, thick_cm=1.05, mat='TackLeather', rim_mat='TackLeatherDark')

    for ei in (0, nu_br - 1):
        st_b = [(bridge_grid[ei][j][0], bridge_grid[ei][j][1] + (0.75 if ei == 0 else -0.75), bridge_grid[ei][j][2] + 0.60)
                for j in range(1, nv_br - 1)]
        b.tube(f'BridgeStitch_{ei}', st_b, 0.19, mat='WaxedThread', sides=6)

    anchors = {}
    for sx in (-1, 1):
        end_p = bridge_grid[nu_br // 2][nv_br - 1 if sx > 0 else 0]
        b.block(f'BridgeKeeper_{sx}', (end_p[0] - sx * 1.4, origin_y_cm, end_p[2] + 0.45),
                (3.6, 9.6, 1.35), mat='TackLeatherDark', rot_deg=(0, sx * 36, 0), bevel_cm=0.14)
        for ri, ry in enumerate((-2.4, 2.4)):
            b.rivet((end_p[0] - sx * 1.2, origin_y_cm + ry, end_p[2] + 1.15), axis='Z', radius_cm=0.48, height_cm=0.36, mat='Brass')
            b.parts[-1].name = f'BridgeRivet_{sx}_{ri}'

        if ref is not None:
            hit = ref.ray_surface_ue((sx * 64.0, origin_y_cm, top_z_cm - 15.0), (-sx, 0.0, 0.0), 50.0)
            flank_x = abs(hit[0].x) if hit is not None else 31.0
            bag_ctr = (sx * (flank_x + 4.4), origin_y_cm, top_z_cm - 15.5)
            anchors[f'Pouch_{sx}'] = Vector((sx * flank_x, origin_y_cm, top_z_cm - 10.0))
            _add_saddlebag_pouch(b, f'Pouch_{sx}', bag_ctr, sx, yaw_deg=-sx * 5.0, tilt_deg=17.0)
        else:
            bag_ctr = (sx * 19.2, origin_y_cm, top_z_cm - 14.5)
            _add_saddlebag_pouch(b, f'Pouch_{sx}', bag_ctr, sx, yaw_deg=-sx * 4.0, tilt_deg=10.0)

    center_top = bridge_grid[nu_br // 2][nv_br // 2]
    roll_z, roll_y = center_top[2] + 5.2, origin_y_cm + 2.8
    roll_hw = 19.5 if ref is not None else 15.5
    anchors['Bedroll'] = Vector((0.0, roll_y, center_top[2]))
    b.lathe('TravelBedroll', (0.0, roll_y, roll_z),
            [(-roll_hw, 0.0), (-roll_hw + 0.7, 4.2), (-roll_hw * 0.78, 5.0), (0.0, 5.3),
             (roll_hw * 0.78, 5.0), (roll_hw - 0.7, 4.2), (roll_hw, 0.0)],
            mat='TackBlanket', axis='X', sides=20)
    for sx in (-1, 1):
        b.ring_torus(f'RollSpiralA_{sx}', (sx * (roll_hw - 0.9), roll_y, roll_z), 2.9, 0.38, mat='TackLeatherDark', axis='X', major_segs=16)
        b.ring_torus(f'RollSpiralB_{sx}', (sx * (roll_hw - 0.7), roll_y, roll_z), 1.5, 0.32, mat='TackLeatherDark', axis='X', major_segs=14)
        rx = sx * (roll_hw * 0.56)
        cinch_pts = [(rx, roll_y + 5.4 * math.cos(k * math.tau / 20), roll_z + 5.4 * math.sin(k * math.tau / 20)) for k in range(20)]
        b.strap(f'BedrollCinch_{sx}', cinch_pts, 2.1, 0.48, mat='TackLeatherDark', cyclic=True, up_hint=(1, 0, 0))
        add_3d_buckle(b, f'BedrollBuckle_{sx}', (rx, roll_y - 5.7, roll_z + 0.7),
                      2.8, 2.9, 0.70, frame_mat='Brass', pin_mat='TackSteel', rot_deg=(0, 0, 0))
    return anchors


def build_saddlebags_pair(ref: WarhorseRef):
    bm = AssetBuilder('SK_Tack_Saddlebags_Mounted', seed=5230, ground_mud_cm=0.0, is_wall_mounted=True)
    anchors = _add_saddlebags_assembly(bm, ref=ref, origin_y_cm=-44.0, top_z_cm=165.0)
    # Exclude thigh bones so saddlebags follow the spine/pelvis croup cleanly without stretching with leg stride!
    bag_excl = ('stirrup_L', 'stirrup_R', 'thigh_L', 'thigh_R', 'calf_L', 'calf_R',
                'tail_01', 'tail_02', 'tail_03', 'tail_04', 'tail_05')
    w_pouch_l = ref.sample_weights_ue(anchors['Pouch_1'], exclude_bones=bag_excl)
    w_pouch_r = ref.sample_weights_ue(anchors['Pouch_-1'], exclude_bones=bag_excl)
    w_bedroll = ref.sample_weights_ue(anchors['Bedroll'], exclude_bones=bag_excl)

    def weight_fn(part_name, p_ue, p_bl):
        if part_name.startswith('Pouch_1'):
            return w_pouch_l
        if part_name.startswith('Pouch_-1'):
            return w_pouch_r
        if part_name.startswith(('TravelBedroll', 'RollSpiral', 'Bedroll')):
            return w_bedroll
        return ref.sample_weights_bl(p_bl, exclude_bones=bag_excl)

    m_mounted = finish_skinned_tack(bm, ref, weight_fn, lod_ratios=(1.0, 0.52, 0.25))

    bs = AssetBuilder('SM_Tack_Saddlebags', seed=5231, ground_mud_cm=12.0)
    _add_saddlebags_assembly(bs, ref=None, origin_y_cm=0.0, top_z_cm=27.8)
    all_z_m = [min((p.matrix_world @ vv.co).z for vv in p.data.vertices) for p in bs.parts]
    z_shift = -min(all_z_m)
    for p in bs.parts:
        p.location.z += z_shift
    bs.add_collider((0.0, 0.0, 18.0), (54.0, 30.0, 36.0))
    m_stand = bs.finish(EXCHANGE_DIR, lod_ratios=(1.0, 0.52, 0.24))
    return m_stand, m_mounted


# ---------------------------------------------------------------------------
# Studio PBR Wiring + Transparent 512x512 Inventory/Shop Icons + QA Contact Renders
# ---------------------------------------------------------------------------

def _wire_preview_pbr_materials():
    tex_sets = {
        'TackSteel': 'T_TackSteel',
        'TackLeather': 'T_TackLeather',
        'TackLeatherDark': 'T_TackLeatherDark',
        'TackBlanket': 'T_TackBlanket',
    }
    for mat_name, prefix in tex_sets.items():
        mat = bpy.data.materials.get(mat_name)
        if not mat:
            continue
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

        bc_img = bpy.data.images.load(str(TEX_DIR / f'{prefix}_BaseColor.png'), check_existing=True)
        bc_node = nt.nodes.new('ShaderNodeTexImage')
        bc_node.image = bc_img
        nt.links.new(bc_node.outputs['Color'], bsdf.inputs['Base Color'])

        orm_img = bpy.data.images.load(str(TEX_DIR / f'{prefix}_ORM.png'), check_existing=True)
        orm_img.colorspace_settings.name = 'Non-Color'
        orm_node = nt.nodes.new('ShaderNodeTexImage')
        orm_node.image = orm_img
        sep = nt.nodes.new('ShaderNodeSeparateColor')
        nt.links.new(orm_node.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], bsdf.inputs['Metallic'])

        nrm_img = bpy.data.images.load(str(TEX_DIR / f'{prefix}_NormalDX.png'), check_existing=True)
        nrm_img.colorspace_settings.name = 'Non-Color'
        nrm_node = nt.nodes.new('ShaderNodeTexImage')
        nrm_node.image = nrm_img
        nmap = nt.nodes.new('ShaderNodeNormalMap')
        nmap.inputs['Strength'].default_value = 0.85
        nt.links.new(nrm_node.outputs['Color'], nmap.inputs['Color'])
        nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])

    for mname, (col, met, rgh) in {
        'Brass': ((0.72, 0.52, 0.19, 1.0), 0.92, 0.26),
        'WaxedThread': ((0.80, 0.66, 0.38, 1.0), 0.0, 0.78),
    }.items():
        mat = bpy.data.materials.get(mname)
        if not mat:
            continue
        mat.use_nodes = True
        nt = mat.node_tree
        nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = col
        bsdf.inputs['Metallic'].default_value = met
        bsdf.inputs['Roughness'].default_value = rgh
        nt.links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])


def _autocrop_square_rgba(png_path: Path, out_size=512, pad_ratio=0.065):
    """Tightly frame rendered transparent icon into crisp square RGBA PNG (~87% fill) using Blender+NumPy."""
    import numpy as np

    img = bpy.data.images.load(str(png_path), check_existing=False)
    try:
        w, h = int(img.size[0]), int(img.size[1])
        px = np.array(img.pixels[:], dtype=np.float32).reshape((h, w, 4))
        ys, xs = np.nonzero(px[:, :, 3] > 0.015)
        if len(xs) == 0:
            return
        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        sub = np.ascontiguousarray(px[y0:y1 + 1, x0:x1 + 1, :])
        ch, cw = sub.shape[0], sub.shape[1]

        inner = int(round(out_size * (1.0 - 2.0 * pad_ratio)))
        scale = min(inner / max(1, cw), inner / max(1, ch))
        nw, nh = max(1, int(round(cw * scale))), max(1, int(round(ch * scale)))

        tmp = bpy.data.images.new('_tack_icon_crop', width=cw, height=ch, alpha=True)
        try:
            tmp.pixels.foreach_set(sub.ravel())
            tmp.scale(nw, nh)
            resized = np.array(tmp.pixels[:], dtype=np.float32).reshape((nh, nw, 4))
        finally:
            bpy.data.images.remove(tmp)

        canvas = np.zeros((out_size, out_size, 4), dtype=np.float32)
        ox = (out_size - nw) // 2
        oy = (out_size - nh) // 2
        canvas[oy:oy + nh, ox:ox + nw, :] = resized

        out_img = bpy.data.images.new('_tack_icon_out', width=out_size, height=out_size, alpha=True)
        try:
            out_img.pixels.foreach_set(canvas.ravel())
            out_img.filepath_raw = str(png_path)
            out_img.file_format = 'PNG'
            out_img.save()
        finally:
            bpy.data.images.remove(out_img)
    finally:
        bpy.data.images.remove(img)


def render_icons_and_qa(ref: WarhorseRef):
    """Render 4 transparent 512x512 studio icons directly from the 4 standalone 3A models + mounted QA shot."""
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    _wire_preview_pbr_materials()

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.use_denoising = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'

    world = bpy.data.worlds.new('TackStudioWorld')
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    if bg:
        bg.inputs[0].default_value = (0.28, 0.30, 0.34, 1.0)
        bg.inputs[1].default_value = 0.85

    def add_light(name, loc, rot, energy, size=1.4, color=(1.0, 0.96, 0.90)):
        ld = bpy.data.lights.new(name, type='AREA')
        ld.energy = energy
        ld.size = size
        ld.color = color
        lo = bpy.data.objects.new(name, ld)
        scene.collection.objects.link(lo)
        lo.location = loc
        lo.rotation_euler = [math.radians(a) for a in rot]
        return lo

    lights = [
        add_light('Key', (1.8, -2.2, 2.2), (50, 0, 38), 320.0, 1.6, (1.0, 0.95, 0.88)),
        add_light('Fill', (-2.1, -1.6, 1.5), (62, 0, -54), 160.0, 2.2, (0.84, 0.92, 1.0)),
        add_light('Rim', (0.3, 2.4, 2.0), (54, 0, 174), 260.0, 1.4, (1.0, 0.92, 0.80)),
    ]

    cam_data = bpy.data.cameras.new('IconCam')
    cam_data.lens = 58.0
    cam = bpy.data.objects.new('IconCam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    def aim_cam(loc, target):
        cam.location = Vector(loc)
        cam.rotation_euler = (Vector(target) - cam.location).to_track_quat('-Z', 'Y').to_euler()

    all_tack_objs = [o for o in bpy.data.objects if o.type == 'MESH' and o != ref.mesh_obj]
    for o in all_tack_objs:
        o.hide_render = True
    ref.mesh_obj.hide_render = True

    # Render all 4 transparent 512x512 studio icons directly from real 3A standalone models!
    scene.render.film_transparent = True
    scene.cycles.samples = 40
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640

    icon_shots = [
        ('SM_Tack_Horseshoes', 'stable_horseshoes.png', (0.14, -0.25, 0.42), (0.0, 0.01, 0.02), (0, 0, 18)),
        ('SM_Tack_Saddle',     'stable_saddle.png',     (1.52, -1.38, 0.96), (0.0, -0.02, 0.44), (0, 0, -34)),
        ('SM_Tack_Barding',    'stable_barding.png',    (0.56, -0.78, 0.48), (0.0, 0.0, 0.28),   (0, 0, -18)),
        ('SM_Tack_Saddlebags', 'stable_saddlebags.png', (0.70, -0.78, 0.50), (0.0, 0.0, 0.20),   (0, 0, -22)),
    ]
    for obj_name, png_name, cloc, ctgt, rdeg in icon_shots:
        obj = bpy.data.objects.get(obj_name)
        if not obj:
            continue
        saved_rot = obj.rotation_euler.copy()
        obj.rotation_euler = Euler([math.radians(a) for a in rdeg], 'XYZ')
        obj.hide_render = False
        aim_cam(cloc, ctgt)
        out_png = ICONS_DIR / png_name
        scene.render.filepath = str(out_png)
        bpy.ops.render.render(write_still=True)
        _autocrop_square_rgba(out_png, out_size=512, pad_ratio=0.065)
        # Also copy icon preview into REVIEW_DIR for easy inspection
        import shutil
        shutil.copy2(out_png, REVIEW_DIR / f'icon_{png_name}')
        obj.rotation_euler = saved_rot
        obj.hide_render = True

    for lo in lights:
        bpy.data.objects.remove(lo, do_unlink=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    ref.mesh_obj.hide_render = False
    for o in all_tack_objs:
        o.hide_render = False


def main():
    SRC_ROOT.mkdir(parents=True, exist_ok=True)
    EXCHANGE_DIR.mkdir(parents=True, exist_ok=True)

    ref = WarhorseRef()
    ref.hide_for_export(True)

    assets = []
    # 1. Horseshoes (standalone SM + 4-hoof skinned SK)
    assets.append(build_horseshoes_standalone())
    assets.append(build_horseshoes_mounted_skinned(ref))

    # 2. Saddle (standalone SM + skinned SK with saddle/blanket/breastplate/stirrups)
    assets.append(build_saddle_standalone())
    assets.append(build_saddle_mounted_skinned(ref))

    # 3. Barding (standalone SM + articulated head/ear skinned SK)
    b_stand, b_mount = build_barding_pair(ref)
    assets.append(b_stand)
    assets.append(b_mount)

    # 4. Saddlebags (standalone SM + croup-following skinned SK)
    sb_stand, sb_mount = build_saddlebags_pair(ref)
    assets.append(sb_stand)
    assets.append(sb_mount)

    render_icons_and_qa(ref)

    bpy.ops.wm.save_as_mainfile(filepath=str(BLEND_OUT))

    manifest = dict(
        revision='HorseTackR52b',
        blender_version='.'.join(map(str, bpy.app.version)),
        blend_file=str(BLEND_OUT),
        warhorse_source=str(WARHORSE_GLB if WARHORSE_GLB.exists() else WARHORSE_FBX),
        assets=assets,
    )
    MANIFEST_OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'HORSE_TACK_R52B_BUILT count={len(assets)} blend={BLEND_OUT}', flush=True)
    for a in assets:
        print(f"  {a['name']:28s} kind={a.get('kind','static'):16s} LOD0={a['lods'][0]['triangles']:6d} tris  size={a['size_cm']}  open={a['open_edges']}  mats={a['materials']}", flush=True)


if __name__ == '__main__':
    main()
