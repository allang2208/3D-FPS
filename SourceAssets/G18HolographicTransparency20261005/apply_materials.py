"""Save the G18 aperture fix without mesh reimport, scene creation or tests."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
PROJECT = OUT.parents[1]
ROOT = '/Game/Weapons/G18/Integrated20260929'
MESH = ROOT + '/Attachments/SM_G18_holographic'
BODY = ROOT + '/Materials/M_G18_HoloBodyMasked'
WEATHER = ROOT + '/DA_G18_WetMaterials'
targets = {MESH, BODY, WEATHER}
receipt = {'saved': [], 'runtime_tested': False, 'rendered_for_acceptance': False}


def record():
    (OUT / 'save_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')


def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()], False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    record()


content = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())).resolve()
if content != (PROJECT / 'Content').resolve():
    raise RuntimeError('Wrong project content mount')
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_name() in targets]
if dirty:
    raise RuntimeError('Preserve unsaved target assets: ' + str(dirty))
for target in sorted(targets):
    package = content / (target.removeprefix('/Game/') + '.uasset')
    before = OUT / 'BeforePackages' / package.relative_to(content)
    if package.exists() and not before.exists():
        before.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(package, before)

mesh = u.load_asset(MESH)
if not mesh:
    raise RuntimeError('Missing active G18 holographic mesh')
slots = list(mesh.get_editor_property('static_materials'))
receipt['before_materials'] = {str(s.material_slot_name): s.material_interface.get_path_name() for s in slots}
if not {'M_HoloBody', 'M_HoloReticle'}.issubset(receipt['before_materials']):
    raise RuntimeError('G18 holographic slot layout changed')
helpers = runpy.run_path(str(PROJECT / 'Tools/Weapons/g18_holographic_material.py'))
reticle = u.load_asset(helpers['RETICLE_PATH'])
if not reticle:
    raise RuntimeError('Missing existing holographic reticle material')
body = helpers['ensure_holo_body'](save)
for index, slot in enumerate(slots):
    if str(slot.material_slot_name) == 'M_HoloBody':
        slot.material_interface = body
    elif str(slot.material_slot_name) == 'M_HoloReticle':
        slot.material_interface = reticle
    slots[index] = slot
mesh.set_editor_property('static_materials', slots)
u.EditorAssetLibrary.set_metadata_tag(mesh, 'G18HolographicTransparency',
    '20261005: UV0 aperture alpha retained on G18 housing; original masked reticle')
save(mesh)
helpers['register_wet_material'](body, save)
receipt['materials'] = {str(s.material_slot_name): s.material_interface.get_path_name() for s in slots}
receipt['mesh_geometry'] = 'unchanged; no reimport'
receipt['calibration'] = 'existing sockets and transforms unchanged'
receipt['status'] = 'materials_bound_and_saved'
record()
print('G18_HOLOGRAPHIC_MATERIALS_SAVED', flush=True)
