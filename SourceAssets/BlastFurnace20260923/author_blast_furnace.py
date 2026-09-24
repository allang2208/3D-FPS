"""Author the field blast furnace (ore -> ingot) as an editable UE prop.

    & 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup \
        --python SourceAssets/BlastFurnace20260923/author_blast_furnace.py

Design contract (fixed by the host, not by taste):

* Target is the O2 field facility ``高炉``. It is placed on the project's
  20 cm building lattice, so the whole solid must fit an integer number of
  cells. Footprint 6 x 5 x 11 cells = 120 x 100 x 220 cm.
* ``AVoxelBuildPrefabActor::ComputeTransform`` puts the *bounds centre* at the
  centre of the occupied cell box, so a mesh whose bounds are exactly
  X 120 / Y 100 / Z 220 and whose base sits at local z = 0 drops in with
  ``PivotOffsetCm = (0,0,0)``. Bounds are asserted below.
* Blender -> UE is ``(x, -y, z)`` (see ``DungeonWorkbenchKit20260921``
  ``author_kit.py``). UE +X is actor forward, so the tap/forehearth face is
  modelled on **Blender +X**, the blast inlet on Blender +Y, the ash clean-out
  on Blender -X.
* Interface sockets published for the gameplay actor: charging mouth, blast
  flange (``NS_ForgeSparks`` / bellows), tap hole, ember bed, slag notch.

No rendering and no testing: the script only writes geometry, maps, the
editable ``.blend``, the UE ``.fbx`` and a manifest with the numbers a
consumer needs. Visual acceptance stays with the user.
"""
import bmesh
import bpy
import hashlib
import json
import math
import random
import sys
import warnings
from pathlib import Path
from mathutils import Vector

HERE = Path(__file__).resolve().parent
OUT = HERE / 'Authored'
TEX = OUT / 'Textures'
OUT.mkdir(parents=True, exist_ok=True)

# --- lattice and bounds contract ----------------------------------------
CELL_CM = 20.0
FOOTPRINT = (6, 5, 11)                       # X, Y, Z in 20 cm cells
DIM = (FOOTPRINT[0] * 0.20, FOOTPRINT[1] * 0.20, FOOTPRINT[2] * 0.20)
TOP_Z = DIM[2]
BOUND_TOL = 1e-4

# --- layout --------------------------------------------------------------
# A squat masonry shaft on a substantial plinth: the earlier 0.36 m plinth made
# the whole prop read as a chimney rather than a smelter.
STACK_CX, STACK_CY = -0.18, 0.0
# 48 segments: with rounded course arrises a 32-gon still read as a faceted
# cone, which is exactly the "razor corners" complaint.
STACK_SEGMENTS = 48
STACK_PHASE_DEG = -180.0 / STACK_SEGMENTS    # facet centres land on 0/90/180/270
COURSE_COUNT = 14
COURSE_Z0, COURSE_Z1 = 0.47, 1.68
# A taller ledge than the first pass so the edge radius below has room to bite
# without clamp_overlap collapsing it.
COURSE_LEDGE = 0.005
STACK_BODY = [(0.47, 0.352), (0.60, 0.356), (0.80, 0.348), (1.02, 0.330),
              (1.24, 0.310), (1.46, 0.288), (1.60, 0.262), (1.68, 0.238)]
# Taper -> projecting corbel -> straight crown -> flaring lip. An earlier
# bulge-and-waist profile made the prop read as a chimney pot; so did a shaft
# that ran two thirds of the total height.
CORBEL_Z0, CORBEL_Z1, CORBEL_R0, CORBEL_R1 = 1.68, 1.76, 0.242, 0.272
CROWN_Z0, CROWN_Z1, CROWN_R0, CROWN_R1 = 1.76, 2.00, 0.272, 0.262
LIP_Z0, LIP_Z1, LIP_R0, LIP_R1 = 2.00, 2.12, 0.262, 0.276
RIM_Z0, RIM_Z1, RIM_R0, RIM_R1 = 2.12, 2.20, 0.276, 0.266
BOWL_LIP_R = 0.194

PLINTH_CX, PLINTH_CY = -0.18, 0.0
PLINTH_MOULD = (0.82, 0.88)
PLINTH_BODY = (0.78, 0.84)
PLINTH_CAP_BOTTOM = (0.80, 0.86)
PLINTH_CAP_TOP = (0.76, 0.82)
PLINTH_MOULD_Z0, PLINTH_MOULD_Z1 = 0.09, 0.13
PLINTH_BODY_Z1 = 0.40
CAP_TOP_Z = 0.47

BED_Z0, BED_Z1 = 0.0, 0.09
CAST_BED = dict(x0=0.15, x1=0.58, y0=-0.47, y1=0.47, z0=0.09, z1=0.20)

TAP_ARCH_BASE_Z, TAP_ARCH_HALF_W, TAP_ARCH_JAMB = 0.58, 0.070, 0.060
SLAG_NOTCH_Z0, SLAG_NOTCH_Z1 = 0.92, 1.10
ASH_DOOR_Z0, ASH_DOOR_Z1 = 0.54, 0.90
TUYERE_Z0, TUYERE_Z1 = 1.00, 1.30
TUYERE_Z = 1.15
BLOW_PIPE_Y = 0.375
BLOW_PIPE_R = 0.050
FLANGE_R = 0.102
FLANGE_Z = 0.62
BAND_Z = (0.76, 1.18, 1.56)
CROWN_BAND_Z = 1.98
MOULD_X = 0.45
MOULD_Z = CAST_BED['z1']

MATERIAL_SPEC = [
    ('BlastFurnace_Masonry', 2.25, 0.34, 0.33, 0.31, 0.78, 0.0),
    ('BlastFurnace_Firebrick', 0.95, 0.36, 0.29, 0.23, 0.82, 0.0),
    ('BlastFurnace_WroughtIron', 0.50, 0.16, 0.15, 0.15, 0.45, 0.90),
    ('BlastFurnace_ClayLuting', 0.45, 0.30, 0.21, 0.15, 0.88, 0.0),
    ('BlastFurnace_SlagLining', 0.90, 0.18, 0.17, 0.17, 0.60, 0.05),
    ('BlastFurnace_EmberBed', 1.20, 0.13, 0.12, 0.12, 0.80, 0.0),
    ('BlastFurnace_OreLump', 0.45, 0.19, 0.16, 0.14, 0.72, 0.10),
]
# The library brick is a cut-out of the Normandy wall atlas, not a tileable
# texture (the pack has none). It is mapped exactly once: one wrap around the
# shaft (u) and one span from the base of the courses to the rim (v), so no
# seam from tiling can appear. The u seam therefore sits at 315 degrees, which
# is where a vertical tie strap is.

FIREBRICK_UV = dict(u_tile=1.885, v_tile=1.79, u_phase=0.125, v_origin=0.41)
UV_OVERRIDE = {MATERIAL_SPEC[1][0]: FIREBRICK_UV}
MAT = {name: index for index, (name, *_rest) in enumerate(MATERIAL_SPEC)}
MASONRY, FIREBRICK, IRON, CLAY, SLAG, EMBER, ORE = (MAT[s[0]] for s in MATERIAL_SPEC)
UV_METERS = [spec[1] for spec in MATERIAL_SPEC]


# ======================================================================
# scene + materials
# ======================================================================
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 30
    return scene


def principled_of(mat):
    for node in mat.node_tree.nodes:
        if node.type == 'BSDF_PRINCIPLED':
            return node
    return None


