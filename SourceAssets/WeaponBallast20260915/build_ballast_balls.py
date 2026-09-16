"""Build the three weapon ballast balls (硬化配重 / 符文配重 / 魔力球配重).

Usage:
    blender --background --factory-startup --python build_ballast_balls.py -- <out_dir>

Author entry for the 2026-09-15 ballast request. The three variants share one
mounting interface so they can be swapped in the same gunsmith slot:

    +Z (outward)  ball / housing
    z = 0         seating plane (object origin, interface datum)
    -Z (inward)   M6 stud that enters the host socket

All dimensions are metres in the Blender scene and metres in the exported
geometry; the FBX exporter writes the centimetre scale Unreal expects.
"""

import json
import math
import os
import sys

import bpy
import bmesh

# ---------------------------------------------------------------- dimensions

BALL_RADIUS = 0.017          # Ø34 mm ball
STUD_RADIUS = 0.003          # M6 stud
STUD_LENGTH = 0.010          # 10 mm into the host
FLANGE_RADIUS = 0.007        # Ø14 mm seating flange
FLANGE_HEIGHT = 0.003        # 3 mm
SEAT_Z = FLANGE_HEIGHT       # ball sits on top of the flange
BALL_CENTER_Z = SEAT_Z + BALL_RADIUS

HEX_ACROSS_FLATS = 0.030     # hardened variant: 6 flats cut into the ball

RUNE_GROOVE_WIDTH = 0.0025   # 2.5 mm engraved grooves: has to read at preview scale
RUNE_GROOVE_DEPTH = 0.0025   # depth at the tangent point; tapers with the sphere
RUNE_CUTTER_THICKNESS = 0.0058   # radial size: inner face grazes the surface

SOCKET_RADIUS = 0.009        # magic variant: Ø18 mm bore
SOCKET_DEPTH = 0.008
CORE_RADIUS = 0.008          # Ø16 mm orb, lifted so it clears the socket rim
CORE_TOP_Z = 0.0378          # 0.8 mm proud of the ball top: reads as a magic orb
BEZEL_MAJOR = 0.009          # ring at the rim where the bore meets the surface
BEZEL_MINOR = 0.0012


def log(message):
    print("[ballast] " + message)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    # Blender writes .blend1 backups on every save; the author folder keeps only
    # the current sources.
    try:
        bpy.context.preferences.filepaths.save_version = 0
    except Exception:
        pass
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.unit_settings.length_unit = 'MILLIMETERS'


def material(name, base_color, metallic, roughness, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission is not None:
        # Blender 4.x/5.x share these socket names.
        if "Emission Color" in bsdf.inputs:
            bsdf.inputs["Emission Color"].default_value = emission
            bsdf.inputs["Emission Strength"].default_value = emission_strength
        else:
            bsdf.inputs["Emission"].default_value = emission
            bsdf.inputs["Emission Strength"].default_value = emission_strength
    return mat


def shade_smooth(obj, angle_deg=35.0):
    for face in obj.data.polygons:
        face.use_smooth = True
    try:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle_deg))
    except Exception:
        pass  # older builds: plain smooth shading is enough for a sphere


def set_active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def join(objects, name):
    objects = [o for o in objects if o is not None]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    if len(objects) > 1:
        bpy.ops.object.join()
    result = bpy.context.view_layer.objects.active
    result.name = name
    result.data.name = name + "_Mesh"
    return result


def apply_boolean(target, cutter, operation='DIFFERENCE'):
    set_active(target)
    mod = target.modifiers.new("bool_" + cutter.name, 'BOOLEAN')
    mod.operation = operation
    mod.object = cutter
    try:
        mod.solver = 'EXACT'
    except Exception:
        pass
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)
    return target


def add_sphere(radius, location, segments=32, rings=16, name="Sphere"):
    try:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments,
                                             ring_count=rings, location=location)
    except TypeError:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, segments=segments,
                                             location=location)
    obj = bpy.context.object
    obj.name = name
    return obj


def add_cylinder(radius, depth, location, vertices=32, name="Cylinder"):
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth,
                                        vertices=vertices, location=location)
    obj = bpy.context.object
    obj.name = name
    return obj


def add_box(size, location, name="Box"):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (size[0], size[1], size[2])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return obj


def add_torus(major, minor, location, name="Torus"):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor,
                                     major_segments=32, minor_segments=12,
                                     location=location)
    obj = bpy.context.object
    obj.name = name
    return obj


