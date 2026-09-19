"""Import only the ASH-12 clips (mesh untouched) via commandlet.

Used when the editor holds the mesh uasset locked but the mesh itself did not
change (e.g. a retime pass that only rewrites animation timing).
"""
import unreal as u

O = r"D:\FPS3D\FPSGAME\SourceAssets\ASH1220260917"
D = "/Game/Weapons/ASH12/Integrated20260917"
COMPRESSION = "/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel"
CLIPS = ["idle", "aim", "fire", "aim_fire", "reload", "reload_empty", "equip_charge"]

tools = u.AssetToolsHelpers.get_asset_tools()
mesh = u.load_asset(D + "/SK_ASH12_Manny")
if not mesh:
    raise RuntimeError("live mesh not found")
for kind in CLIPS:
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = mesh.skeleton
    options.anim_sequence_import_data.set_editor_property("use_default_sample_rate", False)
    options.anim_sequence_import_data.set_editor_property("custom_sample_rate", 120)
    task = u.AssetImportTask()
    task.filename = O + ("\\A_ASH12_%s.fbx" % kind)
    task.destination_path = D + "/Animations"
    task.destination_name = "A_ASH12_" + kind
    task.options = options
    task.automated = True
    task.replace_existing = True
    task.save = False
    tools.import_asset_tasks([task])
    clip = u.load_asset(D + "/Animations/A_ASH12_" + kind)
    if not clip:
        raise RuntimeError("clip import failed: " + kind)
    clip.set_editor_property("bone_compression_settings", u.load_asset(COMPRESSION))
    if not u.EditorAssetLibrary.save_loaded_asset(clip, False):
        raise RuntimeError("clip save failed (locked by the editor?): " + kind)
    u.log("ASH12_LIVE_CLIP %s %.3fs" % (kind, clip.get_play_length()))
u.log("ASH12_LIVE_CLIPS_COMPLETE")
