import json
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/TemperateForestRealism20261110')
OUT = ROOT / 'Donors'
OUT.mkdir(exist_ok=True)
report = {'textures': [], 'meshes': []}
for name in ['T_Ground_Leaves_01_CA', 'T_Ground_Leaves_01_NA']:
    tex = u.load_asset('/Game/RuralAustralia/Landscape/Textures/' + name)
    report['textures'].append({'path': tex.get_path_name(), 'compression': str(tex.get_editor_property('compression_settings')),
                               'srgb': tex.get_editor_property('srgb'), 'size': [tex.blueprint_get_size_x(), tex.blueprint_get_size_y()]})
    if name.endswith('_CA'):
        task = u.AssetExportTask()
        task.object = tex
        task.filename = str(OUT / (name + '.png'))
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        task.exporter = u.TextureExporterPNG()
        report['exported'] = u.Exporter.run_asset_export_task(task)
for asset in json.loads((ROOT / 'inputs.json').read_text())['fields']['fallen_logs']:
    mesh = u.load_asset(asset)
    b = mesh.get_bounding_box()
    report['meshes'].append({'path': asset, 'min': [b.min.x,b.min.y,b.min.z], 'max': [b.max.x,b.max.y,b.max.z]})
(OUT / 'sources.json').write_text(json.dumps(report, indent=2))
u.log('FOREST_DONORS_READ ' + str(len(report['textures'])))
