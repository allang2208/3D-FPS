"""Load back the field-hat assets and print their saved runtime properties."""
import unreal as u

DEST = "/Game/Characters/ModularOutfit20260924/FieldHat20261019"
S = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
E = u.EditorAssetLibrary


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError("missing " + path)
    return asset


def dump_static(label, path):
    mesh = load(path)
    print(label, mesh.get_path_name(), "lod", mesh.get_num_lods(),
          "tris", [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())],
          "materials", [str(s.material_slot_name) + "=" + (s.material_interface.get_path_name() if s.material_interface else "None")
                        for s in mesh.get_editor_property("static_materials")], flush=True)


mesh = load(DEST + "/SK_FieldHat")
print("SKELETAL", mesh.get_path_name(), "skeleton", mesh.skeleton.get_path_name(),
      "lods", S.get_lod_count(mesh), "physics", mesh.get_editor_property("physics_asset"), flush=True)
print("SLOTS", [(str(s.material_slot_name), s.material_interface.get_path_name() if s.material_interface else None)
                for s in mesh.get_editor_property("materials")], flush=True)
for i in range(S.get_lod_count(mesh)):
    info = S.get_lod_build_settings(mesh, i)
    print("LOD", i, "tris", mesh.get_num_triangles(i), "verts", mesh.get_num_vertices(i),
          "screen", info.get_editor_property("screen_size").default, flush=True)
bounds = mesh.get_bounds()
print("BOUNDS", bounds.box_extent, bounds.origin, flush=True)
skeleton = load(mesh.skeleton.get_path_name().split(".")[0])
print("BONES", [str(b.name) for b in skeleton.get_editor_property("bone_names")], flush=True)
dump_static("PICKUP", load(DEST + "/Pickups/SM_FieldHat_Pickup").get_path_name())
dump_static("ICONMESH", load(DEST + "/Icons/SM_FieldHat_Icon").get_path_name())
tex = load(DEST + "/Icons/T_FieldHat_Icon")
print("ICONTEX", tex.get_path_name(), tex.blueprint_get_size_x(), tex.blueprint_get_size_y(),
      "srgb", tex.get_editor_property("srgb"), "compression", tex.get_editor_property("compression_settings"),
      "mips", tex.get_editor_property("mip_gen_settings"), flush=True)
print("FIELD_HAT_VERIFIED", flush=True)