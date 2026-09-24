"""Export SM_PoplarLog_Solid_A to OBJ. No scene capture and no map changes."""
from pathlib import Path
import unreal as u

mesh = u.load_asset("/Game/Items/HarvestTimber/SM_PoplarLog_Solid_A.SM_PoplarLog_Solid_A")
if mesh is None:
    raise RuntimeError("missing SM_PoplarLog_Solid_A")
out = Path("D:/FPS3D/FPSGAME/Saved/HarvestTimber/SM_PoplarLog_Solid_A.obj")
out.parent.mkdir(parents=True, exist_ok=True)
task = u.AssetExportTask()
task.object = mesh
task.filename = str(out)
task.automated = True
task.prompt = False
task.replace_identical = True
task.exporter = u.StaticMeshExporterOBJ()
ok = u.Exporter.run_asset_export_task(task)
u.log("WOOD_LOG_OBJ %s ok=%s bytes=%s" % (out, ok, out.stat().st_size if out.exists() else 0))
if not ok or not out.exists() or out.stat().st_size < 100:
    raise RuntimeError("OBJ export failed")
