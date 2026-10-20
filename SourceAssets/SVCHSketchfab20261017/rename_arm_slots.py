"""Rename the SVCh arm material slots and report the render-section layout.

The catalog icon hides arm sections by material slot name. The accepted SVD and
this mesh both use `MI_Manny_01/02`, yet the SVD icon comes out clean and this one
keeps its arms, so the slot naming is the cheapest variable to test: `Manny_Arms_01`
satisfies every branch of WeaponPresentationMaterials::IsArmName at once.
"""
import json

import unreal as u

PATH = '/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny'
mesh = u.load_asset(PATH)
if not mesh:
    raise RuntimeError('mesh missing: ' + PATH)

slots = mesh.get_editor_property('materials')
before = [str(s.material_slot_name) for s in slots]
report = {'before': before}

for index, material in enumerate(slots):
    name = str(material.material_slot_name)
    if 'Manny' in name:
        material.material_slot_name = u.Name('Manny_Arms_%s' % name.rsplit('_', 1)[-1])
        slots[index] = material

mesh.set_editor_property('materials', slots)
after = [str(s.material_slot_name) for s in mesh.get_editor_property('materials')]
report['after'] = after

saved = u.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False)
report['saved'] = bool(saved)

print('SVCH_SLOT_RENAME ' + json.dumps(report), flush=True)
