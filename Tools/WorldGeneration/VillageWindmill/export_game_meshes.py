"""Build game FBXs at the survey datums, from the approved mill masters and Meshy surfaces.

Run Blender in background with --python-exit-code 1 --python export_game_meshes.py.
The exchange uses numeric centimetres, FBX Z-up/-Y-front, and an identity mesh node.
"""
from contextlib import ExitStack
import json
import math
from pathlib import Path
import struct
import sys
from unittest.mock import patch

import bpy
import numpy as np
from mathutils import Matrix

PROJECT = Path(__file__).resolve().parents[3]
SOURCE = PROJECT / "SourceAssets/HillsVillageWindmill/ComponentsR2"
OUT = Path("F:/FPSGAMEData/ArtProduction/HillsVillageWindmill/GameR1/Exchange")
sys.path[:0] = [str(SOURCE / "Author"), str(Path(__file__).resolve().parent)]
import building
import millkit
import machine_fit
import walk_fit

ATLAS_PARTS = {"A01", "B02", "C06", "C08", "D04"}
PALETTE = set(millkit.PALETTE)
STAIR_CENTER = walk_fit.WELL_CENTER


def polar(radius, angle, z, center=(0, 0)):
    return (center[0] + radius * math.cos(angle), center[1] + radius * math.sin(angle), z)


def well_cutter():
    n = 112
    vertices = [polar(walk_fit.well_radius(math.tau * j / n) + .022, math.tau * j / n, z, STAIR_CENTER)
                for z in (-1, 1) for j in range(n)]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(j, (j+1) % n, n + (j+1) % n, n+j) for j in range(n)]
    return millkit.mesh("Eccentric stair opening", vertices, faces, "lime")


def game_deck(upper):
    def cutter(name, *args):
        return well_cutter() if name == "Stair well" else millkit.cyl(name, *args)

    def framed_beam(name, a, b, *args):
        if name == "Stair opening framed rim":
            def at(p):
                x, y, z = p
                angle = math.atan2(y - STAIR_CENTER[1], x - STAIR_CENTER[0])
                return polar(walk_fit.well_radius(angle) + .086, angle, z, STAIR_CENTER)
            a, b = at(a), at(b)
        return millkit.beam(name, a, b, *args)

    def deck_box(name, center, size, *args):
        if name == "Grain trunk opening":
            center, size = (-1.10, -.185, 0), (.37, .43, 2)
        elif name == "Meal spout opening":
            center, size = (-1.443, -1.455, 0), (.51, .56, 2)
        return millkit.box(name, center, size, *args)

    with ExitStack() as edits:
        edits.enter_context(patch.object(building, "cyl", cutter))
        edits.enter_context(patch.object(building, "beam", framed_beam))
        edits.enter_context(patch.object(building, "box", deck_box))
        building.deck(upper)


def atlas_input(part):
    path = SOURCE / "Meshy" / part / "downloads/model_urls_glb.glb"
    with path.open("rb") as src:
        src.seek(12)
        size, kind = struct.unpack("<II", src.read(8))
        spec = json.loads(src.read(size))
        src.seek(8, 1)
        start = src.tell()
        prim = spec["meshes"][0]["primitives"][0]

        def read(index):
            entry = spec["accessors"][index]
            view = spec["bufferViews"][entry["bufferView"]]
            src.seek(start + view.get("byteOffset", 0))
            raw = src.read(view["byteLength"])
            dtype = np.dtype({5126:"<f4", 5125:"<u4", 5123:"<u2", 5121:"u1"}[entry["componentType"]])
            cols = {"VEC2":2, "VEC3":3, "SCALAR":1}[entry["type"]]
            stride = view.get("byteStride", cols*dtype.itemsize)
            array = np.ndarray((entry["count"],cols), dtype, raw,
                               entry.get("byteOffset",0), (stride,dtype.itemsize))
            if entry.get("normalized") and dtype.kind == "u":
                return array.astype(np.float32) / np.iinfo(dtype).max
            return array.copy()

        position = read(prim["attributes"]["POSITION"])[:, [0, 2, 1]].copy()
        position[:,1] *= -1
        uv = read(prim["attributes"]["TEXCOORD_0"])
        uv[:,1] = 1 - uv[:,1]
        indices = read(prim["indices"]).reshape(-1,3)
    return position, uv, indices


