"""Install the extended magazines as factory-part extensions.

Every rifle's extended magazine now comes from that rifle's own factory
magazine and uses the same material as the rifle's magazine slot, so the part
is "unified" with the gun by construction instead of through a baked coating:

  M4A1    SM_ExtMag_M440   -> /Game/Weapons/M4InfimaV3/Magazine_Light_001
  QBZ-191 SM_ExtMag_QBZ40  -> .../M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer
  AKM     SM_ExtMag_AKM40  -> /Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR
                             (rebuilt from AKM_FactoryMagazine_Preview, so it also
                              keeps the AKM's own magazine shape and position)

Run: UnrealEditor-Cmd.exe FPSGAME.uproject -run=pythonscript -script=<this file>
"""
import unreal as u
import json
import sys
from pathlib import Path

O = Path(__file__).parent
D = '/Game/Weapons/ExtMagUniversal20260917'
A = u.AssetToolsHelpers.get_asset_tools()
E = u.EditorAssetLibrary

JOBS = {
    'SM_ExtMag_M440': dict(
        fbx=None,
        magazine_material='/Game/Weapons/M4InfimaV3/Magazine_Light_001.Magazine_Light_001',
        rifle='M4',
        note='factory M4 magazine lengthened; material = that rifle magazine slot material'),
    'SM_ExtMag_QBZ40': dict(
        fbx=None,
        magazine_material='/Game/Weapons/QBZ191/Attachments20260913/Materials/'
                           'M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer.'
                           'M_QBZ191_Unified_M_QBZ191_Wear_Magazine_polymer',
        rifle='QBZ191',
        note='factory QBZ-191 magazine lengthened; material = that rifle magazine slot material'),
    'SM_ExtMag_AKM40': dict(
        fbx='SM_ExtMag_AKM40_factory.fbx',
        magazine_material='/Game/Weapons/AKMIntegration/SovietFab/M_AKM_Soviet_PBR.M_AKM_Soviet_PBR',
        rifle='AKM',
        note='factory AKM magazine lengthened in place; material = that rifle magazine slot material'),
}


def save(asset):
    # wepaon-finish.md: a locked editor makes the external save fail silently or
    # throw, so every asset records its own outcome instead of aborting the run.
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())


ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ONLY = set(ARGV)

def install(name, cfg):
    if cfg['fbx']:
        task = u.AssetImportTask()
        task.filename = str(O / 'FBX' / cfg['fbx'])
        task.destination_path = D
        task.destination_name = name
        opt = u.FbxImportUI()
        opt.automated_import_should_detect_type = False
        opt.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_materials = False
        opt.import_textures = False
        opt.import_animations = False
        opt.static_mesh_import_data.combine_meshes = True
        opt.static_mesh_import_data.convert_scene_unit = False
        opt.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options = opt
        task.automated = True
        task.replace_existing = True
        task.save = False
        A.import_asset_tasks([task])

    mesh = u.load_asset(D + '/' + name)
    if not mesh:
        return 'MESH MISSING'
    material = u.load_asset(cfg['magazine_material'])
    if not material:
        return 'MATERIAL MISSING ' + cfg['magazine_material']
    slots = mesh.get_editor_property('static_materials')
    for index, slot in enumerate(slots):
        slot.material_interface = material
        slots[index] = slot
    mesh.set_editor_property('static_materials', slots)
    E.set_metadata_tag(mesh, 'ExtMagSource', 'factory magazine, lengthened 6 cm')
    E.set_metadata_tag(mesh, 'ExtMagMaterial', cfg['magazine_material'])
    save(mesh)

    bounds = mesh.get_bounds()
    return {
        'material': material.get_path_name(),
        'rifle': cfg['rifle'],
        'slots': [str(slot.material_slot_name) for slot in slots],
        'lod0_vertices': mesh.get_num_vertices(0),
        'lod0_triangles': mesh.get_num_triangles(0),
        'bounds_cm': [round(bounds.box_extent.x * 2, 2), round(bounds.box_extent.y * 2, 2),
                      round(bounds.box_extent.z * 2, 2)],
        'note': cfg['note'],
    }


report = {}
for name, cfg in JOBS.items():
    if ONLY and name not in ONLY:
        continue
    try:
        report[name] = install(name, cfg)
    except Exception as err:
        report[name] = 'FAILED (editor may hold the asset): %s' % err

(O / 'factory_install_receipt.json').write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
u.log('EXTMAG_FACTORY_INSTALLED ' + json.dumps(report, ensure_ascii=False, default=str))
