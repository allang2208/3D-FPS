"""Export selected installed firearms for assembly authoring.

UE 5.8's skeletal FBX export needs a real RHI even with material baking disabled.
For a commandlet use -AllowCommandletRendering -RenderOffscreen, not -NullRHI.
ASSEMBLY_ROOT and ASSEMBLY_WEAPONS may be supplied by a production batch.
"""
import json, re
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
ROOT = Path(globals().get('ASSEMBLY_ROOT', P / 'SourceAssets/GunAssemblyCompletion20261015'))
OUT = ROOT / 'Sources'
OUT.mkdir(parents=True, exist_ok=True)
result = {'weapons': []}
for key, header in globals().get('ASSEMBLY_WEAPONS', [('hk416', 'HK416'), ('super90', 'Super90'), ('g18', 'G18'),
                    ('pit_viper2011', 'PitViper2011'), ('rsh12', 'RSH12')]):
    text = (P / f'Source/FPSGAME/Weapons/{header}WeaponAssets.h').read_text(encoding='utf-8-sig')
    path = re.search(r'\bMeshPath\s*=\s*TEXT\("([^"]+)"\)', text).group(1).split('.')[0]
    mesh = u.load_asset(path)
    if not isinstance(mesh, u.SkeletalMesh):
        raise RuntimeError('Missing installed weapon: ' + path)
    fbx = OUT / (key + '.fbx')
    task = u.AssetExportTask()
    task.object = mesh
    task.filename = str(fbx)
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    task.exporter = u.SkeletalMeshExporterFBX()
    options = u.FbxExportOption()
    options.ascii = False
    options.level_of_detail = False
    options.collision = False
    options.bake_material_inputs = u.FbxMaterialBakeMode.DISABLED
    task.options = options
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Export failed: ' + path)
    materials = [{'slot': str(s.material_slot_name),
                  'asset': s.material_interface.get_path_name() if s.material_interface else None}
                 for s in mesh.get_editor_property('materials')]
    result['weapons'].append({'key': key, 'definition': 'ue_' + key,
                             'source_mesh': path, 'fbx': str(fbx), 'materials': materials})
    (ROOT / 'sources.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ASSEMBLY_SOURCE_EXPORTED', key)
