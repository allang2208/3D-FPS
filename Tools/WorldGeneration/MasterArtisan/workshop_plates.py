"""Author the workshop's selection plates from the gameplay preview meshes at a matching camera angle."""
import json, math, os, struct, sys, zipfile
from pathlib import Path
import bpy
from mathutils import Euler, Vector

siege_source = Path(os.environ["VILLAGE_SIEGE_SOURCE"]) if "VILLAGE_SIEGE_SOURCE" in os.environ else None
hotoil_zip = Path(os.environ.get("VILLAGE_HOTOIL_ZIP", str(Path(__file__).resolve().parents[3] / "SourceAssets/HillsVillageHighWall20261120/HotOil/SM_OilHearth.meshzip")))
output = Path(os.environ["VILLAGE_SIEGE_PLATES"])
output.mkdir(parents=True, exist_ok=True)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
only = {a.split("=", 1)[1] for a in argv if a.startswith("--only=")}
models = [m for m in ("Trebuchet", "Ballista", "HotOil") if (not only or m in only)]


def studio_render(parts, center, size, lo_z, name, extra_lights=()):
    scene = bpy.context.scene
    bpy.ops.mesh.primitive_plane_add(size=20 * size, location=(center.x, center.y, lo_z - .004 * size))
    floor = bpy.data.materials.new("workshop backdrop")
    floor.use_nodes = True
    ground = floor.node_tree.nodes.get("Principled BSDF")
    ground.inputs["Base Color"].default_value = (.030, .035, .038, 1.)
    ground.inputs["Roughness"].default_value = .82
    bpy.context.object.data.materials.append(floor)
    camera = bpy.data.cameras.new("Plate")
    ob = bpy.data.objects.new("Plate", camera)
    scene.collection.objects.link(ob)
    direction = Vector((.48, -1., .45)).normalized()
    ob.location = center + direction * size * 3
    ob.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    camera.type = "ORTHO"
    camera.clip_end = size * 25
    camera.clip_start = size * .005
    scene.camera = ob
    scene.render.resolution_x = 672
    scene.render.resolution_y = 322
    scene.render.resolution_percentage = 100
    bpy.context.view_layer.update()
    proj = ob.matrix_world.inverted()
    xy = [proj @ (part.matrix_world @ v.co) for part in parts for v in part.data.vertices]
    xs = [q.x for q in xy]
    ys = [q.y for q in xy]
    camera.ortho_scale = max(max(xs) - min(xs), (max(ys) - min(ys)) * 672 / 322) * 1.22
    ob.location += ob.rotation_euler.to_quaternion() @ Vector(((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, 0))
    scene.world = bpy.data.worlds.new("Studio")
    scene.world.color = (.12, .13, .14)
    for d, power, color in [((-.5, -1, 1.4), 60, (1, .86, .68)), ((.5, 1, .9), 72, (.75, .84, 1))]:
        light = bpy.data.lights.new("Softbox", "AREA")
        lamp = bpy.data.objects.new("Softbox", light)
        scene.collection.objects.link(lamp)
        vec = Vector(d)
        lamp.location = center + vec * size
        lamp.rotation_euler = (-vec).to_track_quat("-Z", "Y").to_euler()
        light.energy = power * size ** 2
        light.shape = "DISK"
        light.size = size
        light.color = color
    for pos, energy, color in extra_lights:
        pt = bpy.data.lights.new("HearthGlow", "POINT")
        pt.energy = energy * size ** 2
        pt.color = color
        pt.shadow_soft_size = 0.14 * size
        lamp = bpy.data.objects.new("HearthGlow", pt)
        scene.collection.objects.link(lamp)
        lamp.location = pos
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 91
    scene.render.filepath = str(output / (name + ".jpg"))
    bpy.ops.render.render(write_still=True)


def make_mat(name, base, rough=.65, metal=0., emit=(0., 0., 0.), emit_str=0.):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1.)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit_str > 0.:
        bsdf.inputs["Emission Color"].default_value = (*emit, 1.)
        bsdf.inputs["Emission Strength"].default_value = emit_str
    return mat