def build_materials():
    """Load the generated PBR sets and wire one Principled material each."""
    materials = []
    for name, uv_m, r, g, b, roughness, metallic in MATERIAL_SPEC:
        mat = bpy.data.materials.new(name)
        with warnings.catch_warnings():
            # Blender 5.1 deprecates the flag; enabling it is still the way to
            # get a node tree on a fresh material.
            warnings.simplefilter('ignore', DeprecationWarning)
            mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = principled_of(mat)
        if bsdf is None:
            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            out = next(n for n in nodes if n.type == 'OUTPUT_MATERIAL')
            links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])
        bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
        bsdf.inputs['Roughness'].default_value = roughness
        bsdf.inputs['Metallic'].default_value = metallic
        mat.diffuse_color = (r, g, b, 1.0)
        uv = nodes.new('ShaderNodeUVMap')
        uv.uv_map = 'UVMap'
        for channel, socket in (('BaseColor', 'Base Color'), ('Roughness', 'Roughness'),
                                ('Metallic', 'Metallic'), ('Normal', 'Normal')):
            path = TEX / (name + '_' + channel + '.png')
            if not path.exists():
                raise RuntimeError('Missing furnace map set: ' + str(path))
            node = nodes.new('ShaderNodeTexImage')
            node.image = bpy.data.images.load(str(path))
            node.label = channel
            node.location = (-620, 320 - 240 * len(nodes))
            links.new(uv.outputs['UV'], node.inputs['Vector'])
            if channel == 'Normal':
                node.image.colorspace_settings.name = 'Non-Color'
                nmap = nodes.new('ShaderNodeNormalMap')
                nmap.inputs['Strength'].default_value = 1.0
                links.new(node.outputs['Color'], nmap.inputs['Color'])
                links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
            elif channel in ('Roughness', 'Metallic'):
                node.image.colorspace_settings.name = 'Non-Color'
                links.new(node.outputs['Color'], bsdf.inputs[socket])
            else:
                node.image.colorspace_settings.name = 'sRGB'
                ao_path = TEX / (name + '_AO.png')
                if ao_path.exists():
                    ao = nodes.new('ShaderNodeTexImage')
                    ao.image = bpy.data.images.load(str(ao_path))
                    ao.image.colorspace_settings.name = 'Non-Color'
                    ao.label = 'AO'
                    ao.location = (-620, -320)
                    links.new(uv.outputs['UV'], ao.inputs['Vector'])
                    mix = nodes.new('ShaderNodeMixRGB')
                    mix.blend_type = 'MULTIPLY'
                    mix.inputs[0].default_value = 1.0
                    links.new(node.outputs['Color'], mix.inputs[1])
                    links.new(ao.outputs['Color'], mix.inputs[2])
                    links.new(mix.outputs[0], bsdf.inputs['Base Color'])
                else:
                    links.new(node.outputs['Color'], bsdf.inputs[socket])
        materials.append(mat)
    return materials


# ======================================================================
# mesh authoring helpers
# ======================================================================
class Part:
    """Accumulates vertices and per-face material indices, then emits an object.

    Every part carries all seven slots in the same order so a boolean
    ``material_mode='TRANSFER'`` maps the cutter's material by index and the
    final join keeps one deterministic slot order.
    """

    def __init__(self, name, materials, mapping='planar', smooth=False, bevel=None):
        self.name = name
        self.materials = materials
        self.mapping = mapping
        self.smooth = smooth
        # (width_metres, segments) applied by the project's angle-limited BEVEL
        # recipe, or None for parts whose edges are already round.
        self.bevel = bevel
        self.center = (0.0, 0.0)
        self.verts = []
        self.faces = []

    def add(self, co):
        self.verts.append((float(co[0]), float(co[1]), float(co[2])))
        return len(self.verts) - 1

    def ring(self, points):
        return [self.add(p) for p in points]

    def face(self, indices, mat):
        self.faces.append((tuple(int(i) for i in indices), int(mat)))

    def strip(self, lower, upper, mat, closed=True):
        n = len(lower)
        span = n if closed else n - 1
        for i in range(span):
            j = (i + 1) % n
            self.face((lower[i], lower[j], upper[j], upper[i]), mat)

    def fan(self, apex, ring, mat, flip=False):
        n = len(ring)
        for i in range(n):
            j = (i + 1) % n
            tri = (apex, ring[j], ring[i]) if flip else (apex, ring[i], ring[j])
            self.face(tri, mat)

    def emit(self):
        mesh = bpy.data.meshes.new(self.name + '_Mesh')
        mesh.from_pydata(self.verts, [], [f[0] for f in self.faces])
        if len(mesh.vertices) != len(self.verts):
            raise RuntimeError('Vertex build failed for ' + self.name)
        mesh.update()
        for mat in self.materials:
            mesh.materials.append(mat)
        for polygon, (_idx, mat) in zip(mesh.polygons, self.faces):
            polygon.material_index = mat
            # Smoothing is authored per part here because the join below keeps
            # polygon flags but would drop a per-object custom property.
            polygon.use_smooth = bool(self.smooth)
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        obj['mapping'] = self.mapping
        obj['center'] = tuple(self.center)
        obj['bevel'] = list(self.bevel) if self.bevel else []
        return obj


def apply_edge_radius(obj):
    """The project's Blender edge-rounding recipe.

    Angle-limited bevel, matching SourceAssets/PKMLowpoly20260922 and the
    spirit of the palette's ``EdgeRadiusCm = 1.4`` voxel rounding: only edges
    steeper than 35 degrees are touched, so cylinder facets stay smooth while
    every block arris gets a real radius. Clamp overlap keeps the short course
    ledges from self-intersecting.
    """
    spec = obj.get('bevel')
    if not spec:
        return
    width, segments = spec
    modifier = obj.modifiers.new('EdgeRadius', 'BEVEL')
    modifier.width = width
    modifier.segments = int(segments)
    modifier.limit_method = 'ANGLE'
    modifier.angle_limit = math.radians(35.0)
    modifier.use_clamp_overlap = True
    modifier.miter_outer = 'MITER_ARC'
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=modifier.name)


