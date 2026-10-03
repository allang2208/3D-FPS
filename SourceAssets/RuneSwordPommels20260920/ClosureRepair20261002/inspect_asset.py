"""Read/export the actual shared meteor asset and its materials without edits."""
import unreal as u, json
from pathlib import Path
P = Path(__file__).parent
root = '/Game/Weapons/AzureRunesword20260913/Pommels20260920'
path = root + '/Models/SM_RunePommel_Meteor'
mesh = u.load_asset(path)
if not mesh:
    raise RuntimeError('Missing live shared meteor mesh: ' + path)
rows = {'asset': mesh.get_path_name(), 'slots': [], 'materials': []}
for slot in mesh.static_materials:
    rows['slots'].append({'slot': str(slot.material_slot_name), 'material': slot.material_interface.get_path_name() if slot.material_interface else None})
paths = [root+'/Materials/M_RunePommel_meteor_Opaque', root+'/Materials/M_RunePommel_meteor_Crystal',
         '/Game/Weapons/TangDao20261002/SurfaceV2/Materials/MI_TangDaoPommel_meteor',
         '/Game/Weapons/SharedSwordPommels20260920/Materials/MI_SharedPommel_meteor_FrostBronze']
for path in paths:
    mat = u.load_asset(path)
    row = {'path': path, 'chain': []}
    while mat:
        entry = {'asset': mat.get_path_name(), 'class': mat.get_class().get_name()}
        if isinstance(mat, u.MaterialInstanceConstant):
            overrides = mat.get_editor_property('base_property_overrides')
            entry['override_two_sided'] = overrides.get_editor_property('override_two_sided')
            entry['two_sided'] = overrides.get_editor_property('two_sided')
            row['chain'].append(entry)
            mat = mat.get_editor_property('parent')
        else:
            entry['two_sided'] = mat.get_editor_property('two_sided')
            entry['blend_mode'] = str(mat.get_editor_property('blend_mode'))
            entry['front_material_node'] = str(u.MaterialEditingLibrary.get_material_property_input_node(mat, u.MaterialProperty.MP_FRONT_MATERIAL))
            row['chain'].append(entry)
            break
    rows['materials'].append(row)
task = u.AssetExportTask()
task.object = mesh
task.filename = str(P/'CurrentUE_Meteor.fbx')
task.automated = True
task.prompt = False
task.replace_identical = True
task.exporter = u.StaticMeshExporterFBX()
task.options = u.FbxExportOption()
task.options.ascii = False
task.options.level_of_detail = False
task.options.collision = False
if not u.Exporter.run_asset_export_task(task):
    raise RuntimeError('Could not export actual meteor mesh for topology diagnosis')
(P/'asset_findings.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
print('METEOR_ASSET_INSPECTION_SAVED', json.dumps(rows, ensure_ascii=False))
