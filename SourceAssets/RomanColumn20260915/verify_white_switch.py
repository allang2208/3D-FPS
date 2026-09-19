import unreal
D = "/Game/Props/RomanColumn20260915"
for path in (D+"/SM_RomanBaluster_Small", D+"/SM_RomanRail_200", D+"/SM_RomanPavilionDome_20", D+"/SM_RomanColumn_Round_20"):
    a = unreal.EditorAssetLibrary.load_asset(path)
    s = a.get_editor_property("static_materials")[0].get_editor_property("material_interface")
    print("[vr] %-28s slot0=%s" % (path.split("/")[-1], s.get_path_name().split(".")[-1] if s else "EMPTY"))
pal = unreal.load_asset("/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette")
for m in (pal.get_editor_property("materials") or []):
    if str(m.get_editor_property("id")) == "marble":
        s = m.get_editor_property("surface")
        print("[vr] palette marble row surface=%s" % (s.get_path_name().split(".")[-1] if s else "None"))
