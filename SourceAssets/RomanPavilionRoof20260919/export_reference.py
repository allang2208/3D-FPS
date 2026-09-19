"""Read-only export of the installed pavilion for three roof design previews."""
import json
from pathlib import Path
import unreal as u

out = Path(__file__).parent
out.mkdir(parents=True, exist_ok=True)
path = '/Game/Props/RomanColumn20260915/SM_RomanPavilionFull_20'
mesh = u.load_asset(path)
task = u.AssetExportTask()
task.object = mesh
task.filename = str(out/'pavilion_reference.fbx')
task.exporter = u.StaticMeshExporterFBX()
task.automated = True
task.prompt = False
task.replace_identical = True
task.options = u.FbxExportOption()
if not u.Exporter.run_asset_export_task(task):
    raise RuntimeError('Could not export the current pavilion')
b = mesh.get_bounds()
(out/'reference.json').write_text(json.dumps({
    'source_asset':path, 'dimensions_cm':[b.box_extent.x*2,b.box_extent.y*2,b.box_extent.z*2],
    'origin_cm':[b.origin.x,b.origin.y,b.origin.z],
    'preview_only':True, 'ue_assets_modified':False,
}, indent=2), encoding='utf-8')
print('PAVILION_REFERENCE_EXPORTED '+str(out/'pavilion_reference.fbx'))
