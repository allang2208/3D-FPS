"""Read the imported ice graphs and export source color maps for wall authoring."""
import json
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir())
dest = root / 'SourceAssets/IceWall20260930/FabIceV3/ImportedReference'
dest.mkdir(parents=True, exist_ok=True)
lib = u.MaterialEditingLibrary
records = []
for index in range(1, 11):
    mat = u.load_asset(f'/Game/Ice/Materials/M_Ice{index}')
    record = {'material': mat.get_path_name(), 'class': mat.get_class().get_name(),
              'blend_mode': str(mat.get_editor_property('blend_mode')),
              'shading_model': str(mat.get_editor_property('shading_model')), 'nodes': []}
    for expr in lib.get_material_expressions(mat):
        node = {'class': expr.get_class().get_name()}
        for key in ('texture', 'parameter_name', 'default_value', 'r', 'constant'):
            try:
                value = expr.get_editor_property(key)
                node[key] = value.get_path_name() if isinstance(value, u.Object) else str(value)
            except Exception:
                pass
        record['nodes'].append(node)
    tex = u.load_asset(f'/Game/Ice/Textures/T_Ice{index}_basecolor')
    task = u.AssetExportTask()
    task.object = tex
    task.exporter = u.TextureExporterPNG()
    task.filename = str(dest / f'T_Ice{index}_basecolor.png')
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError(f'Cannot export ice source {index}')
    records.append(record)
path = dest.parent / 'imported-materials.json'
path.write_text(json.dumps(records, indent=2), encoding='utf-8')
print('Imported ice authoring sources: ' + str(path))
