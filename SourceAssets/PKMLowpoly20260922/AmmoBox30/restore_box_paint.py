"""Restore the two PKM reload boxes' olive paint, preserving current UV/rig.

Only two material copies, the live mesh bindings and its private wet library are
saved. Run in a Python commandlet with the editor closed, or the existing bridge.
"""
import json
import shutil
import sys
from pathlib import Path
import unreal as u

O = Path(__file__).parent
R = O.parent
P = '/Game/Weapons/PKMLowpoly20260922'
DEST = P + '/AmmoBox30/Materials'
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not commandlet:
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PKM30: stop PIE before changing the weapon material bindings')

mesh = u.load_asset(P + '/Accessories14/SK_PKM_Manny_Modular')
table = u.load_asset(P + '/Finish20/DA_PKM_WetMaterials')
if not mesh or not table:
    raise RuntimeError('PKM30 requires the current PKM mesh and private weather table')
sys.path.insert(0, str(R / 'Belt08'))
from material_binding import imported_name, box_paint_override

slots = mesh.materials
indices = [i for i, s in enumerate(slots)
           if imported_name(s).endswith(('__OldBox', '__NewBox'))]
if len(indices) != 2:
    raise RuntimeError('Expected exactly two existing PKM box sections')
mapping = dict(table.get_editor_property('wet_materials'))
source_dry = slots[indices[0]].material_interface
if any(slots[i].material_interface != source_dry for i in indices):
    raise RuntimeError('The two box sections have different materials; preserve their edits')
source_wet = next((v for k, v in mapping.items() if str(k) == source_dry.get_path_name()), None)
if not source_wet:
    raise RuntimeError('Missing existing wet partner for the current box finish')

dest_paths = [DEST + '/M_PKM_AmmoBoxPaint_Dry', DEST + '/M_PKM_AmmoBoxPaint_Wet']
targets = [mesh.get_path_name().split('.')[0], table.get_path_name().split('.')[0]] + dest_paths
if not commandlet:
    conflict = set(targets) & {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if conflict:
        raise RuntimeError('PKM30 targets have unsaved edits: ' + str(sorted(conflict)))

content = Path(u.Paths.project_dir()).resolve() / 'Content'
for package in targets:
    relative = package.removeprefix('/Game/') + '.uasset'
    source = content / relative
    backup = O / 'BeforeImport' / relative
    if source.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup)

report = {'mesh': mesh.get_path_name(), 'wet_library': table.get_path_name(),
          'source_dry': source_dry.get_path_name(), 'source_wet': source_wet.get_path_name(),
          'saved': [], 'bindings_before': [], 'bindings_after': [],
          'mesh_reimported': False, 'game_tested': False}
for i in indices:
    s = slots[i]
    report['bindings_before'].append({'index': i, 'slot': str(s.material_slot_name),
                                     'material': s.material_interface.get_path_name()})
receipt = O / 'import_receipt.json'

def record():
    receipt.write_text(json.dumps(report, indent=2), encoding='utf-8')

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('PKM30 save failed: ' + asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    record()

materials = []
for source, path in zip((source_dry, source_wet), dest_paths):
    mat = u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(source.get_path_name(), path)
    if not isinstance(mat, u.Material):
        raise RuntimeError('Expected a copied PKM finish material: ' + path)
    custom = {str(n.get_editor_property('description')): n for n in L.get_material_expressions(mat)
              if isinstance(n, u.MaterialExpressionCustom)}
    for label, filename in [('PKM20 restrained scuffs', 'OlivePaint.hlsl'),
                            ('PKM20 fine exposed metal', 'PaintMetallic.hlsl')]:
        if label not in custom:
            raise RuntimeError('PKM30 source finish node missing: ' + label)
        custom[label].set_editor_property('code', (O / filename).read_text(encoding='utf-8'))
    # Retain the matte roughness, micro scratches, atlas normal/AO and wet overlay.
    E.set_metadata_tag(mat, 'PKM30_Finish', 'Independent olive ammo-box paint; linear pigment .047 .065 .025')
    E.set_metadata_tag(mat, 'PKM20_Category', 'paint')
    errors = [str(v) for v in L.recompile_material(mat)]
    if errors:
        raise RuntimeError('PKM30 material compile failed: ' + str(errors))
    materials.append(mat)

dry, wet = materials
E.set_metadata_tag(wet, 'PKM20_WetSource', dry.get_path_name())
save(dry)
save(wet)
mapping[dry.get_path_name()] = wet
table.set_editor_property('wet_materials', mapping)
save(table)

for i in indices:
    s = slots[i]
    s.material_interface = box_paint_override(imported_name(s))
    if not s.material_interface:
        raise RuntimeError('PKM30 box binding could not resolve the new material')
    slots[i] = s
mesh.set_editor_property('materials', slots)
E.set_metadata_tag(mesh, 'PKMAmmoBoxFinishRevision', 'AmmoBox30: olive paint on OldBox and NewBox; existing section identities retained')
save(mesh)

for i in indices:
    s = mesh.materials[i]
    report['bindings_after'].append({'index': i, 'slot': str(s.material_slot_name),
                                    'material': s.material_interface.get_path_name()})
actual_map = table.get_editor_property('wet_materials')
report['wet_partner'] = next(v.get_path_name() for k, v in actual_map.items() if str(k) == dry.get_path_name())
report['complete'] = True
record()
print('PKM30_SAVED', json.dumps({'saved': report['saved'], 'boxes': report['bindings_after'],
                                'wet_partner': report['wet_partner'], 'game_tested': False}), flush=True)
