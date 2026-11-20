"""Create the clean shirt masters from the native wearable pattern and binding."""
import hashlib
import json
from pathlib import Path
import sys

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from coyote_glove_art import select
from field_pants_art import garment, relief_texture
from ridge_boots_art import finish_bevel_uvs
from patrol_shirt_materials import create

ROOT = HERE.parents[1]/"SourceAssets/ModernTacticalSet20261113/PatrolShirtR2"
NAME = "SK_TS01_PatrolShirt"


def high_relief(ob):
    sub = ob.modifiers.new("Textile relief subdivision","SUBSURF")
    sub.subdivision_type = "SIMPLE"
    sub.levels = sub.render_levels = 2 if len(ob.data.polygons)<85000 else 1
    sub.uv_smooth = "NONE"
    for slot,strength in (("PS_Jersey",.00019),("PS_Ripstop",.00031),("PS_Reinforcement",.00026),
                          ("PS_Loop",.00046),("PS_Binding",.00027)):
        mi = ob.data.materials.find(slot)
        if mi < 0:
            continue
        vertices, edges = set(), {}
        for face in ob.data.polygons:
            if face.material_index == mi:
                vertices.update(face.vertices)
                for edge in face.edge_keys:
                    edges[edge] = edges.get(edge,0)+1
        for edge,count in edges.items():
            if count==1:
                vertices.difference_update(edge)
        if vertices:
            group = ob.vertex_groups.new(name=slot+" fabric interior")
            group.add(sorted(vertices),1.,"REPLACE")
            disp = ob.modifiers.new(slot+" warp and weft","DISPLACE")
            disp.texture = relief_texture(slot)
            disp.texture_coords = "UV"
            disp.uv_layer = ob.data.uv_layers.active.name
            disp.vertex_group = group.name
            disp.strength = strength
            disp.mid_level = .5
    return len(ob.data.polygons)*4**sub.levels


def main():
    models, exports = ROOT/"Models", ROOT/"Exports"
    for path in (models,exports):
        path.mkdir(parents=True,exist_ok=True)
    source = ROOT/"World/shirt_Jason.json"
    raw = source.read_bytes()
    data = json.loads(raw)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    mats = create()
    for i,slot in enumerate(data["material_slots"]):
        name = slot.rsplit("/",1)[-1].split(".")[0].removeprefix("M_")
        data["material_slots"][i] = name if name in mats else "NATIVE:"+slot
    finish_bevel_uvs(data,mats)
    ob, rig = garment(data,mats)
    ob.name = ob.data.name = NAME
    ob.modifiers[0].name = "Native waist, shoulder, arm and wrist weights"
    select([ob,rig])
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(models/(NAME+"_GAME.blend")),compress=True)
    bpy.ops.export_scene.gltf(filepath=str(exports/(NAME+".glb")),export_format="GLB",use_selection=True,
                              export_animations=False,export_tangents=True,export_all_influences=True)
    bpy.ops.export_scene.fbx(filepath=str(exports/(NAME+".fbx")),use_selection=True,object_types={"MESH","ARMATURE"},
                             bake_anim=False,add_leaf_bones=False,mesh_smooth_type="FACE",apply_unit_scale=True,
                             axis_forward="-Y",axis_up="Z",path_mode="COPY",embed_textures=True)
    high = high_relief(ob)
    bpy.ops.wm.save_as_mainfile(filepath=str(models/(NAME+"_HIGH.blend")),compress=True)
    meta = dict(source=source.relative_to(ROOT).as_posix(),source_sha256=hashlib.sha256(raw).hexdigest(),
                native_rig="Jason",triangles=len(ob.data.polygons), high_triangles=high,
                game_blend="Models/"+NAME+"_GAME.blend",high_blend="Models/"+NAME+"_HIGH.blend",
                game_glb="Exports/"+NAME+".glb",native_fbx="Exports/"+NAME+".fbx")
    (models/"models.json").write_text(json.dumps(meta,indent=2),encoding="utf8")


if __name__=="__main__":
    main()