def weld_and_orient(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    # Weld exact duplicate positions (1 micron) so a coincident ring can never
    # leave a topological border, then orient every face outwards.
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


def angle_grid(segments, phase_deg, cx, cy, radius, z):
    return [(cx + radius * math.cos(math.radians(phase_deg + 360.0 * i / segments)),
             cy + radius * math.sin(math.radians(phase_deg + 360.0 * i / segments)), z)
            for i in range(segments)]


def revolve(name, materials, profile, segment_mats, cx=0.0, cy=0.0, segments=32,
            phase_deg=0.0, closed_loop=False, smooth=False, bevel=None):
    """Solid of revolution. `profile` is (radius, z) from bottom to top.

    A profile whose first and last points coincide is treated as a closed
    loop (a ring with a rectangular section). Radius 0 collapses a ring to a
    pole and generates a triangle fan. Face winding is normalised afterwards,
    so only the profile order matters here.
    """
    if len(segment_mats) != len(profile) - 1:
        raise RuntimeError('%s: %d profile points need %d segments, got %d'
                           % (name, len(profile), len(profile) - 1, len(segment_mats)))
    part = Part(name, materials, mapping='cyl', smooth=smooth, bevel=bevel)
    part.center = (cx, cy)
    if closed_loop:
        # The last profile point repeats the first; reuse that ring instead of
        # building a second one, otherwise the surface is geometrically closed
        # but topologically open (288 border edges on the first run).
        if abs(profile[0][0] - profile[-1][0]) > 1e-9 or abs(profile[0][1] - profile[-1][1]) > 1e-9:
            raise RuntimeError('closed_loop profile must start and end on the same point: ' + name)
        profile = profile[:-1]
    rings = []
    for radius, z in profile:
        if abs(radius) < 1e-9:
            rings.append(('pole', part.add((cx, cy, z))))
        else:
            rings.append(('ring', part.ring(angle_grid(segments, phase_deg, cx, cy, radius, z))))
    count = len(rings)
    for i, mat in enumerate(segment_mats):
        a_kind, a = rings[i]
        b_kind, b = rings[(i + 1) % count] if closed_loop else rings[i + 1]
        if a_kind == 'pole' and b_kind == 'pole':
            continue
        if a_kind == 'pole':
            part.fan(a, b, mat, flip=True)
        elif b_kind == 'pole':
            part.fan(b, a, mat)
        else:
            part.strip(a, b, mat)
    obj = part.emit()
    weld_and_orient(obj)
    return obj


CORNER_ORDER = ((-1, -1), (1, -1), (1, 1), (-1, 1))


def box(name, materials, center, size, mat, smooth=False, bevel=None):
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    part = Part(name, materials, smooth=smooth, bevel=bevel)
    part.center = (cx, cy)
    # The corner list must walk the perimeter in order. A (sy outer, sx inner)
    # comprehension yields (-,-), (+,-), (-,+), (+,+), which turns every side
    # quad into a bowtie whose two triangles face opposite ways.
    lo = part.ring([(cx + sx * hx, cy + sy * hy, cz - hz) for sx, sy in CORNER_ORDER])
    hi = part.ring([(cx + sx * hx, cy + sy * hy, cz + hz) for sx, sy in CORNER_ORDER])
    part.strip(lo, hi, mat)
    part.face(tuple(reversed(lo)), mat)
    part.face(tuple(hi), mat)
    obj = part.emit()
    weld_and_orient(obj)
    return obj


def frustum_box(name, materials, center, size_z, half_xy_low, half_xy_high, mat, bevel=None):
    cx, cy, z0 = center
    z1 = z0 + size_z
    part = Part(name, materials, bevel=bevel)
    part.center = (cx, cy)
    lo = part.ring([(cx + sx * half_xy_low[0], cy + sy * half_xy_low[1], z0) for sx, sy in CORNER_ORDER])
    hi = part.ring([(cx + sx * half_xy_high[0], cy + sy * half_xy_high[1], z1) for sx, sy in CORNER_ORDER])
    part.strip(lo, hi, mat)
    part.face(tuple(reversed(lo)), mat)
    part.face(tuple(hi), mat)
    obj = part.emit()
    weld_and_orient(obj)
    return obj


def chamfered_slab(name, materials, center, size, chamfer, mat, bevel=None):
    """Rectangular slab with the four vertical corners cut at 45 degrees."""
    cx, cy, cz = center
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    c = chamfer
    outline = [(hx, hy - c), (hx - c, hy), (-hx + c, hy), (-hx, hy - c),
               (-hx, -hy + c), (-hx + c, -hy), (hx - c, -hy), (hx, -hy + c)]
    part = Part(name, materials, bevel=bevel)
    part.center = (cx, cy)
    lo = part.ring([(cx + x, cy + y, cz - hz) for x, y in outline])
    hi = part.ring([(cx + x, cy + y, cz + hz) for x, y in outline])
    part.strip(lo, hi, mat)
    part.face(tuple(reversed(lo)), mat)
    part.face(tuple(hi), mat)
    obj = part.emit()
    weld_and_orient(obj)
    return obj


def lerp_profile(points, z):
    if z <= points[0][0]:
        return points[0][1]
    if z >= points[-1][0]:
        return points[-1][1]
    for (z0, r0), (z1, r1) in zip(points, points[1:]):
        if z0 <= z <= z1:
            t = (z - z0) / (z1 - z0)
            return r0 + (r1 - r0) * t
    return points[-1][1]


def wall_radius(z):
    """Outer radius of the shaft at height z: bosh, batter, corbel and crown."""
    if z <= CORBEL_Z0:
        return lerp_profile(STACK_BODY, z)
    if z <= CORBEL_Z1:
        return CORBEL_R0 + (CORBEL_R1 - CORBEL_R0) * (z - CORBEL_Z0) / (CORBEL_Z1 - CORBEL_Z0)
    if z <= CROWN_Z1:
        return CROWN_R0 + (CROWN_R1 - CROWN_R0) * (z - CROWN_Z0) / (CROWN_Z1 - CROWN_Z0)
    if z <= LIP_Z1:
        return LIP_R0 + (LIP_R1 - LIP_R0) * (z - LIP_Z0) / (LIP_Z1 - LIP_Z0)
    return RIM_R0 + (RIM_R1 - RIM_R0) * min(1.0, (z - RIM_Z0) / (RIM_Z1 - RIM_Z0))


def wall_point(angle_deg, z, radial_offset, cx=STACK_CX, cy=STACK_CY):
    r = wall_radius(z) + radial_offset
    a = math.radians(angle_deg)
    return (cx + r * math.cos(a), cy + r * math.sin(a), z)


def wall_frame(angle_deg):
    """Tangential (a) and vertical (b) unit axes on the stack wall."""
    a = math.radians(angle_deg)
    return Vector((-math.sin(a), math.cos(a), 0.0)), Vector((0.0, 0.0, 1.0))


def curved_box(name, materials, angle0, angle1, z0, z1, r_in, r_out, mat,
               angle_steps=6, z_steps=3, bevel=None):
    """A solid patch hugging the stack wall, spanning [angle0, angle1] x [z0, z1]."""
    part = Part(name, materials, mapping='cyl', bevel=bevel)
    part.center = (STACK_CX, STACK_CY)
    angles = [angle0 + (angle1 - angle0) * i / angle_steps for i in range(angle_steps + 1)]
    zs = [z0 + (z1 - z0) * i / z_steps for i in range(z_steps + 1)]
    outer = [[part.add(wall_point(a, z, r_out)) for a in angles] for z in zs]
    inner = [[part.add(wall_point(a, z, r_in)) for a in angles] for z in zs]
    for k in range(z_steps):
        for i in range(angle_steps):
            part.face((outer[k][i], outer[k][i + 1], outer[k + 1][i + 1], outer[k + 1][i]), mat)
            part.face((inner[k][i], inner[k + 1][i], inner[k + 1][i + 1], inner[k][i + 1]), mat)
    for i in range(angle_steps):
        part.face((outer[0][i], inner[0][i], inner[0][i + 1], outer[0][i + 1]), mat)
        part.face((outer[-1][i], outer[-1][i + 1], inner[-1][i + 1], inner[-1][i]), mat)
    for k in range(z_steps):
        part.face((outer[k][0], outer[k + 1][0], inner[k + 1][0], inner[k][0]), mat)
        part.face((outer[k][-1], inner[k][-1], inner[k + 1][-1], outer[k + 1][-1]), mat)
    obj = part.emit()
    weld_and_orient(obj)
    return obj


def arch_outline(half_width, jamb_top, head_segments=10):
    """CCW outline of an arched opening in (tangential, vertical) coordinates."""
    points = [(-half_width, 0.0), (half_width, 0.0), (half_width, jamb_top)]
    for i in range(1, head_segments + 1):
        a = math.pi * i / head_segments
        points.append((half_width * math.cos(a), jamb_top + half_width * math.sin(a)))
    return points


def arch_cutter(materials, angle_deg, base_z, half_width, jamb_top, r_in, r_out, mat):
    """Closed arch prism used to cut a tap arch, slag notch or ash opening."""
    part = Part('ArchCutter', materials, mapping='cyl')
    part.center = (STACK_CX, STACK_CY)
    tangential, vertical = wall_frame(angle_deg)
    radial = Vector((math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg)), 0.0))
    origin = Vector(wall_point(angle_deg, base_z, 0.0))
    outline = arch_outline(half_width, jamb_top)

    def place(a, b, offset):
        return part.add(origin + tangential * a + vertical * b + radial * offset)

    front = [place(a, b, r_out) for a, b in outline]
    back = [place(a, b, r_in) for a, b in outline]
    part.face(tuple(front), mat)
    part.face(tuple(reversed(back)), mat)
    part.strip(back, front, mat)
    obj = part.emit()
    weld_and_orient(obj)
    return obj