def build_hotoil():
    scene = bpy.context.scene
    with zipfile.ZipFile(hotoil_zip) as z:
        meta = json.loads(z.read("mesh.json"))
        mesh_data = bpy.data.meshes.new("SM_OilHearth")
        all_verts, all_tris, all_mats = [], [], []
        mat_styles = {
            "Footing": make_mat("Footing", (.30, .28, .25), rough=.84, metal=0.),
            "SignOak": make_mat("SignOak", (.27, .127, .050), rough=.58, metal=0.),
            "ForgedStrap": make_mat("ForgedStrap", (.13, .135, .145), rough=.38, metal=.76),
            "WheelBrass": make_mat("WheelBrass", (.58, .41, .16), rough=.28, metal=.88),
        }
        for idx, mat_name in enumerate(meta["materials"]):
            mesh_data.materials.append(mat_styles.get(mat_name, make_mat(mat_name, (.25, .22, .19))))
            vraw = z.read(f"{idx}/vertices")
            iraw = z.read(f"{idx}/indices")
            vcount = len(vraw) // 12
            voff = len(all_verts)
            floats = struct.unpack(f"<{vcount * 3}f", vraw)
            for k in range(0, len(floats), 3):
                # Rotate Z so open hearth arch & wooden side handles show cleanly toward the 3/4 camera.
                all_verts.append((floats[k] * .01, -floats[k + 1] * .01, floats[k + 2] * .01))
            indices = struct.unpack(f"<{len(iraw) // 4}I", iraw)
            for k in range(0, len(indices), 3):
                all_tris.append((voff + indices[k], voff + indices[k + 2], voff + indices[k + 1]))
                all_mats.append(idx)
        mesh_data.from_pydata(all_verts, [], all_tris)
        for p, m_idx in zip(mesh_data.polygons, all_mats):
            p.material_index = m_idx
            p.use_smooth = True
        mesh_data.update()
        hearth = bpy.data.objects.new("SM_OilHearth", mesh_data)
        scene.collection.objects.link(hearth)
        hearth.rotation_euler = Euler((0., 0., math.radians(-58.)), "XYZ")
        es = hearth.modifiers.new("EdgeSplit", "EDGE_SPLIT")
        es.split_angle = math.radians(38.)

    # Boiling dark-amber glossy oil surface with subtle procedural heat ripples
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=.57, depth=.03, location=(0., 0., .875))
    oil_disc = bpy.context.object
    oil_mat = make_mat("OilLiquid", (.055, .016, .003), rough=.05, metal=0., emit=(.45, .11, .008), emit_str=.22)
    nt = oil_mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 4.0
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = .14
    bump.inputs["Distance"].default_value = .012
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    oil_disc.data.materials.append(oil_mat)

    # Dark charcoal bed with glowing ember fissures inside open stone firebox (z=0.16m)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=.36, depth=.05, location=(0., 0., .16))
    embers = bpy.context.object
    emb_mat = make_mat("Embers", (.025, .018, .015), rough=.92, metal=0.)
    ent = emb_mat.node_tree
    ebsdf = ent.nodes.get("Principled BSDF")
    vor = ent.nodes.new("ShaderNodeTexVoronoi")
    vor.feature = "DISTANCE_TO_EDGE"
    vor.inputs["Scale"].default_value = 14.0
    ramp = ent.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (1.0, .26, .02, 1.0)
    ramp.color_ramp.elements[1].position = 0.24
    ramp.color_ramp.elements[1].color = (.01, .005, .003, 1.0)
    ent.links.new(vor.outputs["Distance"], ramp.inputs["Fac"])
    ent.links.new(ramp.outputs["Color"], ebsdf.inputs["Emission Color"])
    ebsdf.inputs["Emission Strength"].default_value = 8.0
    embers.data.materials.append(emb_mat)

    parts = [hearth, oil_disc, embers]
    bpy.context.view_layer.update()
    corners = [ob.matrix_world @ Vector(c) for ob in parts for c in ob.bound_box]
    lo = Vector([min(v[i] for v in corners) for i in range(3)])
    hi = Vector([max(v[i] for v in corners) for i in range(3)])
    center = (lo + hi) / 2
    size = max(hi - lo)
    studio_render(parts, center, size, lo.z, "HotOil", extra_lights=[((0., 0., .28), 3.2, (1., .36, .06))])


for model in models:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if model == "HotOil":
        build_hotoil()
        continue
    assert siege_source is not None, "VILLAGE_SIEGE_SOURCE required for Trebuchet/Ballista"
    scene = bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=str(siege_source / f"SM_{model}Preview.fbx"))
    parts = [ob for ob in scene.objects if ob.type == "MESH"]
    for mat in {m for ob in parts for m in ob.data.materials if m}:
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        bsdf = nodes.get("Principled BSDF")
        if "Ballista" in mat.name:
            t = nodes.new("ShaderNodeTexImage")
            t.image = bpy.data.images.load(str(siege_source / "T_BallistaBase.png"))
            mat.node_tree.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            colors = {"Oak": (.27, .127, .050), "Iron": (.17, .18, .19), "Stone": (.34, .32, .29), "Leather": (.12, .055, .024)}
            bsdf.inputs["Base Color"].default_value = (*colors.get(mat.name.split(".")[0], (.22, .16, .09)), 1.)
            bsdf.inputs["Metallic"].default_value = .7 if "Iron" in mat.name else 0.
    corners = [ob.matrix_world @ Vector(c) for ob in parts for c in ob.bound_box]
    lo = Vector([min(v[i] for v in corners) for i in range(3)])
    hi = Vector([max(v[i] for v in corners) for i in range(3)])
    studio_render(parts, (lo + hi) / 2, max(hi - lo), lo.z, model)
