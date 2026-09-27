"""Import/save only the six potion-use derivatives, reusing original materials."""
import unreal, json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/PotionUse20260926'
manifest = json.loads((OUT / 'manifest.json').read_text(encoding='utf-8'))
original = json.loads((ROOT / 'SourceAssets/Consumables5080_20260910/UE/manifest.json').read_text())
tools = unreal.AssetToolsHelpers.get_asset_tools()
destination = '/Game/Items/Consumables/PotionUse'
receipt = {}
for name, entry in manifest.items():
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_materials = options.import_textures = options.import_as_skeletal = False
    options.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    options.automated_import_should_detect_type = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.one_convex_hull_per_ucx = True
    task = unreal.AssetImportTask()
    task.filename = entry['file']
    task.destination_path, task.destination_name = destination, name
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.options = options
    tools.import_asset_tasks([task])
    mesh = unreal.load_asset(destination + '/' + name)
    if not isinstance(mesh, unreal.StaticMesh): raise RuntimeError('Potion import failed: ' + name)
    materials = {}
    family = entry['family']
    for i, material in enumerate(original[family]['materials']):
        path = '/Game/Items/Consumables/' + family + '/M_' + family + '_' + str(i)
        materials[material.replace(' ', '_')] = unreal.load_asset(path)
    for i, slot in enumerate(mesh.static_materials):
        material = materials.get(str(slot.material_slot_name))
        if not material: raise RuntimeError('Unmapped potion material: ' + str(slot.material_slot_name))
        mesh.set_material(i, material)
    nanite = mesh.get_editor_property('nanite_settings')
    nanite.enabled = False
    mesh.set_editor_property('nanite_settings', nanite)
    if not unreal.EditorAssetLibrary.save_loaded_asset(mesh): raise RuntimeError('Save failed: ' + name)
    receipt[name] = {'asset': mesh.get_path_name(), 'saved': True, 'source': entry['source']}
(OUT / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
unreal.log('POTION_PARTS_SAVED')