def apply_boolean(target, cutter, operation='DIFFERENCE'):
    modifier = target.modifiers.new('cut', 'BOOLEAN')
    modifier.operation = operation
    modifier.solver = 'EXACT'
    modifier.object = cutter
    modifier.material_mode = 'TRANSFER'
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    mesh = cutter.data
    bpy.data.objects.remove(cutter, do_unlink=True)
    bpy.data.meshes.remove(mesh)


def sweep(name, materials, path, profile, segment_mats, smooth=False, bevel=None):
    """Sweep a closed 2D profile along a 3D polyline.

    `profile` is a list of (a, b) offsets in the frame (tangential, vertical);
    `segment_mats` has one entry per profile edge.
    """
    part = Part(name, materials, smooth=smooth, bevel=bevel)
    path = [Vector(p) for p in path]
    part.center = (path[0].x, path[0].y)
    rings = []
    for i, p in enumerate(path):
        tangent = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)])
        if tangent.length < 1e-9:
            tangent = Vector((1.0, 0.0, 0.0))
        tangent.normalize()
        reference = Vector((0.0, 1.0, 0.0)) if abs(tangent.y) < 0.9 else Vector((0.0, 0.0, 1.0))
        right = tangent.cross(reference)
        if right.length < 1e-9:
            right = Vector((0.0, 0.0, 1.0))
        right.normalize()
        up = right.cross(tangent).normalized()
        rings.append(part.ring([tuple(p + right * a + up * b) for a, b in profile]))
    n = len(profile)
    for i in range(len(rings) - 1):
        for k in range(n):
            j = (k + 1) % n
            part.face((rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k]), segment_mats[k])
    part.face(tuple(reversed(rings[0])), segment_mats[0])
    part.face(tuple(rings[-1]), segment_mats[-1])
    obj = part.emit()
    weld_and_orient(obj)
    return obj


def tube(name, materials, path, radius, mat, sides=12, smooth=True):
    profile = [(radius * math.cos(2 * math.pi * i / sides), radius * math.sin(2 * math.pi * i / sides))
               for i in range(sides)]
    return sweep(name, materials, path, profile, [mat] * sides, smooth=smooth)


def hex_bolt(name, materials, center, axis, radius, height, mat, washer=None):
    """A hex head plus an optional square washer; returns every object it made."""
    made = []
    axis = Vector(axis).normalized()
    reference = Vector((0.0, 0.0, 1.0)) if abs(axis.z) < 0.9 else Vector((1.0, 0.0, 0.0))
    u = axis.cross(reference).normalized()
    v = axis.cross(u).normalized()
    base = Vector(center)
    if washer:
        part = Part(name + '_Washer', materials)
        part.center = (base.x, base.y)
        outline = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        lo = part.ring([tuple(base + u * (sx * washer) + v * (sy * washer)) for sx, sy in outline])
        hi = part.ring([tuple(base + axis * washer * 0.8 + u * (sx * washer) + v * (sy * washer))
                        for sx, sy in outline])
        part.strip(lo, hi, mat)
        part.face(tuple(reversed(lo)), mat)
        part.face(tuple(hi), mat)
        obj = part.emit()
        weld_and_orient(obj)
        made.append(obj)
        base = base + axis * washer * 0.8
    part = Part(name, materials)
    part.center = (base.x, base.y)
    lo = part.ring([tuple(base + u * (radius * math.cos(2 * math.pi * i / 6 + 0.4))
                          + v * (radius * math.sin(2 * math.pi * i / 6 + 0.4))) for i in range(6)])
    hi = part.ring([tuple(base + axis * height + u * (radius * math.cos(2 * math.pi * i / 6 + 0.4))
                          + v * (radius * math.sin(2 * math.pi * i / 6 + 0.4))) for i in range(6)])
    part.strip(lo, hi, mat)
    part.face(tuple(reversed(lo)), mat)
    part.face(tuple(hi), mat)
    obj = part.emit()
    weld_and_orient(obj)
    made.append(obj)
    return made


def irregular_lump(name, materials, center, radius, mat, seed, squash=0.72):
    """A closed faceted lump: an icosphere pushed around by a seeded jitter."""
    rng = random.Random(seed)
    mesh = bpy.data.meshes.new(name + '_Mesh')
    bm = bmesh.new()
    try:
        bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1.0)
    except TypeError:
        bmesh.ops.create_icosphere(bm, subdivisions=1, diameter=1.0)
    for vert in bm.verts:
        co = vert.co.normalized()
        wobble = (0.86 + 0.30 * abs(co.x) ** 0.6 + 0.16 * math.sin(3.1 * co.x + seed)
                  + 0.12 * math.cos(2.3 * co.z - seed * 0.7))
        vert.co = co * (rng.uniform(0.90, 1.10) * wobble)
    bm.to_mesh(mesh)
    bm.free()
    for vert in mesh.vertices:
        vert.co.x = vert.co.x * radius + center[0]
        vert.co.y = vert.co.y * radius + center[1]
        vert.co.z = vert.co.z * radius * squash + center[2]
    mesh.update()
    for spec in MATERIAL_SPEC:
        mesh.materials.append(bpy.data.materials[spec[0]])
    for polygon in mesh.polygons:
        polygon.material_index = mat
        polygon.use_smooth = False
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj['mapping'] = 'planar'
    obj['center'] = (center[0], center[1])
    return obj


# ======================================================================
# UV authoring (per part, before the join)
# ======================================================================
def uv_layer(mesh):
    layer = mesh.uv_layers.get('UVMap')
    if layer is None:
        layer = mesh.uv_layers.new(name='UVMap')
    return layer


def uv_name_offset(name):
    digest = hashlib.sha256(name.encode('utf-8')).digest()
    return (digest[0] / 255.0, digest[1] / 255.0)


def assign_uv_planar(obj):
    """Per-face planar projection along the dominant normal axis.

    The tile size is read from each polygon's *own* material. Reading it from
    the object's first slot is wrong here: every part carries all seven slots,
    so slot 0 (masonry, 2.25 m) would stretch the 0.95 m firebrick courses into
    metre-tall blocks.
    """
    mesh = obj.data
    layer = uv_layer(mesh)
    ou, ov = uv_name_offset(obj.name)
    for polygon in mesh.polygons:
        uv_meters = UV_METERS[polygon.material_index]
        axis = max(range(3), key=lambda i: abs(polygon.normal[i]))
        a, b = ((1, 2), (0, 2), (0, 1))[axis]
        flip = polygon.normal[axis] < 0
        for li in polygon.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            u = co[a] / uv_meters + ou
            v = co[b] / uv_meters + ov
            layer.data[li].uv = (-u if flip else u, v)