def fitted_skin(part, mesh_name):
    p, uv, faces = atlas_input(part)
    x, y, z = p.T
    keep = None
    if part == "A01":
        # The left stile, cloth hand, and four cuff levels identify the X/Y/Z signs.
        # Trim the approximate cuff ears; the master supplies the actual stock bore.
        x[:] = (x + .191) * 2.21 + .195
        y[:] = (y - .058) * 2.32 + .016
        z[:] = (z + .952067) * (4.414 / 1.903449)
        keep = x >= .138
    elif part == "B02":
        # The through-hole, not the silhouette, is the bearing centre.
        z -= .093
        raw_r = np.hypot(x, z)
        x *= .87/1.903
        z *= .3725/(.690394+.093)
        xz_r = np.maximum(np.hypot(x, z), .00001)
        near_bore = np.clip((.60-raw_r)/.20, 0, 1)
        fitted_r = (1-near_bore)*xz_r + near_bore*np.maximum(.177, raw_r*.53)
        x *= fitted_r/xz_r
        z *= fitted_r/xz_r
        y *= .40/.877
    elif part == "C06":
        # Back/front are identifiable by the bend from the hopper to the floor slot.
        x *= -1.48/1.209
        y *= -1.20/1.0207
        z[:] = (z+.029236)*(1.19/(.95094+.029236))
        keep = (z>.171) | ((np.abs(x)>.30) & (z>=-.001))
        # Retain the Meshy sides, rim and legs. The surveyed floor below has an
        # actual draw hole. Reject spanning triangles even when all three
        # corners individually happen to be on the bin perimeter.
        outer = (x[faces].min(axis=1)>.54) | (x[faces].max(axis=1)<-.54)
        outer |= (y[faces].min(axis=1)>.40) | (y[faces].max(axis=1)<-.40)
        faces = faces[outer]
    elif part == "C08":
        # Select the actual coiled rope between the cheeks, keeping journals and handle surveyed.
        keep = (x>=-.515) & (x<=.201) & (np.hypot(y+.008,z+.018)>.213)
        x[:] = -.184+(x+.515)*(.368/.716)
        y[:] = (y+.008)*.56
        z[:] = (z+.018)*.56
    elif part == "D04":
        # X datum is the outer hinge pin; the meeting edge reaches +.742 m.
        x[:] = (x+.307)*(.742/(.32102+.307))
        y *= 1.24
        z[:] = .01+(z+.95199)*(2.323/1.90272)
    if keep is not None:
        faces = faces[np.all(keep[faces],axis=1)]
    uv_loops = uv[faces.reshape(-1)].ravel()
    used, remap = np.unique(faces, return_inverse=True)
    # Weld identical atlas seam positions while retaining per-corner UVs.
    points, compact = np.unique(p[used],axis=0,return_inverse=True)
    indices = compact[remap].reshape(-1)
    n = len(faces)
    data = bpy.data.meshes.new(part+" Meshy surface")
    data.vertices.add(len(points))
    data.vertices.foreach_set("co",points.astype(np.float32,copy=False).ravel())
    data.loops.add(3*n)
    data.loops.foreach_set("vertex_index",indices.astype(np.int32))
    data.polygons.add(n)
    data.polygons.foreach_set("loop_start",np.arange(0,3*n,3,dtype=np.int32))
    data.update(calc_edges=True)
    tex = data.uv_layers.new(name="UVMap")
    tex.uv.foreach_set("vector",uv_loops)
    data.polygons.foreach_set("use_smooth",np.ones(n,np.bool_))
    data.materials.append(slot("Meshy"))
    obj = bpy.data.objects.new(mesh_name+" scanned surface",data)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    decimate = obj.modifiers.new("Fitted game mesh", "DECIMATE")
    target = {"A01":52000, "B02":15000, "C03":22000, "C04":26000,
              "C06":25000,"C08":24000,"D04":18000}[part]
    decimate.ratio = min(1, target/n)
    decimate.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    return obj


def slot(name):
    return bpy.data.materials.get(name) or bpy.data.materials.new(name)


def material_name(mat):
    key = mat.name.split("/")[-1].strip().lower()
    if key in PALETTE:
        return key
    if "stone" in key:
        return "stone"
    if "linen" in key:
        return "flax"
    raise ValueError("Unmapped mill material: "+mat.name)


