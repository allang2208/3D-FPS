"""Retain the saved R01 finish after an explicitly invoked legacy import.

Does not rebuild graphs or meshes. Accepts the captured old binding or the
current R01 binding, preserving an independently edited slot by stopping.
"""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
R = json.loads((O / 'recipe.json').read_text())
C = json.loads((O / 'Input/current.json').read_text())
receipt = json.loads((O / 'apply_receipt.json').read_text())
if not receipt.get('complete'):
    raise RuntimeError('R01 save is not complete')
if Path(u.Paths.project_dir()).resolve() != O.parents[3]:
    raise RuntimeError('Wrong project')
E = u.EditorAssetLibrary
dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('Stop PIE before restoring material bindings')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
jobs = []
for path, rows in R['bindings'].items():
    mesh = u.load_asset(path)
    if not mesh:
        raise RuntimeError('Missing current mesh ' + path)
    prop = 'materials' if C['meshes'][path]['skeletal'] else 'static_materials'
    slots = list(mesh.get_editor_property(prop))
    by_name = {str(s.material_slot_name): i for i, s in enumerate(slots)}
    changed = False
    for row in rows:
        i = by_name.get(row['slot'])
        if i is None:
            raise RuntimeError('Changed material slot identity ' + path + ' ' + row['slot'])
        target = receipt['instances'][row['key']]['path']
        slot = slots[i]
        before = slot.material_interface.get_path_name() if slot.material_interface else None
        if before not in (row['before'], target):
            raise RuntimeError('Preserve separately edited binding ' + path + ' ' + row['slot'])
        if before != target:
            slot.material_interface = u.load_asset(target)
            if not slot.material_interface:
                raise RuntimeError('Missing saved finish ' + target)
            slots[i] = slot
            changed = True
    if changed:
        if path.split('.')[0] in dirty:
            raise RuntimeError('Unsaved mesh ' + path)
        jobs.append((mesh, prop, slots))
weather = u.load_asset(C['weather']['path'])
if not weather:
    raise RuntimeError('Missing PKM weather library')
mapping = dict(weather.get_editor_property('wet_materials'))
paths = {str(k): v.get_path_name() if v else None for k, v in mapping.items()}
wet_changed = False
for row in receipt['instances'].values():
    if paths.get(row['path']) != row['path']:
        mapping[row['path']] = u.load_asset(row['path'])
        wet_changed = True
if wet_changed and weather.get_path_name().split('.')[0] in dirty:
    raise RuntimeError('Unsaved PKM weather library')
if wet_changed:
    weather.set_editor_property('wet_materials', mapping)
    if not E.save_loaded_asset(weather, False):
        raise RuntimeError('Weather save failed')
for mesh, prop, slots in jobs:
    mesh.set_editor_property(prop, slots)
    E.set_metadata_tag(mesh, 'PKMSurfaceFinishRevision', R['version'])
    if not E.save_loaded_asset(mesh, False):
        raise RuntimeError('Binding save failed ' + mesh.get_path_name())
print('WEAPON_SURFACE_PKM_R01_REBOUND', len(jobs), 'meshes; tested=False', flush=True)
