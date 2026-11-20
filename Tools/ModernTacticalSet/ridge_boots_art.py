"""Build editable and interchange models for both native-weighted TS01 boots."""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from coyote_glove_art import select
from field_pants_art import garment, relief_texture
from ridge_boots_materials import create

ROOT = HERE.parents[1] / "SourceAssets/ModernTacticalSet20261113/RidgeBootsR2"
NAME = "SK_TS01_RidgeBoots"


def finish_bevel_uvs(data,mats):
    # At a straight section a rolled edge can be parallel to its UV offset.
    # Keep its longest edge anchored, then lay its third corner out at the
    # real unit scale, so normal mapping follows the thickness of the seam.
    ids = np.asarray(data["triangle_materials"])
    wearable = np.isin(ids,[i for i,s in enumerate(data["material_slots"]) if s in mats])
    faces = np.asarray(data["triangles"])
    p = np.asarray(data["positions"])[faces]
    uv = np.asarray(data["uv"])
    geom_area = np.linalg.norm(np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0]),axis=1)
    flat = wearable & (geom_area < 1.e-7)
    if flat.any():
        # Preserve all original triangle/part ranges when filtering a
        # collapsed point bevel from the exported model.
        ids[flat] = len(data["material_slots"])
        data["material_slots"].append("NATIVE:collapsed bevel")
        data["triangle_materials"] = ids.tolist()
    a,b = uv[:,1]-uv[:,0],uv[:,2]-uv[:,0]
    det = a[:,0]*b[:,1]-a[:,1]*b[:,0]
    for index in np.flatnonzero(wearable & ~flat & (np.abs(det)<1.e-8)):
        uv_face,tri = uv[index],p[index]
        edges = np.roll(uv_face,-1,axis=0)-uv_face
        i = int(np.argmax(np.linalg.norm(edges,axis=1)))
        j,k = (i+1)%3,(i+2)%3
        edge = tri[j]-tri[i]
        if np.linalg.norm(edges[i])<1.e-8:
            i = int(np.argmax(np.linalg.norm(np.roll(tri,-1,axis=0)-tri,axis=1)))
            j,k = (i+1)%3,(i+2)%3
            edge = tri[j]-tri[i]
            uv_face[j] = uv_face[i]+[np.linalg.norm(edge)/4.,0.]
        direction = uv_face[j]-uv_face[i]
        direction /= np.linalg.norm(direction)
        distance = np.linalg.norm(edge)
        station = np.dot(tri[k]-tri[i],edge)/distance
        height = geom_area[index]/distance
        uv_face[k] = uv_face[i]+(station*direction+height*np.array([-direction[1],direction[0]]))*.25
        data["uv"][index] = uv_face.tolist()


def high_relief(ob):
    sub = ob.modifiers.new("Surface subdivision for leather grain and weave", "SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 2 if len(ob.data.polygons) < 95000 else 1
    sub.uv_smooth = "NONE"
    for name, strength in (("RB_Suede", .00036), ("RB_Textile", .00032),
                           ("RB_Frame", .00015), ("RB_Outsole", .00026), ("RB_Lining", .00017)):
        slot = ob.data.materials.find(name)
        if slot < 0:
            continue
        vertices = set()
        boundary = {}
        for face in ob.data.polygons:
            if face.material_index == slot:
                vertices.update(face.vertices)
                for edge in face.edge_keys:
                    boundary[edge] = boundary.get(edge, 0) + 1
        for edge, count in boundary.items():
            if count == 1:
                vertices.difference_update(edge)
        if not vertices:
            continue
        mask = ob.vertex_groups.new(name=name + " relief mask")
        mask.add(sorted(vertices), 1., "REPLACE")
        mod = ob.modifiers.new(name + " surface relief", "DISPLACE")
        mod.texture = relief_texture(name)
        mod.texture_coords = "UV"
        mod.uv_layer = ob.data.uv_layers.active.name
        mod.vertex_group = mask.name
        mod.strength = strength
        mod.mid_level = .5
    return len(ob.data.polygons) * 4**sub.levels


def main():
    models, exports = ROOT/"Models", ROOT/"Exports"
    for path in (models, exports):
        path.mkdir(parents=True, exist_ok=True)
    source = ROOT/"Authored/boots_Jason.json"
    raw = source.read_bytes()
    data = json.loads(raw)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    mats = create()
    for im in bpy.data.images:
        if im.source == "FILE" and im.filepath and not im.packed_file:
            im.pack()
    # Native cutaway skin is required by the worn variant only.
    for i, original in enumerate(data["material_slots"]):
        short = original.rsplit("/", 1)[-1].split(".")[0].removeprefix("M_")
        if short in mats:
            data["material_slots"][i] = short
    finish_bevel_uvs(data,mats)
    ob, rig = garment(data, mats)
    ob.name = ob.data.name = NAME
    ob.modifiers[0].name = "Native calf, ankle and forefoot weights"
    pattern = ob.data.attributes.get("Sewing pattern piece")
    if pattern:
        pattern.name = "Boot construction piece"
    select([ob, rig])
    bpy.ops.wm.save_as_mainfile(filepath=str(models/(NAME+"_GAME.blend")), compress=True)
    bpy.ops.export_scene.gltf(filepath=str(exports/(NAME+".glb")), export_format="GLB", use_selection=True,
                              export_animations=False, export_tangents=True, export_all_influences=True)
    bpy.ops.export_scene.fbx(filepath=str(exports/(NAME+".fbx")), use_selection=True,
                             object_types={"MESH","ARMATURE"}, bake_anim=False, add_leaf_bones=False,
                             mesh_smooth_type="FACE", apply_unit_scale=True, axis_forward="-Y", axis_up="Z",
                             path_mode="COPY", embed_textures=True)
    high = high_relief(ob)
    bpy.ops.wm.save_as_mainfile(filepath=str(models/(NAME+"_HIGH.blend")), compress=True)
    record = dict(source=source.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(raw).hexdigest(),
                  native_rig="Jason", triangles=len(ob.data.polygons), high_triangles=high,
                  game_blend="Models/"+NAME+"_GAME.blend", high_blend="Models/"+NAME+"_HIGH.blend",
                  game_glb="Exports/"+NAME+".glb", native_fbx="Exports/"+NAME+".fbx")
    (models/"models.json").write_text(json.dumps(record, indent=2))
    print("RIDGE_BOOT_MASTERS", record, flush=True)


if __name__ == "__main__":
    main()
