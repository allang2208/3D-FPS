"""Move the blast furnace into the building panel's 其他 (unclassified) tab.

    & UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this> -unattended -nop4 -nosplash

The 其他 tab lists only components whose palette ``Material`` field is empty
(see ``VoxelBuildWidget.cpp``:744). ``register``/``revise`` left the furnace
under ``stone``, which puts it in 材质 -> 石头 -> 其他构造 instead. This clears
that one field on that one entry, keeps every other entry and its live fields,
and writes back the before/after values.

Same mesh, same footprint, same pivot: only the drawer grouping changes, so no
mesh reimport is involved.
"""
import json
from pathlib import Path

import unreal as u

HERE = Path(__file__).resolve().parent
PALETTE = '/Game/Building/Voxels/Rounded/DA_VoxelBuildPalette'
TARGET_ID = 'blast_furnace'
receipt = {'palette': PALETTE, 'id': TARGET_ID, 'before': None, 'after': None,
           'entries': 0, 'saved': False, 'runtime_tested': False}


def log(message):
    print('[blast_furnace_drawer] ' + message, flush=True)


palette = u.load_asset(PALETTE)
if palette is None:
    raise RuntimeError('Active building palette missing: ' + PALETTE)

components = list(palette.get_editor_property('components'))
receipt['entries'] = len(components)

target = None
index = -1
for position, entry in enumerate(components):
    if str(entry.get_editor_property('id')) == TARGET_ID:
        target = entry
        index = position
        break
if target is None:
    raise RuntimeError('Palette entry missing: ' + TARGET_ID)

before_material = str(target.get_editor_property('material'))
before_mesh = target.get_editor_property('mesh').get_path_name() if target.get_editor_property('mesh') else None
before_footprint = [target.get_editor_property('footprint').x,
                    target.get_editor_property('footprint').y,
                    target.get_editor_property('footprint').z]
receipt['before'] = {'material': before_material, 'mesh': before_mesh, 'footprint': before_footprint}
log('before material=%r mesh=%s footprint=%s' % (before_material, before_mesh, before_footprint))

if before_material == 'None' or before_material == '':
    log('material already empty; nothing to change')
else:
    # Field only: the drawer grouping. Same mesh/footprint/pivot, so the
    # placement contract is untouched. An empty FName reads back as
    # Name("None") whose str() is "None", so the check below has to use
    # is_none() -- comparing str() to '' made the first pass report success
    # while the value silently stayed "stone".
    target.set_editor_property('material', u.Name(''))
    check_now = target.get_editor_property('material')
    if not (hasattr(check_now, 'is_none') and check_now.is_none()):
        raise RuntimeError('Clearing Material did not stick in memory: %r' % (check_now,))
    # The list from get_editor_property is a COPY, and so is each struct in it:
    # mutating the struct in place never reaches the asset. The array has to be
    # written back whole (that is how register/revise landed their entries).
    components[index] = target
    palette.set_editor_property('components', components)
    palette.modify()
    if not u.EditorLoadingAndSavingUtils.save_packages([u.load_package(PALETTE)], False):
        raise RuntimeError('Palette save failed')

# Re-load and confirm from the asset, not from the in-memory object.
check = u.load_asset(PALETTE)
found = None
for entry in check.get_editor_property('components'):
    if str(entry.get_editor_property('id')) == TARGET_ID:
        found = entry
        break
if found is None:
    raise RuntimeError('Entry lost after save: ' + TARGET_ID)
after_field = found.get_editor_property('material')
mesh_after = found.get_editor_property('mesh').get_path_name() if found.get_editor_property('mesh') else None
footprint_after = [found.get_editor_property('footprint').x,
                   found.get_editor_property('footprint').y,
                   found.get_editor_property('footprint').z]
if not (hasattr(after_field, 'is_none') and after_field.is_none()):
    raise RuntimeError('Saved Material is not empty: %r' % (after_field,))
receipt['after'] = {'material_str': str(after_field), 'material_is_none': True,
                    'classified_into_other_tab': True, 'mesh': mesh_after,
                    'footprint': footprint_after}
receipt['saved'] = True
log('after material empty (Name "None"), mesh=%s footprint=%s' % (mesh_after, footprint_after))

(HERE / 'drawer_receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2),
                                          encoding='utf-8')
print('BLAST_FURNACE_DRAWER_DONE ' + json.dumps(receipt, ensure_ascii=False), flush=True)