def assign_uv_cylindrical(obj, center):
    """Wrap around the object's axis; the seam is fixed up per polygon.

    A material may override the mapping entirely (``UV_OVERRIDE``), which is how
    the library brick atlas gets mapped exactly once instead of tiled.
    """
    mesh = obj.data
    layer = uv_layer(mesh)
    cx, cy = center
    circumference = 2.0 * math.pi * 0.30
    ou, ov = uv_name_offset(obj.name)
    for polygon in mesh.polygons:
        uv_meters = UV_METERS[polygon.material_index]
        override = UV_OVERRIDE.get(MATERIAL_SPEC[polygon.material_index][0])
        us = []
        for li in polygon.loop_indices:
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            us.append((math.atan2(co.y - cy, co.x - cx) / (2.0 * math.pi)) % 1.0)
        if max(us) - min(us) > 0.5:
            us = [u + 1.0 if u < 0.5 else u for u in us]
        for li, u in zip(polygon.loop_indices, us):
            co = mesh.vertices[mesh.loops[li].vertex_index].co
            if override:
                # One wrap around the axis, one span up the shaft, no random
                # offset: any offset would slide the single-shot window off the
                # clean block of the atlas.
                layer.data[li].uv = ((u + override['u_phase']) * circumference / override['u_tile'],
                                     (co.z - override['v_origin']) / override['v_tile'])
            else:
                layer.data[li].uv = (u * circumference / uv_meters + ou, co.z / uv_meters + ov)


def assign_uvs(obj):
    mapping = obj.get('mapping', 'planar')
    center = tuple(obj.get('center', (STACK_CX, STACK_CY)))
    if mapping == 'cyl':
        assign_uv_cylindrical(obj, center)
    else:
        assign_uv_planar(obj)


# ======================================================================
# the furnace
# ======================================================================
def build_stack(materials):
    """One closed solid of revolution: base, 14 masonry courses, corbel,
    crown and the interior charging bowl.

    A single solid keeps the shell closed and manifold; the per-course ledges
    are real profile steps, so the silhouette gets shadow lines without
    stacking coplanar caps.
    """
    profile = [(0.0, 0.41)]
    segment_mats = []

    def push(radius, z, mat):
        profile.append((radius, z))
        segment_mats.append(mat)

    push(wall_radius(COURSE_Z0) + COURSE_LEDGE, 0.41, FIREBRICK)
    push(wall_radius(COURSE_Z0) + COURSE_LEDGE, COURSE_Z0, FIREBRICK)
    height = (COURSE_Z1 - COURSE_Z0) / COURSE_COUNT
    for i in range(COURSE_COUNT):
        z0 = COURSE_Z0 + i * height
        z1 = z0 + height
        # A couple of millimetres of per-course wander keeps the battered shaft
        # from reading as a perfect turned cone.
        wander = 0.0018 * math.sin(i * 2.399) + 0.0011 * math.cos(i * 5.117)
        push(wall_radius(z1) - COURSE_LEDGE + wander, z1, FIREBRICK)
        if i < COURSE_COUNT - 1:
            push(wall_radius(z1) + COURSE_LEDGE + wander, z1, FIREBRICK)
    # Projecting corbel, straight crown, flaring lip and rounded rim.
    push(CORBEL_R0 + 0.004, CORBEL_Z0, FIREBRICK)
    push(CORBEL_R1, CORBEL_Z1, FIREBRICK)
    push(CROWN_R0, CROWN_Z0, FIREBRICK)
    push(CROWN_R1, CROWN_Z1, FIREBRICK)
    push(LIP_R0, LIP_Z0, FIREBRICK)
    push(LIP_R1, LIP_Z1, FIREBRICK)
    push(RIM_R0, RIM_Z0, FIREBRICK)
    push(RIM_R1, RIM_Z1, FIREBRICK)
    # Rim top face, then down the inside of the charging bowl.
    push(BOWL_LIP_R, RIM_Z1, FIREBRICK)
    push(0.180, 2.10, FIREBRICK)
    push(0.190, 1.98, FIREBRICK)
    push(0.196, 1.90, FIREBRICK)
    push(0.190, 1.86, SLAG)
    # Ember bed: the runtime may swap this slot for an emissive material.
    push(0.150, 1.852, EMBER)
    push(0.096, 1.844, EMBER)
    push(0.042, 1.840, EMBER)
    profile.append((0.0, 1.839))
    segment_mats.append(EMBER)

    return revolve('Stack', materials, profile, segment_mats,
                   cx=STACK_CX, cy=STACK_CY, segments=STACK_SEGMENTS,
                   phase_deg=STACK_PHASE_DEG, smooth=True, bevel=(0.0015, 3))


def build_foundation(materials):
    parts = []
    parts.append(chamfered_slab('Foundation_Bed', materials, (0.0, 0.0, (BED_Z0 + BED_Z1) / 2.0),
                                (DIM[0], DIM[1], BED_Z1 - BED_Z0), 0.075, MASONRY, bevel=(0.008, 3)))
    parts.append(box('Plinth_BaseMould', materials,
                     (PLINTH_CX, PLINTH_CY, (PLINTH_MOULD_Z0 + PLINTH_MOULD_Z1) / 2.0),
                     (PLINTH_MOULD[0], PLINTH_MOULD[1], PLINTH_MOULD_Z1 - PLINTH_MOULD_Z0), MASONRY,
                     bevel=(0.006, 3)))
    parts.append(box('Plinth_Body', materials,
                     (PLINTH_CX, PLINTH_CY, (PLINTH_MOULD_Z1 + PLINTH_BODY_Z1) / 2.0),
                     (PLINTH_BODY[0], PLINTH_BODY[1], PLINTH_BODY_Z1 - PLINTH_MOULD_Z1), MASONRY,
                     bevel=(0.006, 3)))
    parts.append(frustum_box('Plinth_Cap', materials, (PLINTH_CX, PLINTH_CY, PLINTH_BODY_Z1),
                             CAP_TOP_Z - PLINTH_BODY_Z1,
                             (PLINTH_CAP_BOTTOM[0] / 2.0, PLINTH_CAP_BOTTOM[1] / 2.0),
                             (PLINTH_CAP_TOP[0] / 2.0, PLINTH_CAP_TOP[1] / 2.0), MASONRY,
                             bevel=(0.006, 3)))
    # Rammed loam casting bed, not a slag-black hole: the previous version read
    # as an opening in the foundation.
    parts.append(box('Casting_Bed', materials,
                     ((CAST_BED['x0'] + CAST_BED['x1']) / 2.0,
                      (CAST_BED['y0'] + CAST_BED['y1']) / 2.0,
                      (CAST_BED['z0'] + CAST_BED['z1']) / 2.0),
                     (CAST_BED['x1'] - CAST_BED['x0'], CAST_BED['y1'] - CAST_BED['y0'],
                      CAST_BED['z1'] - CAST_BED['z0']), CLAY, bevel=(0.005, 3)))
    return parts


