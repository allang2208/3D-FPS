"""Read the active tactical attachment meshes for new model fitting."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlessedLaser20261006/Model/Sources')
OUT.mkdir(parents=True, exist_ok=True)
paths = {
    **{k: '/Game/Weapons/TacticalDevices20260913/' + k + '/laser/SM_TacticalDevice' for k in ['M4', 'AKM', 'QBZ191']},
    'M1911': '/Game/Weapons/M1911/CompactFit20260913/laser/SM_TacticalDevice',
    'G18': '/Game/Weapons/G18/Integrated20260929/Attachments/SM_G18_laser',
    'PitViper2011': '/Game/Weapons/PitViper2011/Attachments20261002/SM_PitViper2011_laser',
    'DanWesson715': '/Game/Weapons/DanWesson715/AccessoryPolymer20260914/Attachments/laser/SM_TacticalDevice',
    'RSH12': '/Game/Weapons/RSH12/Tactical20261005/Meshes/SM_RSH12_laser',
    'ASH12': '/Game/Weapons/ASH12/TacticalDevices20260920/laser/SM_ASH12_laser',
    'M16': '/Game/Weapons/M16A2/UniversalAttachments20260920/Meshes/SM_M16_laser',
    'A762': '/Game/Weapons/A762/Accessories05/Meshes/SM_A762_laser',
    'SVD': '/Game/Weapons/SVDDragunov20260922/Accessories20260923/Meshes/SM_SVD_laser',
    'PKM': '/Game/Weapons/PKMLowpoly20260922/Accessories14/Meshes/SM_PKM_laser',
    'LMG201': '/Game/Weapons/LMG201/Accessories22/Meshes/SM_LMG201_laser',
    'HK416': '/Game/Weapons/HK416/Reworked20260930/Attachments/SM_HK416_laser',
}
report = {}
for family, path in paths.items():
    mesh = u.load_asset(path)
    if mesh is None:
        raise RuntimeError('Missing fitting source: ' + path)
    task = u.AssetExportTask()
    task.object = mesh
    task.exporter = u.StaticMeshExporterFBX()
    task.filename = str(OUT / (family + '.fbx'))
    task.automated = True
    task.prompt = False
    task.replace_identical = True
    options = u.FbxExportOption()
    options.set_editor_property('collision', False)
    options.set_editor_property('level_of_detail', False)
    task.options = options
    if not u.Exporter.run_asset_export_task(task):
        raise RuntimeError('Fitting export failed: ' + family)
    sockets = {}
    for name in ['Emitter', 'AimGuide']:
        sock = mesh.find_socket(name)
        if not sock:
            raise RuntimeError('Missing fitting socket: ' + family + '/' + name)
        p = sock.relative_location
        sockets[name] = [p.x, p.y, p.z]
    report[family] = {'source': path, 'fbx': task.filename, 'sockets_ue_cm': sockets,
                      'slots': [{'name': str(s.material_slot_name), 'material': s.material_interface.get_path_name() if s.material_interface else None} for s in mesh.static_materials]}
(OUT / 'mount-sources.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('BLESSED_MOUNT_SOURCES_EXPORTED ' + json.dumps({k: v['slots'] for k,v in report.items()}))
