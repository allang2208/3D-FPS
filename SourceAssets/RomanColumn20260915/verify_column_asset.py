"""Read back the saved Roman column asset: mesh stats, material slots, collision."""

import unreal

MESH_PATH = "/Game/Props/RomanColumn20260915/SM_RomanColumn"
MAT_PATH = "/Game/Props/RomanColumn20260915/M_Plaster"

mesh = unreal.EditorAssetLibrary.load_asset(MESH_PATH)
material = unreal.EditorAssetLibrary.load_asset(MAT_PATH)

print("[verify] mesh loaded: %s" % (mesh is not None))
print("[verify] material loaded: %s" % (material is not None))

if mesh:
    bounds = mesh.get_bounds()
    extent = bounds.box_extent
    origin = bounds.origin
    print("[verify] bounds origin=%s extent=%s" % (origin, extent))
    try:
        print("[verify] triangles LOD0: %d" % mesh.get_num_triangles(0))
    except Exception as exc:  # noqa: BLE001
        print("[verify] triangle query failed: %s" % exc)
    slots = mesh.get_editor_property("static_materials")
    for index, slot in enumerate(slots):
        print("[verify] slot %d -> %s" % (index, slot.get_editor_property("material_interface").get_path_name()))
    body = mesh.get_editor_property("body_setup")
    print("[verify] body_setup: %s" % (body.get_path_name() if body else "None"))

if material:
    library = unreal.MaterialEditingLibrary
    print("[verify] material expressions: %d" % len(library.get_material_expressions(material)))
    print("[verify] base color connected: %s" % library.get_material_property_input_node(
        material, unreal.MaterialProperty.MP_BASE_COLOR))
    print("[verify] roughness connected: %s" % library.get_material_property_input_node(
        material, unreal.MaterialProperty.MP_ROUGHNESS))