def build_tap_breast(materials):
    """Clay breast with a real arched tap hole (boolean). Nothing pours out of it.

    The sloping launder and its two piers used to run from this arch down to the
    casting bed. The user asked for that flow to be removed rather than frozen:
    it read as a stream of material leaving the furnace. The runtime will supply
    its own molten-material asset, so the arch now opens straight onto the empty
    casting bed with the ingot moulds waiting in front of it.
    """
    parts = []
    breast = curved_box('Tap_Breast', materials, angle0=-15.0, angle1=15.0,
                        z0=0.50, z1=0.88, r_in=-0.02, r_out=0.052, mat=CLAY,
                        angle_steps=7, z_steps=4, bevel=(0.003, 3))
    cutter = arch_cutter(materials, 0.0, base_z=TAP_ARCH_BASE_Z, half_width=TAP_ARCH_HALF_W,
                         jamb_top=TAP_ARCH_JAMB, r_in=-0.05, r_out=0.10, mat=SLAG)
    apply_boolean(breast, cutter)
    parts.append(breast)
    return parts


def build_slag_notch(materials):
    parts = []
    notch = curved_box('Slag_Notch', materials, angle0=-10.0, angle1=10.0,
                       z0=SLAG_NOTCH_Z0, z1=SLAG_NOTCH_Z1, r_in=-0.02, r_out=0.046, mat=CLAY,
                       angle_steps=5, z_steps=3, bevel=(0.0025, 2))
    cutter = arch_cutter(materials, 0.0, base_z=0.955, half_width=0.040, jamb_top=0.032,
                         r_in=-0.05, r_out=0.09, mat=SLAG)
    apply_boolean(notch, cutter)
    parts.append(notch)
    return parts


def build_ash_door(materials):
    """Arched clean-out on the back face: cut recess, iron frame, leaf, hinges, latch."""
    parts = []
    frame = curved_box('AshDoor_Frame', materials, angle0=180.0 - 16.0, angle1=180.0 + 16.0,
                       z0=ASH_DOOR_Z0, z1=ASH_DOOR_Z1, r_in=-0.02, r_out=0.046, mat=IRON,
                       angle_steps=6, z_steps=4, bevel=(0.0025, 2))
    cutter = arch_cutter(materials, 180.0, base_z=ASH_DOOR_Z0 + 0.055, half_width=0.080,
                         jamb_top=0.075, r_in=-0.05, r_out=0.09, mat=SLAG)
    apply_boolean(frame, cutter)
    parts.append(frame)
    leaf = curved_box('AshDoor_Leaf', materials, angle0=180.0 - 10.5, angle1=180.0 + 10.5,
                      z0=ASH_DOOR_Z0 + 0.070, z1=ASH_DOOR_Z1 - 0.070, r_in=0.024, r_out=0.042,
                      mat=IRON, angle_steps=6, z_steps=3, bevel=(0.002, 2))
    parts.append(leaf)
    for index, z in enumerate((0.62, 0.82)):
        # Compact hardware: with the shaft at 35 cm radius there is only ~7 cm
        # between the back wall and the 120 cm X bound, so the barrel is short.
        centre = Vector(wall_point(180.0 + 10.5, z, 0.048))
        radial = Vector(wall_point(180.0 + 10.5, z, 1.0)) - Vector(wall_point(180.0 + 10.5, z, 0.0))
        parts.append(tube('AshDoor_Hinge_%d' % (index + 1), materials,
                          [tuple(centre - radial * 0.014), tuple(centre + radial * 0.014)],
                          0.011, IRON, sides=8))
    latch = wall_point(180.0 - 11.5, 0.72, 0.044)
    parts.append(box('AshDoor_Latch', materials, (latch[0] - 0.004, latch[1], latch[2]),
                     (0.032, 0.022, 0.018), IRON, bevel=(0.002, 2)))
    return parts


def build_bands(materials):
    """Three bolted iron bands with vertical tie straps down the shaft."""
    parts = []
    for index, z in enumerate(BAND_Z):
        inner, outer = wall_radius(z) - 0.012, wall_radius(z) + 0.022
        profile = [(inner, z - 0.036), (outer, z - 0.032), (outer, z + 0.032),
                   (inner, z + 0.036), (inner, z - 0.036)]
        parts.append(revolve('Stack_Band_%d' % (index + 1), materials, profile,
                             [IRON] * 4, cx=STACK_CX, cy=STACK_CY,
                             segments=STACK_SEGMENTS, phase_deg=STACK_PHASE_DEG,
                             closed_loop=True, smooth=True, bevel=(0.0025, 2)))
        for bolt_index, angle in enumerate((45.0, 135.0, 225.0, 315.0)):
            base = Vector(wall_point(angle, z, 0.020))
            axis = Vector(wall_point(angle, z, 1.0)) - Vector(wall_point(angle, z, 0.0))
            parts += hex_bolt('Stack_Bolt_%d_%d' % (index + 1, bolt_index + 1), materials,
                              tuple(base), tuple(axis), 0.020, 0.019, IRON, washer=0.029)
    for index, angle in enumerate((45.0, 135.0, 225.0, 315.0)):
        path = [wall_point(angle, z, 0.012) for z in (0.52, 0.70, 0.90, 1.10, 1.30, 1.50, 1.66, 1.74)]
        parts.append(sweep('Stack_Strap_%d' % (index + 1), materials, path,
                           [(-0.027, 0.0), (0.027, 0.0), (0.027, 0.014), (-0.027, 0.014)],
                           [IRON] * 4, bevel=(0.0015, 2)))
    inner, outer = wall_radius(CROWN_BAND_Z) - 0.012, wall_radius(CROWN_BAND_Z) + 0.020
    profile = [(inner, CROWN_BAND_Z - 0.028), (outer, CROWN_BAND_Z - 0.025),
               (outer, CROWN_BAND_Z + 0.025), (inner, CROWN_BAND_Z + 0.028), (inner, CROWN_BAND_Z - 0.028)]
    parts.append(revolve('Crown_Band', materials, profile, [IRON] * 4,
                         cx=STACK_CX, cy=STACK_CY, segments=STACK_SEGMENTS,
                         phase_deg=STACK_PHASE_DEG, closed_loop=True, smooth=True,
                         bevel=(0.0025, 2)))
    return parts


