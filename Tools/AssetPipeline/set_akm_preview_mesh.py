import unreal

folder = "/Game/Weapons/AKM"
mesh = unreal.load_asset(f"{folder}/SK_AKM_Viewmodel")
for clip in ("idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "draw", "holster", "inspect"):
    animation = unreal.load_asset(f"{folder}/A_AKM_{clip}")
    if animation and mesh:
        animation.set_preview_skeletal_mesh(mesh)
unreal.EditorAssetLibrary.save_directory(folder, only_if_is_dirty=False, recursive=True)
unreal.log("AKM_PREVIEW_MESH_SET")