def real_uv(data):
    data.update()
    uv = data.uv_layers.new(name="UVMap")
    co = np.empty(len(data.vertices)*3,np.float32)
    data.vertices.foreach_get("co",co)
    co = co.reshape(-1,3)
    loops = np.empty(len(data.loops),np.int32)
    data.loops.foreach_get("vertex_index",loops)
    corners = co[loops]
    lengths = np.empty(len(data.polygons),np.int32)
    data.polygons.foreach_get("loop_total",lengths)
    normals = np.empty(len(data.polygons)*3,np.float32)
    data.polygons.foreach_get("normal",normals)
    normals = normals.reshape(-1,3)
    axis = np.abs(normals).argmax(axis=1)
    loop_axis = np.repeat(axis,lengths)
    loop_sign = np.repeat(np.where(normals[np.arange(len(axis)),axis]<0,-1.0,1.0),lengths)
    # One texture repeat per metre. Preserve orientation on opposite box faces.
    u = np.where(loop_axis==0,corners[:,1],corners[:,0])
    v = np.where(loop_axis==2,corners[:,1],corners[:,2])
    u *= np.where(loop_axis==1,-loop_sign,loop_sign)
    uv.uv.foreach_set("vector",np.column_stack((u,v)).astype(np.float32).ravel())


def master_filter(part, name):
    if part == "A01":
        return name.startswith(("Split stock cuffs", "Cuff attachment cheek", "Hot-riveted cuff pins"))
    if part == "B02":
        return "replaceable bearing liner" in name or name.startswith(("Tie bolt","Square seat washer","Cap nut"))
    if part == "C06":
        return name.startswith(("Grain draw","Spout binding","Slide runway","Oak shutoff","Gate grip","Boarded flat bin floor"))
    if part == "C08":
        return not name.startswith("Laid hemp on drum")
    return part != "D04"


def prepare_master(part):
    if part in {"D02","D03","D05","D06","D07"}:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        if part in {"D02","D03"}:
            game_deck(part=="D03")
        elif part == "D07":
            walk_fit.build_guard()
        else:
            walk_fit.build_stair(part=="D06")
    else:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE/"Masters"/(part+".blend")),load_ui=False)
    machine_fit.prepare(part)
    if part in {"C07","B04","D03"}:
        import hoist_fit
        hoist_fit.prepare(part)
    bpy.context.view_layer.update()
    depsgraph = bpy.context.evaluated_depsgraph_get()
    ready = []
    for source in list(bpy.context.scene.objects):
        if source.type not in {"MESH","CURVE","SURFACE"} or source.hide_render or not master_filter(part,source.name):
            continue
        evaluated = source.evaluated_get(depsgraph)
        data = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        if not data.polygons:
            bpy.data.meshes.remove(data)
            continue
        data.transform(evaluated.matrix_world)
        machine_fit.fit_source(part,source,data)
        if part == "D01":
            # The gameplay floor datum is 4 cm above the village soil. Extend
            # only the toe of the existing masonry beneath it, keeping the
            # arch, hinges, first bed joint and walking surfaces at survey Z.
            for vertex in data.vertices:
                if vertex.co.z < .12:
                    weight = min(1., (.12-vertex.co.z)/.12)
                    vertex.co.z -= .10*weight
        if part == "C05":
            walk_fit.fit_hurst_west(source,data)
        if part == "B01":
            # Extend the hewn parallel neck only; keep both bearing seats and
            # the brake-wheel mortise fixed. The square tenon, pin and front
            # iron hoop all move 52 cm towards the new canvas plane.
            for v in data.vertices:
                travel = min(1., max(0., (-2.08-v.co.y)/.14))
                v.co.y -= .52*travel
        # Boolean cut faces on some masters reference a blank cutter slot.
        # Machine those newly exposed faces in the same material as their host.
        host = next((mat for mat in data.materials if mat is not None),None)
        material_keys = [material_name(mat or host) if (mat or host) else "oak"
                         for mat in data.materials]
        if not material_keys:
            data.materials.append(slot("oak"))
        for j, key in enumerate(material_keys):
            data.materials[j] = slot(key)
        for uv in list(data.uv_layers):
            data.uv_layers.remove(uv)
        real_uv(data)
        obj = bpy.data.objects.new("Fitted "+source.name,data)
        bpy.context.collection.objects.link(obj)
        ready.append(obj)
    return ready


DESCRIPTIONS = {
    "D01":"Surveyed masonry tower with its bottom course bedded below the village soil datum.",
    "A01":"Original Meshy sailcloth and wood lattice registered to the four collar stations; master iron cuffs and cheeks.",
    "B02":"Original Meshy bearing block fitted about the journal; master replaceable liners and through bolts.",
    "C03":"Hollow surveyed octagonal casing with a working stone clearance, open race and flour sleeve.",
    "C04":"Surveyed feed hopper, open throat and separately suspended feed shoe over the runner eye.",
    "C06":"Meshy bin sides and legs surrounding the surveyed open draw floor, slide and trunk.",
    "C08":"Original Meshy coiled rope between surveyed drum cheeks; master through-axle, journals and crank.",
    "D04":"Original Meshy arched door registered on the hinge line, sill and mating edge.",
    "D02":"Surveyed lower deck with eccentric full-height stair well and flour-chute opening on its actual run.",
    "D03":"Surveyed upper deck with eccentric full-height stair well and offset aperture for the grain downpipe.",
    "D05":"Survey stair datum, widened treads toward tower interior, 65-degree landing and open entry.",
    "D06":"Survey stair datum, widened treads toward tower interior, 65-degree landing and open entry.",
}


