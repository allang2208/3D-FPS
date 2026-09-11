"""Export two official motions with their preview mesh for contact inspection."""
from pathlib import Path
import unreal

output = Path("D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Reference")
output.mkdir(parents=True, exist_ok=True)
base = "/Game/Characters/UEFN_Mannequin/Animations/Traversal/"
for folder, name in (
    ("Vault", "M_Neutral_Traversal_Vault_1_0_stand_F_Lfoot"),
    ("Mantle", "M_Neutral_Traversal_Mantle_1_0_stand_F_Lfoot"),
    ("Climb", "M_Neutral_Traversal_Climb_Start_2_5_stand_F_Lfoot"),
):
    asset = unreal.load_asset(base + folder + "/" + name)
    assert asset, name
    task = unreal.AssetExportTask()
    task.object = asset
    task.filename = str(output / (folder + ".fbx"))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.options = unreal.FbxExportOption()
    task.options.set_editor_property("export_preview_mesh", True)
    assert unreal.Exporter.run_asset_export_task(task), task.errors
unreal.log("GASP_REFERENCE_EXPORT_COMPLETE")