def build_tuyere(materials):
    """Tuyere plate, nozzle and the blast pipe ending in a coupling flange."""
    parts = []
    parts.append(curved_box('Tuyere_Luting', materials, angle0=90.0 - 19.0, angle1=90.0 + 19.0,
                            z0=TUYERE_Z0 - 0.05, z1=TUYERE_Z1 + 0.05, r_in=-0.02, r_out=0.018,
                            mat=CLAY, angle_steps=6, z_steps=4, bevel=(0.003, 2)))
    parts.append(curved_box('Tuyere_Plate', materials, angle0=90.0 - 20.0, angle1=90.0 + 20.0,
                            z0=TUYERE_Z0, z1=TUYERE_Z1, r_in=-0.02, r_out=0.038, mat=IRON,
                            angle_steps=5, z_steps=3, bevel=(0.003, 2)))
    for bolt_index, (angle, z) in enumerate(((70.0, 1.04), (110.0, 1.04), (70.0, 1.26), (110.0, 1.26))):
        base = Vector(wall_point(angle, z, 0.038))
        axis = Vector(wall_point(angle, z, 1.0)) - Vector(wall_point(angle, z, 0.0))
        parts += hex_bolt('Tuyere_Bolt_%d' % (bolt_index + 1), materials, tuple(base),
                          tuple(axis), 0.016, 0.015, IRON)
    # Nozzle: a tapered cone from the plate through the wall.
    nozzle_start = wall_point(90.0, TUYERE_Z, 0.030)
    nozzle_end = wall_point(90.0, TUYERE_Z, 0.072)
    parts.append(sweep('Tuyere_Nozzle', materials, [nozzle_start, nozzle_end],
                       [(0.095 * math.cos(2 * math.pi * i / 14), 0.095 * math.sin(2 * math.pi * i / 14))
                        for i in range(14)], [IRON] * 14, smooth=True))
    # Blast pipe: out of the nozzle, then straight down to the coupling flange.
    path = [(STACK_CX, 0.10, TUYERE_Z), (STACK_CX, 0.30, TUYERE_Z),
            (STACK_CX, BLOW_PIPE_Y, TUYERE_Z - 0.024),
            (STACK_CX, BLOW_PIPE_Y, 1.00), (STACK_CX, BLOW_PIPE_Y, 0.80),
            (STACK_CX, BLOW_PIPE_Y, FLANGE_Z + 0.020)]
    parts.append(tube('Blast_Pipe', materials, path, BLOW_PIPE_R, IRON, sides=14))
    parts.append(revolve('Blast_Flange', materials,
                         [(0.055, FLANGE_Z - 0.012), (FLANGE_R, FLANGE_Z - 0.004),
                          (FLANGE_R, FLANGE_Z + 0.012), (0.055, FLANGE_Z + 0.020),
                          (0.055, FLANGE_Z - 0.012)],
                         [IRON] * 4, cx=STACK_CX, cy=BLOW_PIPE_Y, segments=16, closed_loop=True,
                         smooth=True, bevel=(0.0025, 2)))
    for i in range(6):
        a = 2 * math.pi * i / 6
        parts += hex_bolt('Blast_Flange_Bolt_%d' % (i + 1), materials,
                          (STACK_CX + 0.082 * math.cos(a), BLOW_PIPE_Y + 0.082 * math.sin(a), FLANGE_Z - 0.012),
                          (0.0, 0.0, -1.0), 0.012, 0.016, IRON)
    parts.append(box('Blast_Pipe_Bracket', materials,
                     (STACK_CX, wall_radius(0.86) + 0.024, 0.86), (0.055, 0.12, 0.022), IRON,
                     bevel=(0.003, 2)))
    return parts


def build_moulds(materials):
    """Three cast-iron ingot moulds on the casting bed, open-topped and empty."""
    parts = []
    for index, y in enumerate((-0.15, 0.0, 0.15)):
        body = frustum_box('IngotMould_%d_Body' % (index + 1), materials,
                           (MOULD_X, y, MOULD_Z), 0.085,
                           (0.100, 0.0675), (0.104, 0.0705), IRON, bevel=(0.0035, 2))
        # The cut faces take the cutter's material. Iron, not slag: the mould is
        # an empty iron tool, and the cooled-ingot look was removed with the
        # rest of the flowed material.
        cutter = frustum_box('IngotMould_%d_Cutter' % (index + 1), materials,
                             (MOULD_X, y, MOULD_Z + 0.018), 0.10,
                             (0.0675, 0.0375), (0.0875, 0.0525), IRON)
        apply_boolean(body, cutter)
        parts.append(body)
        for sign in (-1, 1):
            parts.append(box('IngotMould_%d_Ear_%d' % (index + 1, sign), materials,
                             (MOULD_X + sign * 0.105, y, MOULD_Z + 0.070),
                             (0.030, 0.026, 0.022), IRON, bevel=(0.0025, 2)))
    return parts


def build_charge_and_spill(materials):
    """Ore lumps waiting to be charged.

    Every free-standing piece of frozen slag was removed on request; the
    runtime will supply its own molten-material asset for the launder.
    """
    parts = []
    heap = [(0.235, -0.345, 0.056), (0.300, -0.372, 0.050), (0.268, -0.282, 0.046),
            (0.345, -0.318, 0.043), (0.214, -0.256, 0.039), (0.312, -0.424, 0.047)]
    for index, (x, y, radius) in enumerate(heap):
        parts.append(irregular_lump('Ore_Lump_%d' % (index + 1), materials,
                                    (x, y, MOULD_Z + radius * 0.72), radius, ORE,
                                    7000 + index * 137, squash=0.72))
    return parts


# ======================================================================
# finalise, verify, export
# ======================================================================
def finalize(obj):
    """Mark hard edges by dihedral angle, then freeze the split normals.

    Order matters (see asset-model-workflow): smoothing is already authored
    per polygon, and the custom normals come *after* it. Setting custom
    normals on a flat-shaded mesh and smoothing afterwards silently drops
    every hard edge.
    """
    mesh = obj.data
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    # The exact boolean solver can leave zero-area slivers along a cut, and a
    # cramped bevel can collapse a narrow facet; collapse both before the
    # normals are frozen. 0.05 mm is far below any authored feature here.
    bmesh.ops.dissolve_degenerate(bm, dist=5e-5, edges=bm.edges[:])
    threshold = math.radians(35.0)
    for edge in bm.edges:
        if len(edge.link_faces) == 2:
            edge.smooth = edge.calc_face_angle(0.0) < threshold
        else:
            edge.smooth = False
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    normals = [n.vector.copy() for n in mesh.corner_normals]
    mesh.normals_split_custom_set(normals)
    mesh.update()


def hard_edge_report(mesh):
    """Count vertices where loop normals disagree by more than 25 degrees."""
    per_vertex = {}
    for loop in mesh.loops:
        per_vertex.setdefault(loop.vertex_index, []).append(loop.normal.copy())
    hard = 0
    worst = 0.0
    worst_at = None
    for index, normals in per_vertex.items():
        if len(normals) < 2:
            continue
        angle = 0.0
        for i in range(len(normals)):
            for j in range(i + 1, len(normals)):
                dot = max(-1.0, min(1.0, normals[i].dot(normals[j])))
                angle = max(angle, math.degrees(math.acos(dot)))
        if angle > worst:
            worst, worst_at = angle, tuple(round(c * 100, 1) for c in mesh.vertices[index].co)
        if angle > 25.0:
            hard += 1
    return hard, worst, worst_at


