"""Read-only material comparison for the reported black PKM hands."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
paths = {
    'PKM': '/Game/Weapons/PKMLowpoly20260922/Accessories14/SK_PKM_Manny_Modular',
    'M4': '/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416',
    'QBZ191': '/Game/Weapons/QBZ191/RearGrip20260913/SK_QBZ191_Manny',
    'ASH12': '/Game/Weapons/ASH12/Surface20260919/SK_ASH12_Surface',
}
report = {'meshes': {}, 'materials': {}}
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    report['pie_active'] = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world() is not None
    report['target_dirty'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                              if p.get_name().startswith('/Game/Weapons/PKMLowpoly20260922/')]
for name, path in paths.items():
    mesh = u.load_asset(path)
    rows = []
    for i, slot in enumerate(mesh.materials):
        mat = slot.material_interface
        rows.append({'index': i, 'slot': str(slot.material_slot_name),
                     'imported': str(slot.get_editor_property('imported_material_slot_name')),
                     'material': mat.get_path_name() if mat else None})
        if mat and ('Manny' in str(slot.material_slot_name) or 'Manny' in mat.get_name()):
            report['materials'][mat.get_path_name()] = {
                'parent': mat.parent.get_path_name() if isinstance(mat, u.MaterialInstance) and mat.parent else None,
                'textures': {str(n): str(u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(mat, n))
                             for n in u.MaterialEditingLibrary.get_texture_parameter_names(mat)}
                            if isinstance(mat, u.MaterialInstance) else {},
            }
    report['meshes'][name] = rows
(O/'asset_diagnosis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print('PKM29_ASSETS', json.dumps({'hands': {k: [v for v in rows if 'Manny' in str(v)] for k, rows in report['meshes'].items()},
                                  'parents': {k: v['parent'] for k,v in report['materials'].items()},
                                  'pie_active': report.get('pie_active'), 'target_dirty': report.get('target_dirty')}), flush=True)
