"""Read/export installed optic interfaces for M24 fitting. No gameplay or captures."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
(O / 'Sources').mkdir(exist_ok=True)
paths = {
    'holographic': '/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_M4_Holographic',
    'panoramic_red_dot': '/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PanoramicRedDot',
    'prism_scope_2x': '/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_PrismScope2X',
    'lpvo_1_6x': '/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVO1to6X',
    'lpvo_ring': '/Game/Weapons/AttachmentFinish20260913/M4/Meshes/SM_LPVORing',
    'eoth_holographic': '/Game/Weapons/CommonHK41620260930/Meshes/SM_Common_eoth_holographic',
    'kv_scope_4x': '/Game/Weapons/KVScope20261019/SM_KVScope_Common',
    'thermal_scope': '/Game/Weapons/ThermalScope20261006/Runtime/SM_Thermal_Common',
    'thermal_selector': '/Game/Weapons/ThermalScope20261006/Runtime/SM_ThermalSelector_Common',
}
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
rows = {}
for key, path in paths.items():
    if path in dirty: raise RuntimeError('Unsaved source retained: ' + path)
    mesh = u.load_asset(path)
    if not mesh: raise RuntimeError('Missing optic: ' + path)
    slots = []
    for s in mesh.static_materials:
        m = s.material_interface
        row = {'slot': str(s.material_slot_name), 'material': m.get_path_name() if m else None}
        if isinstance(m, u.MaterialInstanceConstant):
            row['parent'] = m.parent.get_path_name()
            row['scalars'] = {str(x.parameter_info.name): x.parameter_value for x in m.scalar_parameter_values}
        slots.append(row)
    sockets = {}
    for name in ('SightRear', 'SightFront', 'SightUp', 'AimCenter', 'ZoomRing', 'ZoomPivot'):
        s = mesh.find_socket(name)
        if s: sockets[name] = {'location': list(s.relative_location.to_tuple()), 'rotation': list(s.relative_rotation.to_tuple())}
    task = u.AssetExportTask()
    task.object = mesh; task.filename = str(O / 'Sources' / (key + '.fbx'))
    task.automated = True; task.prompt = False; task.replace_identical = True
    task.exporter = u.StaticMeshExporterFBX()
    task.options = u.FbxExportOption(); task.options.level_of_detail = False
    if not u.Exporter.run_asset_export_task(task): raise RuntimeError('Export failed: ' + path)
    rows[key] = {'source': path, 'materials': slots, 'sockets': sockets, 'fbx': task.filename}
(O / 'sources.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print('M24_COMMON_OPTIC_SOURCES_EXPORTED', len(rows), flush=True)