def topology_report(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    boundary = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonmanifold = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    loose = sum(1 for v in bm.verts if not v.link_faces)
    degenerate = sum(1 for f in bm.faces if f.calc_area() < 1e-9)
    bm.free()
    return dict(vertices=len(obj.data.vertices), polygons=len(obj.data.polygons),
                boundary_edges=boundary, non_manifold_edges=nonmanifold,
                loose_vertices=loose, degenerate_faces=degenerate)


def main():
    reset_scene()
    materials = build_materials()

    parts = []
    parts.append(build_stack(materials))
    parts += build_foundation(materials)
    parts += build_tap_breast(materials)
    parts += build_slag_notch(materials)
    parts += build_ash_door(materials)
    parts += build_bands(materials)
    parts += build_tuyere(materials)
    parts += build_moulds(materials)
    parts += build_charge_and_spill(materials)

    # Edge rounding runs after every boolean and before the UVs, because it
    # changes topology.
    for obj in parts:
        apply_edge_radius(obj)
    for obj in parts:
        assign_uvs(obj)

    part_bounds = {}
    for obj in parts:
        coords = [obj.matrix_world @ v.co for v in obj.data.vertices]
        part_bounds[obj.name] = dict(
            x=[round(min(c.x for c in coords) * 100, 2), round(max(c.x for c in coords) * 100, 2)],
            y=[round(min(c.y for c in coords) * 100, 2), round(max(c.y for c in coords) * 100, 2)],
            z=[round(min(c.z for c in coords) * 100, 2), round(max(c.z for c in coords) * 100, 2)],
            triangles=sum(len(p.vertices) - 2 for p in obj.data.polygons))

    # Name the parts that break the cell box instead of only reporting that the
    # final mesh is oversized.
    limit = dict(x=DIM[0] / 2.0 * 100, y=DIM[1] / 2.0 * 100, z=DIM[2] * 100)
    violations = []
    for name, bounds in part_bounds.items():
        if (bounds['x'][0] < -limit['x'] - 1e-6 or bounds['x'][1] > limit['x'] + 1e-6
                or bounds['y'][0] < -limit['y'] - 1e-6 or bounds['y'][1] > limit['y'] + 1e-6
                or bounds['z'][0] < -1e-6 or bounds['z'][1] > limit['z'] + 1e-6):
            violations.append((name, bounds))
    for name, bounds in violations:
        print('BOUNDS_VIOLATION %s x=%s y=%s z=%s' % (name, bounds['x'], bounds['y'], bounds['z']))

    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    furnace = bpy.context.object
    furnace.name = 'SM_BlastFurnace'
    furnace.data.name = 'SM_BlastFurnace_Mesh'

    triangulate = furnace.modifiers.new('Export_triangulation', 'TRIANGULATE')
    triangulate.quad_method = 'BEAUTY'
    triangulate.ngon_method = 'BEAUTY'
    bpy.ops.object.modifier_apply(modifier=triangulate.name)

    finalize(furnace)

    coords = [v.co for v in furnace.data.vertices]
    bounds = dict(
        x=[min(c.x for c in coords), max(c.x for c in coords)],
        y=[min(c.y for c in coords), max(c.y for c in coords)],
        z=[min(c.z for c in coords), max(c.z for c in coords)])
    size = [bounds[axis][1] - bounds[axis][0] for axis in ('x', 'y', 'z')]
    size_error = [abs(size[i] - DIM[i]) for i in range(3)]
    # UE space swaps Y, so the bounds centre must be zero on X and Y and the
    # base must sit exactly on z = 0 for PivotOffsetCm = (0,0,0).
    centre_error = [abs(bounds['x'][0] + bounds['x'][1]) / 2.0,
                    abs(bounds['y'][0] + bounds['y'][1]) / 2.0,
                    abs(bounds['z'][0])]
    topo = topology_report(furnace)
    hard, worst, worst_at = hard_edge_report(furnace.data)
    slot_names = [mat.name for mat in furnace.data.materials]

    interfaces = {
        'ChargingMouth': [STACK_CX, 0.0, TOP_Z],
        'EmberBed': [STACK_CX, 0.0, 1.86],
        'BlastFlange': [STACK_CX, BLOW_PIPE_Y, FLANGE_Z],
        'TapHole': [round(wall_radius(TAP_ARCH_BASE_Z) + STACK_CX, 4), 0.0, TAP_ARCH_BASE_Z + 0.055],
        'SlagNotch': [round(wall_radius(0.955) + STACK_CX, 4), 0.0, 0.955],
        'AshCleanOut': [round(STACK_CX - wall_radius(0.70), 4), 0.0, 0.70],
        'ForehearthFloor': [0.375, 0.0, MOULD_Z],
        'CastingBedCentre': [(CAST_BED['x0'] + CAST_BED['x1']) / 2.0, 0.0, MOULD_Z],
    }
    interfaces_ue = {key: [round(v[0] * 100, 2), round(-v[1] * 100, 2), round(v[2] * 100, 2)]
                     for key, v in interfaces.items()}

    ok = (max(size_error) < BOUND_TOL and max(centre_error) < BOUND_TOL
          and topo['boundary_edges'] == 0 and topo['non_manifold_edges'] == 0
          and topo['loose_vertices'] == 0 and topo['degenerate_faces'] == 0
          and len(slot_names) == len(MATERIAL_SPEC) and hard > 0)

    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.file.pack_all()
    blend = OUT / 'BlastFurnace.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))

    bpy.ops.object.select_all(action='DESELECT')
    furnace.select_set(True)
    bpy.context.view_layer.objects.active = furnace
    fbx = OUT / 'SM_BlastFurnace.fbx'
    bpy.ops.export_scene.fbx(
        filepath=str(fbx), use_selection=True, object_types={'MESH'}, apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL', axis_forward='-Y', axis_up='Z',
        use_mesh_modifiers=True, mesh_smooth_type='FACE', use_tspace=True,
        add_leaf_bones=False, bake_anim=False)

    report = dict(
        id='blast_furnace',
        display_name='冶炼高炉',
        purpose='field facility, ore -> ingot; placeable on the 20 cm building lattice',
        blender='5.1',
        author_script='author_blast_furnace.py',
        footprint_cells=list(FOOTPRINT),
        intended_dimensions_cm=[DIM[0] * 100, DIM[1] * 100, DIM[2] * 100],
        measured_dimensions_cm=[round(v * 100, 4) for v in size],
        bounds_min_cm=[round(bounds[a][0] * 100, 4) for a in ('x', 'y', 'z')],
        bounds_max_cm=[round(bounds[a][1] * 100, 4) for a in ('x', 'y', 'z')],
        size_error_cm=[round(v * 100, 5) for v in size_error],
        centre_error_cm=[round(v * 100, 5) for v in centre_error],
        pivot='bounds centred on X/Y, base plane on Z = 0; PivotOffsetCm = (0,0,0)',
        blender_to_ue='(x, -y, z) in centimetres',
        orient_ue_forward='tap/forehearth on +X, blast inlet on +Y, ash door on -X',
        polygon_count=topo['polygons'],
        triangle_count=sum(len(p.vertices) - 2 for p in furnace.data.polygons),
        topology=topo,
        hard_edge_vertices=hard,
        max_loop_normal_angle_deg=round(worst, 2),
        max_loop_normal_angle_at_cm=list(worst_at) if worst_at else None,
        material_slots=slot_names,
        uv_layer='UVMap (authored: cylindrical on the shaft, planar elsewhere; tile size per material)',
        interface_points_blender_m={k: [round(c, 4) for c in v] for k, v in interfaces.items()},
        interface_points_ue_cm=interfaces_ue,
        parts=part_bounds,
        fbx=str(fbx),
        blend=str(blend),
        textures='Authored/Textures/*.png (7 materials x BaseColor/Normal/Roughness/Metallic/AO)',
        rendered=False,
        runtime_tested=False,
        self_check_ok=bool(ok),
        geometry_notes=[
            'One closed solid of revolution carries the shaft, corbel, crown and ember bed.',
            'Tap arch, slag notch and ash clean-out are real boolean cut recesses, not painted decals.',
            'Hard edges come from smoothing first, then a custom split-normal freeze.',
            'Block arrises carry an angle-limited 1.5-8 mm BEVEL (35 deg limit, clamp overlap), '
            'the project recipe used for the rounded voxel blocks; the shaft is a 48-gon and is '
            'smooth-shaded so only edges past 35 deg stay creased.',
            'No frozen slag, metal or launder is modelled: the tap arch, the casting bed and the '
            'empty moulds are structure, and the flow itself is left for a runtime asset.',
        ])
    (OUT / 'manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    print('BLAST_FURNACE_AUTHORED')
    print(json.dumps({k: report[k] for k in (
        'measured_dimensions_cm', 'size_error_cm', 'centre_error_cm', 'triangle_count',
        'topology', 'hard_edge_vertices', 'max_loop_normal_angle_deg',
        'max_loop_normal_angle_at_cm', 'material_slots', 'self_check_ok',
        'interface_points_ue_cm')}, ensure_ascii=False))
    if not ok:
        print('BLAST_FURNACE_SELF_CHECK_FAILED')
        sys.exit(1)


main()
