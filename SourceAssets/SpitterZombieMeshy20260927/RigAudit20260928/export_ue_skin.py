"""Export current skin to the diagnostic folder only; never save its package."""
import unreal as u
from pathlib import Path
root=Path(__file__).resolve().parent
mesh=u.load_asset('/Game/Monsters/SpitterZombie/SK_SpitterZombie')
task=u.AssetExportTask();task.object=mesh;task.filename=str(root/'UE_CurrentSkin.fbx')
task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.SkeletalMeshExporterFBX()
options=u.FbxExportOption();options.set_editor_property('level_of_detail',False);task.options=options
if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Read-only skin export failed')
u.log('SPITTER_AUDIT_SKIN_EXPORTED '+task.filename)
