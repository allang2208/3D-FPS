"""Read-only exports for the requested G18 optic seat inspection."""
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
ROOT = '/Game/Weapons/G18/Integrated20260929'
rows = {}
for name, path, exporter in (
    ('host', ROOT + '/Single/SK_G18_Manny', u.SkeletalMeshExporterFBX),
    ('holographic', ROOT + '/Attachments/SM_G18_holographic', u.StaticMeshExporterFBX),
    ('panoramic_red_dot', ROOT + '/Attachments/SM_G18_panoramic_red_dot', u.StaticMeshExporterFBX),
):
    asset = u.load_asset(path)
    task = u.AssetExportTask()
    task.object = asset
    task.filename = str(OUT / (name + '.fbx'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = exporter()
    options = u.FbxExportOption()
    options.set_editor_property('level_of_detail', False)
    task.options = options
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Export failed: ' + path)
    rows[name] = {'asset': path, 'export': task.filename}
(OUT / 'exports.json').write_text(json.dumps(rows, indent=2), encoding='utf8')
print('G18_CURRENT_ASSETS_EXPORTED', flush=True)