def add_hex_prism(across_flats, height, location, name="HexPrism"):
    # Blender inscribes a 6-sided cylinder in the given radius, so convert the
    # wanted across-flats (inradius) into the circumradius the operator expects.
    circumradius = (across_flats / 2.0) / math.cos(math.radians(30.0))
    bpy.ops.mesh.primitive_cylinder_add(radius=circumradius, depth=height,
                                        vertices=6, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.rotation_euler[2] = math.radians(30.0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    return obj


def build_common_parts(suffix):
    """Ball + flange + stud, shared by all three variants."""
    stud = add_cylinder(STUD_RADIUS, STUD_LENGTH, (0.0, 0.0, -STUD_LENGTH / 2.0),
                        vertices=24, name="Stud_" + suffix)
    flange = add_cylinder(FLANGE_RADIUS, FLANGE_HEIGHT, (0.0, 0.0, FLANGE_HEIGHT / 2.0),
                          vertices=24, name="Flange_" + suffix)
    ball = add_sphere(BALL_RADIUS, (0.0, 0.0, BALL_CENTER_Z), name="Ball_" + suffix)
    return stud, flange, ball


def make_materials():
    """Materials must be built after the scene reset, which clears all data."""
    return {
        "hardened": material("M_Ballast_HardenedSteel", (0.05, 0.052, 0.055, 1.0), 1.0, 0.32),
        # Rune steel stays metal: the earlier 0.35 blue emission made the ball
        # read as a translucent blue orb instead of an engraved steel weight.
        "rune": material("M_Ballast_RuneSteel", (0.095, 0.082, 0.065, 1.0), 1.0, 0.30,
                         emission=(0.35, 0.55, 0.85, 1.0), emission_strength=0.10),
        "housing": material("M_Ballast_MagicHousing", (0.07, 0.07, 0.08, 1.0), 1.0, 0.25),
        # Strength 25 clipped to flat white in AgX and read as an empty hole;
        # a saturated low-strength emission actually reads as a glowing orb.
        "core": material("M_Ballast_MagicCore", (0.05, 0.35, 0.90, 1.0), 0.0, 0.10,
                         emission=(0.15, 0.55, 1.0, 1.0), emission_strength=4.0),
    }


# ------------------------------------------------------------------ variants

def build_hardened(mats):
    mat_steel = mats["hardened"]
    suffix = "Hardened"
    stud, flange, ball = build_common_parts(suffix)
    # Intersecting the ball with a hex prism turns the forged flats into the
    # silhouette itself; a collar sitting inside the sphere would only show
    # its six edges.
    prism = add_hex_prism(HEX_ACROSS_FLATS, BALL_RADIUS * 2.0,
                          (0.0, 0.0, BALL_CENTER_Z), name="HexPrism_" + suffix)
    apply_boolean(ball, prism, 'INTERSECT')
    for obj in (stud, flange, ball):
        obj.data.materials.clear()
        obj.data.materials.append(mat_steel)
    obj = join([ball, flange, stud], "SM_Ballast_Hardened_Candidate")
    shade_smooth(obj)
    return obj, {
        "variant": "Hardened",
        "design": "forged ball with six flats cut across the equator",
        "across_flats_mm": HEX_ACROSS_FLATS * 1000.0,
        "material": mat_steel.name,
    }


def build_rune(mats):
    mat_steel = mats["rune"]
    suffix = "Rune"
    stud, flange, ball = build_common_parts(suffix)

    cutters = []
    # The cutter is a thin slab that only dips RUNE_GROOVE_DEPTH into the
    # surface at its tangent point, so the groove tapers off like an engraving
    # instead of boring a slot through the ball.
    radial_center = -(BALL_RADIUS + RUNE_CUTTER_THICKNESS / 2.0 - RUNE_GROOVE_DEPTH)
    bar_size = (RUNE_GROOVE_WIDTH, RUNE_CUTTER_THICKNESS, 0.022)
    for index, x_offset in enumerate((-0.005, 0.0, 0.005)):
        cutter = add_box(bar_size, (x_offset, radial_center, BALL_CENTER_Z),
                         name="RuneBar_%d_%s" % (index, suffix))
        cutters.append(cutter)
    for sign in (1.0, -1.0):
        diagonal = add_box(bar_size, (0.0, radial_center, BALL_CENTER_Z),
                           name="RuneDiagonal_%s_%s" % ("p" if sign > 0 else "n", suffix))
        diagonal.rotation_euler[0] = math.radians(58.0 * sign)
        set_active(diagonal)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        cutters.append(diagonal)

    for cutter in cutters:
        apply_boolean(ball, cutter, 'DIFFERENCE')

    for obj in (stud, flange, ball):
        obj.data.materials.clear()
        obj.data.materials.append(mat_steel)
    obj = join([ball, flange, stud], "SM_Ballast_Rune_Candidate")
    shade_smooth(obj)
    return obj, {
        "variant": "Rune",
        "design": "engraved three-bar rune crossed by two diagonals on the front face",
        "material": mat_steel.name,
        "groove": {"width_mm": RUNE_GROOVE_WIDTH * 1000.0,
                   "depth_mm": RUNE_GROOVE_DEPTH * 1000.0},
    }


def build_magic_orb(mats):
    mat_housing = mats["housing"]
    mat_core = mats["core"]
    suffix = "MagicOrb"
    stud, flange, ball = build_common_parts(suffix)

    # Bore a socket into the top of the ball and seat the glowing core inside it.
    socket = add_cylinder(SOCKET_RADIUS, SOCKET_DEPTH,
                          (0.0, 0.0, BALL_CENTER_Z + BALL_RADIUS - SOCKET_DEPTH / 2.0),
                          vertices=32, name="Socket_" + suffix)
    apply_boolean(ball, socket, 'DIFFERENCE')

    bezel = add_torus(BEZEL_MAJOR, BEZEL_MINOR,
                      (0.0, 0.0, BALL_CENTER_Z + BALL_RADIUS - 0.0025),
                      name="Bezel_" + suffix)
    core = add_sphere(CORE_RADIUS,
                      (0.0, 0.0, CORE_TOP_Z - CORE_RADIUS),
                      segments=24, rings=12, name="Core_" + suffix)

    for obj in (stud, flange, ball, bezel):
        obj.data.materials.clear()
        obj.data.materials.append(mat_housing)
    core.data.materials.clear()
    core.data.materials.append(mat_core)

    obj = join([ball, bezel, core, flange, stud], "SM_Ballast_MagicOrb_Candidate")
    shade_smooth(obj)
    return obj, {
        "variant": "MagicOrb",
        "design": "caged glowing orb in a bored socket with a torus bezel",
        "materials": [mat_housing.name, mat_core.name],
        "socket_mm": SOCKET_RADIUS * 2000.0,
        "core_mm": CORE_RADIUS * 2000.0,
    }


# --------------------------------------------------------------- inspection

def mesh_report(obj):
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    non_manifold = sum(1 for edge in bm.edges if not edge.is_manifold)
    loose_verts = sum(1 for vert in bm.verts if not vert.link_edges)
    bm.free()
    bbox = [tuple(round(value, 5) for value in corner) for corner in obj.bound_box]
    size = tuple(round(max(c[i] for c in bbox) - min(c[i] for c in bbox), 5) for i in range(3))
    triangles = sum(len(poly.vertices) - 2 for poly in me.polygons)
    return {
        "object": obj.name,
        "verts": len(me.vertices),
        "faces": len(me.polygons),
        "triangles": triangles,
        "size_mm": [round(value * 1000.0, 2) for value in size],
        "material_slots": [slot.material.name for slot in obj.material_slots if slot.material],
        "non_manifold_edges": non_manifold,
        "loose_verts": loose_verts,
        "origin": [round(value, 5) for value in obj.location],
    }


def export_variants(objs, out_dir):
    export_dir = os.path.join(out_dir, "export")
    os.makedirs(export_dir, exist_ok=True)
    written = []
    for obj in objs:
        set_active(obj)
        fbx_path = os.path.join(export_dir, obj.name + ".fbx")
        try:
            bpy.ops.export_scene.fbx(
                filepath=fbx_path, use_selection=True, apply_scale_options='FBX_SCALE_ALL',
                object_types={'MESH'}, use_mesh_modifiers=True, mesh_smooth_type='FACE',
                axis_forward='-Z', axis_up='Y', bake_space_transform=False)
        except TypeError:
            bpy.ops.export_scene.fbx(filepath=fbx_path, use_selection=True)
        written.append(fbx_path)

        glb_path = os.path.join(export_dir, obj.name + ".glb")
        try:
            bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB',
                                      use_selection=True, export_apply=True)
        except TypeError:
            bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')
        written.append(glb_path)
    return written


def main():
    argv = sys.argv
    out_dir = argv[argv.index("--") + 1] if "--" in argv else os.path.dirname(os.path.abspath(__file__))
    blend_dir = os.path.join(out_dir, "blend")
    os.makedirs(blend_dir, exist_ok=True)

    report = {"interface": {
        "origin": "seating plane between flange and host (z = 0)",
        "stud": "M6 x 10 mm along -Z",
        "ball_diameter_mm": BALL_RADIUS * 2000.0,
        "units": "metres in Blender, centimetres in FBX",
    }, "variants": []}

    builders = (
        ("Ballast_Hardened", build_hardened),
        ("Ballast_Rune", build_rune),
        ("Ballast_MagicOrb", build_magic_orb),
    )

    objects = []
    for file_stem, builder in builders:
        reset_scene()
        obj, meta = builder(make_materials())
        info = mesh_report(obj)
        info.update(meta)
        report["variants"].append(info)
        log("%s: %d tris, %s mm, non-manifold=%d, slots=%s" % (
            obj.name, info["triangles"], info["size_mm"], info["non_manifold_edges"],
            ",".join(info["material_slots"])))
        blend_path = os.path.join(blend_dir, file_stem + ".blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend_path)
        objects.append(blend_path)

    # One combined file with all three variants for preview and manual review.
    reset_scene()
    mats = make_materials()
    combined = []
    for index, (file_stem, builder) in enumerate(builders):
        obj, _meta = builder(mats)
        obj.location = (index * 0.06, 0.0, 0.0)
        combined.append(obj)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(blend_dir, "Ballast_All.blend"))
    report["exports"] = export_variants(combined, out_dir)

    with open(os.path.join(out_dir, "build_report.json"), "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    log("report written")


if __name__ == "__main__":
    main()
