import unreal

SV = unreal.ModelingService
D = "/Game/Props/RomanColumn20260915"

def log(m):
    print("[cmp] " + m)

def dump_material(path, label):
    mat = unreal.EditorAssetLibrary.load_asset(path)
    if not mat:
        log("%s: NOT LOADABLE" % label)
        return
    log("%s (%s):" % (label, path.split("/")[-1]))
    for expr in unreal.MaterialEditingLibrary.get_material_expressions(mat) or []:
        name = type(expr).__name__
        pname = tex = dv = None
        try: pname = expr.get_editor_property("parameter_name")
        except Exception: pass
        try: tex = expr.get_editor_property("texture").get_name()
        except Exception: pass
        try:
            v = expr.get_editor_property("default_value")
            dv = "(%.2f, %.2f, %.2f)" % (v.r, v.g, v.b) if hasattr(v, "r") else "%.2f" % v
        except Exception: pass
        log("   %-44s param=%-18s tex=%-22s default=%s" % (name, pname or "-", tex or "-", dv or "-"))

# ---- floor mesh
mesh = unreal.EditorAssetLibrary.load_asset(D + "/SM_MarbleFloorTiles")
b = mesh.get_bounds(); o, e = b.origin, b.box_extent
slots = mesh.get_editor_property("static_materials")
slot0 = slots[0].get_editor_property("material_interface") if slots else None
log("FLOOR MESH: dims=(%.0f x %.0f x %.0f) slot0=%s" % (
    e.x*2, e.y*2, e.z*2, slot0.get_path_name().split(".")[-1] if slot0 else "EMPTY"))
r = SV.load_mesh_from_static_mesh(D + "/SM_MarbleFloorTiles", 0)
info = SV.get_mesh_info(getattr(r, "handle", None))
log("FLOOR GEOM: tris=%s comps=%s open=%s bbox=(%.0f, %.0f, %.0f)" % (
    info.triangle_count, info.connected_components, info.open_border_edges,
    info.bounds_max.x-info.bounds_min.x, info.bounds_max.y-info.bounds_min.y, info.bounds_max.z-info.bounds_min.z))
SV.release_all_meshes()

# ---- materials
dump_material(D + "/M_WhiteMarble_V2", "FLOOR MATERIAL")
dump_material(D + "/M_RomanStone_V2", "VOXEL/BALUSTER MATERIAL")
