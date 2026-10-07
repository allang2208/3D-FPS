"""Direct GLB import to new M27 packages only; run with PythonScript commandlet."""
import json
import traceback
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/MeshyImport20261005V1')
DEST = '/Game/Monsters/MantisM27/MeshyImportV1'
RECEIPT = ROOT / 'ue_import_receipt.json'
report = {'status': 'started', 'destination': DEST, 'saved': [],
          'runtime_tested': False, 'preview_rendered': False, 'gameplay_registered': False}

def save(asset):
    if not u.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    report['saved'].append({'path': asset.get_path_name(), 'class': asset.get_class().get_name()})
    RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

try:
    source_report = json.loads((ROOT / 'source_inspection.json').read_text(encoding='utf-8'))
    report['source_sha256'] = source_report['source_sha256']
    if u.EditorAssetLibrary.does_directory_exist(DEST):
        raise RuntimeError('Destination already exists; preserve it and inspect its receipt before retrying.')
    manager = u.InterchangeManager.get_interchange_manager_scripted()
    source_data = u.InterchangeManager.create_source_data(source_report['archived_source'])
    params = u.ImportAssetParameters()
    params.set_editor_property('is_automated', True)
    params.set_editor_property('replace_existing', False)
    params.set_editor_property('destination_name', 'SM_MantisM27_MeshySource')
    result = manager.import_asset(DEST, source_data, params)
    success = result[0] if isinstance(result, tuple) else result
    if not success:
        raise RuntimeError('Interchange GLB import failed')
    # The synchronous import has completed; save only objects under this new folder.
    paths = u.EditorAssetLibrary.list_assets(DEST, recursive=True, include_folder=False)
    assets = [u.load_asset(path) for path in paths]
    meshes = [asset for asset in assets if isinstance(asset, u.StaticMesh)]
    if len(meshes) != 1:
        raise RuntimeError('Expected one static mesh; found ' + str(len(meshes)))
    mesh = meshes[0]
    target = DEST + '/SM_MantisM27_MeshySource'
    if mesh.get_path_name().split('.')[0] != target:
        if not u.EditorAssetLibrary.rename_asset(mesh.get_path_name(), target):
            raise RuntimeError('Mesh naming failed')
        mesh = u.load_asset(target)
    settings = mesh.get_editor_property('nanite_settings')
    settings.enabled = False
    mesh.set_editor_property('nanite_settings', settings)
    # Keep source surface, imported tangents/materials and original scale intact.
    materials = [slot.material_interface for slot in mesh.static_materials]
    if not materials or any(material is None for material in materials):
        raise RuntimeError('Imported mesh has an unbound material slot')
    bounds = mesh.get_bounds()
    report['mesh'] = mesh.get_path_name()
    report['mesh_bounds_cm'] = {'origin': [bounds.origin.x, bounds.origin.y, bounds.origin.z],
                              'box_extent': [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z]}
    report['materials'] = [material.get_path_name() for material in materials]
    report['source_triangles'] = sum(p['triangles'] for p in source_report['primitives'])
    report['kind'] = 'StaticMesh appearance source; skeleton and animation absent in supplied GLB'
    for asset in assets:
        if asset is not None and not isinstance(asset, u.StaticMesh):
            save(asset)
    save(mesh)
    report['status'] = 'saved'
    RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    u.log('M27_DIRECT_IMPORT_SAVED ' + json.dumps(report, ensure_ascii=False))
except Exception:
    report['status'] = 'failed'
    report['error'] = traceback.format_exc()
    RECEIPT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    raise