def export(row):
    part = row["id"]
    name = "SM_Windmill_"+part
    ready = prepare_master(part)
    if part in ATLAS_PARTS:
        ready.append(fitted_skin(part,name))
    bpy.ops.object.select_all(action="DESELECT")
    for obj in ready:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = ready[0]
    if len(ready)>1:
        bpy.ops.object.join()
    obj = ready[0]
    obj.name = obj.data.name = name
    obj.data.transform(Matrix.Scale(100,4))
    # Triangulate before tangent export, including beveled planks and boolean door reveals.
    triangulate = obj.modifiers.new("Shipping triangles","TRIANGULATE")
    bpy.ops.object.modifier_apply(modifier=triangulate.name)
    bpy.context.view_layer.update()
    mesh = obj.data
    verts = np.empty(len(mesh.vertices)*3,np.float32)
    mesh.vertices.foreach_get("co",verts)
    verts = verts.reshape(-1,3)
    low, high = verts.min(0), verts.max(0)
    bounds = lambda value: [round(float(n),3) for n in value]
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = .01
    tmp = OUT / (name+".partial.fbx")
    dest = OUT / (name+".fbx")
    bpy.ops.export_scene.fbx(filepath=str(tmp),use_selection=True,object_types={"MESH"},
                             axis_forward="Y",axis_up="Z",use_space_transform=True,
                             apply_unit_scale=True,apply_scale_options="FBX_SCALE_UNITS",
                             mesh_smooth_type="FACE",use_tspace=True,bake_anim=False,
                             use_custom_props=False,path_mode="STRIP",embed_textures=False)
    tmp.replace(dest)
    sources = [f"Masters/{part}.blend"]
    if part in ATLAS_PARTS:
        sources.append(f"Meshy/{part}/downloads/model_urls_glb.glb")
    if part in {"D02","D03","D05","D06"}:
        sources.append("Author/building.py")
    print("WINDMILL_GAME_FBX",part,dest,flush=True)
    return {"id":part,"file":dest.name,"sources":sources,"method":DESCRIPTIONS.get(part,
            "Surveyed mechanical / architectural master, evaluated with original machining and mounting datums."),
            "pivot":row["pivot"],"bounds_min_blender_cm":bounds(low),"bounds_max_blender_cm":bounds(high),
            "dimensions_cm":bounds(high-low),"materials":[m.name for m in mesh.materials],
            "triangles":len(mesh.polygons)}


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    rows = json.loads((SOURCE/"catalog.json").read_text(encoding="utf-8-sig"))
    requested = set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
    prior = {}
    if requested:
        unknown = requested - {row["id"] for row in rows}
        if unknown:
            raise ValueError(f"Unknown mill parts: {sorted(unknown)}")
        prior = {p["id"]: p for p in json.loads((OUT/"geometry.json").read_text(encoding="utf-8"))["parts"]}
    parts = [export(row) if not requested or row["id"] in requested else prior[row["id"]] for row in rows]
    report = {"source":str(SOURCE),"fbx_units":"centimetres; FBX numeric mesh vertices are centimetres",
              "axes":"Blender X,Y,Z to Unreal +X,-Y,+Z; FBX Z up, front axis -Y, right handed",
              "pivot":"Identity node, surveyed origin retained in the vertices; do not recenter",
              "uv0":"Original Meshy atlas for Meshy slots. Survey mesh UVs repeat once per metre.",
              "stairs":{"survey_center_xy_m":STAIR_CENTER,"newel_offset_xy_m":walk_fit.NEWEL_OFFSET,"outer_radius_m":[1.019,1.357],
                        "outer_rail_inset_m":.025,"rail_radius_m":.029,"newel_radius_m":.068,
                        "landing_degrees":65,"lower_steps":18,"upper_steps":16,"floors_m":[0,3.10,5.90],
                        "collision":"Use complex as simple on stairs, finished decks, and stone shell."},
              "parts":parts}
    tmp = OUT/"geometry.partial.json"
    tmp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    tmp.replace(OUT/"geometry.json")


if __name__ == "__main__":
    main()
