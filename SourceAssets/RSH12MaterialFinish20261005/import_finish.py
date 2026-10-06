"""Apply only the authorized RSH material fixes and save production assets."""
import json
import runpy
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).resolve().parent
P = O.parents[1]
S = O.parent
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
if Path(u.Paths.project_dir()).resolve() != P:
    raise RuntimeError('Unexpected project')
headless = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not headless and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is active; material installation not started')

hosts = ['/Game/Weapons/RSH12/Native71520261003/' + x for x in
         ('single/SK_RSH12_Manny', 'r/SK_Dual_RSH12_r', 'l/SK_Dual_RSH12_l')]
grips = ['/Game/Weapons/RSH12/Foregrips20261004/Meshes/SM_RSH12_' + x for x in
         ('vertical', 'tactical_vertical', 'canted', 'prism', 'angled')]
ormpath = '/Game/Weapons/RSH12/QuickDrawGrip20261005/Textures/T_RSH12_QuickDrawGrip_GraphiteFrame_ORM'
recesspath = '/Game/Weapons/RSH12/CubeSuppressor20261004/Materials/M_RSH12_Cube_Recess'
tablepath = '/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials'
targets = set(hosts + grips + [ormpath, recesspath, tablepath])
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_name() in targets or p.get_name().startswith('/Game/Weapons/RSH12/MaterialFinish20261005/')]
if dirty:
    raise RuntimeError('Target assets have unsaved changes: ' + str(dirty))

receipt = dict(complete=False, saved=[], bindings={}, runtime_tested=False, rendered=False)
def record():
    (O / 'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')

def backup(package):
    source = P / 'Content' / (package.removeprefix('/Game/') + '.uasset')
    dest = O / 'BeforeAssets' / source.relative_to(P / 'Content')
    if source.exists() and not dest.exists():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)

for target in sorted(targets):
    backup(target)

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Asset save failed: ' + asset.get_path_name())
    if asset.get_path_name() not in receipt['saved']:
        receipt['saved'].append(asset.get_path_name())
    record()

helper = runpy.run_path(str(O / 'finish_materials.py'))
load = helper['load']
front = helper['make_foregrip_materials'](save)
loader = helper['make_loader_materials'](save)
binding = helper['FOREGRIP_BINDINGS']

for path in grips:
    mesh = load(path)
    slots = list(mesh.static_materials)
    for i, slot in enumerate(slots):
        label = str(slot.material_slot_name)
        key = next((k for k in binding if label.startswith(k)), None)
        if key is None:
            raise RuntimeError('Unrecognized RSH grip slot: ' + label)
        slot.material_interface = load(binding[key])
        slots[i] = slot
    mesh.set_editor_property('static_materials', slots)
    save(mesh)
    receipt['bindings'][path] = {str(s.material_slot_name):s.material_interface.get_path_name()
                                for s in mesh.static_materials}
    record()

for path in hosts:
    mesh = load(path)
    slots = list(mesh.materials)
    for i, slot in enumerate(slots):
        key = next((k for k in loader if k in str(slot.material_slot_name)), None)
        if key:
            slot.material_interface = loader[key]
            slots[i] = slot
    mesh.set_editor_property('materials', slots)
    save(mesh)
    receipt['bindings'][path] = {str(s.material_slot_name):s.material_interface.get_path_name()
                                for s in mesh.materials}
    record()

task = u.AssetImportTask()
task.filename = str(S / 'RSH12QuickDrawGrip20261005/Textures/T_RSH12_QuickDrawGrip_GraphiteFrame_ORM.png')
task.destination_path, task.destination_name = ormpath.rsplit('/', 1)
task.automated = True
task.replace_existing = True
task.replace_existing_settings = True
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
tex = load(ormpath)
tex.set_editor_property('srgb', False)
tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_MASKS)
tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
E.set_metadata_tag(tex, 'RSHMaterialFinish', 'Graphite anodized metal: ORM B=1; original AO and roughness preserved')
save(tex)
receipt['quickdraw_frame_metallic'] = 1.

recess = load(recesspath)
metal = L.get_material_property_input_node(recess, u.MaterialProperty.MP_METALLIC)
if not isinstance(metal, u.MaterialExpressionConstant):
    raise RuntimeError('Unexpected recess metallic expression; not overwritten')
metal.set_editor_property('r', 0.)
errors = L.recompile_material(recess)
if errors:
    raise RuntimeError('Recess shader compilation failed: ' + str(errors))
save(recess)
receipt['recess_metallic'] = 0.

helper['register_weather']([*front.values(), *loader.values()], save)
receipt['weather_materials'] = [m.get_path_name() for m in [*front.values(), *loader.values()]]
receipt['complete'] = True
record()
print('RSH_MATERIAL_FINISH_SAVED', json.dumps({'saved':len(receipt['saved']), 'bound_meshes':len(receipt['bindings']),
      'receipt':str(O / 'import_receipt.json')}), flush=True)
