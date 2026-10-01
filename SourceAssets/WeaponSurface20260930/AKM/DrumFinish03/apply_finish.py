"""Author the missing polymer finish on AKM's drum; preserve the R02 steel branch."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
prepare_only = bool(globals().get('PREPARE_ONLY', False))
P = Path('D:/FPS3D/FPSGAME').resolve()
# The online checkout shares this exact Content directory by a junction. Use
# its already-open editor only when the physical asset root is the same.
if Path(u.Paths.project_content_dir()).resolve() != (P / 'Content').resolve():
    raise RuntimeError('Wrong physical Content directory')
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
VERSION = 'AKM-DrumFinish03-20261001'
SOURCE = '/Game/Weapons/AKMIntegration/SurfaceStandard20261001/Master/M_AKM_R01_27a85f71a9b7'
DEST = '/Game/Weapons/AKMIntegration/SurfaceStandard20261001/Master/M_AKM_DrumFinish03'
INSTANCE = '/Game/Weapons/AKMIntegration/SurfaceStandard20261001/Materials/MI_AKM_R01_magazine_dd9b3b77ba'
MESH = '/Game/Weapons/AttachmentFinish20260913/AKM/Meshes/SM_AKM_drum'
params = {'Drum_ShellStrength': 1., 'Drum_ShellRoughness': .42, 'Drum_ShellSourceRoughness': .22}
tint = [.026, .027, .029]
receipt = {'version': VERSION, 'complete': False, 'geometry_changed': False, 'tested': False, 'saved': []}
rp = O / 'apply_receipt.json'
if rp.exists():
    previous = json.loads(rp.read_text())
    if previous.get('version') == VERSION:
        receipt = previous
        receipt['complete'] = False


def record():
    rp.write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Save failed ' + obj.get_path_name())
    if obj.get_path_name() not in receipt['saved']:
        receipt['saved'].append(obj.get_path_name())
    record()


def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n


def wire(src, dest, pin):
    n, channel = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, channel, dest, pin):
        raise RuntimeError('Cannot connect ' + pin)


def custom(m, label, filename, inputs, size):
    n = node(m, u.MaterialExpressionCustom, description=label,
        code=(O / filename).read_text(), output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for name, source in inputs.items():
        wire(source, n, name)
    return n


dirty = set()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE active; drum finish prepared but not saved')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path in (SOURCE, INSTANCE, MESH):
    if path in dirty:
        raise RuntimeError('Preserve unsaved asset ' + path)
mi, source, mesh = u.load_asset(INSTANCE), u.load_asset(SOURCE), u.load_asset(MESH)
if not all((mi, source, mesh)):
    raise RuntimeError('Missing production drum source')
parent = mi.get_editor_property('parent').get_path_name().split('.')[0]
if parent not in (SOURCE, DEST):
    raise RuntimeError('Drum parent changed outside this revision')
slots = list(mesh.get_editor_property('static_materials'))
expected_slots = ['drum_DrumPolymer', 'drum_DrumFasteners', 'drum_DrumIndex']
if [str(s.material_slot_name) for s in slots] != expected_slots or any(s.material_interface != mi for s in slots):
    raise RuntimeError('Drum slot ownership changed')

# The existing instance remains the runtime/weather/reimport binding. Only its
# private parent changes, so no reference or wet-table migration is needed.
file = P / 'Content' / (INSTANCE.removeprefix('/Game/') + '.uasset')
backup = O / 'Before' / file.name
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(file, backup)
receipt['backup'] = {'file': str(backup), 'sha256': hashlib.sha256(backup.read_bytes()).hexdigest()}
record()
if E.does_asset_exist(DEST):
    material = u.load_asset(DEST)
    if E.get_metadata_tag(material, 'WeaponSurfaceGraph') != VERSION:
        raise RuntimeError('Destination belongs to another revision')
else:
    material = E.duplicate_asset(SOURCE, DEST)
    if not material:
        raise RuntimeError('Could not duplicate drum adapter')
    E.set_metadata_tag(material, 'WeaponSurfaceGraph', VERSION)
    nodes = list(L.get_material_expressions(material))
    samples = {n.get_editor_property('texture').get_name(): n for n in nodes
        if isinstance(n, u.MaterialExpressionTextureSample) and n.get_editor_property('texture')}
    colour_source = samples['T_AKM_Drum_BaseColor']
    mr = samples['T_AKM_Drum_MetalRough']
    wet_colour = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
        and n.get_editor_property('code').strip() == 'return Base*(1-Data.a*.055);')
    wet_rough = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
        and n.get_editor_property('code').strip() == 'return lerp(lerp(Base,max(.12,Base*.62),Data.a),.065,Data.b*.85);')
    controls = {name: node(material, u.MaterialExpressionScalarParameter,
        parameter_name=name, default_value=value, group='AKM Drum Shell') for name, value in params.items()}
    tint_node = node(material, u.MaterialExpressionVectorParameter, parameter_name='Drum_ShellTint',
        default_value=u.LinearColor(*tint, 1.), group='AKM Drum Shell')
    colour = custom(material, 'AKM drum graphite shell colour', 'PolymerColor.hlsl',
        {'Base': (colour_source, 'RGB'), 'Metal': (mr, 'B'), 'Tint': tint_node,
         'Strength': controls['Drum_ShellStrength']}, 3)
    rough = custom(material, 'AKM drum satin shell roughness', 'PolymerRoughness.hlsl',
        {'Base': (mr, 'G'), 'Colour': (colour_source, 'RGB'), 'Metal': (mr, 'B'),
         'Center': controls['Drum_ShellRoughness'], 'SourceWeight': controls['Drum_ShellSourceRoughness'],
         'Strength': controls['Drum_ShellStrength']}, 1)
    # Finish the dry shell before its existing single wet layer. The R02 metal
    # branch, atlas, normal map, metallic identity and geometry are untouched.
    wire(colour, wet_colour, 'Base')
    wire(rough, wet_rough, 'Base')
    E.set_metadata_tag(material, 'WeaponSurfacePreserved', 'R02 steel; own UV0 atlas/normal; black gasket; metallic identity; single wet layer')
    errors = L.recompile_material(material)
    if errors:
        raise RuntimeError('Drum material compile failed: ' + str(errors))
    save(material)
if prepare_only:
    receipt.update({'parent': material.get_path_name(), 'prepared': True,
        'scalars': params, 'tint_linear': tint})
    record()
    print('WEAPON_SURFACE_AKM_DRUM03_PREPARED new private parent saved; existing runtime instance unchanged', flush=True)
else:
    L.set_material_instance_parent(mi, material)
    for name, value in params.items():
        L.set_material_instance_scalar_parameter_value(mi, name, value)
    L.set_material_instance_vector_parameter_value(mi, 'Drum_ShellTint', u.LinearColor(*tint, 1.))
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', VERSION)
    save(mi)
    receipt.update({'parent': material.get_path_name(), 'instance': mi.get_path_name(),
        'slots': [{'name': str(s.material_slot_name), 'material': s.material_interface.get_path_name()} for s in mesh.get_editor_property('static_materials')],
        'scalars': params, 'tint_linear': tint, 'complete': True})
    record()
    manifest_path = O.parent / 'current_surface_bindings.json'
    manifest = json.loads(manifest_path.read_text())
    manifest.setdefault('component_revisions', {})['AKM.large_drum'] = {
        'version': VERSION, 'instance': mi.get_path_name(), 'parent': material.get_path_name(),
        'recipe': str(O / 'apply_finish.py')}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('WEAPON_SURFACE_AKM_DRUM03_SAVED private parent and existing instance; 3 existing slots retained; geometry_changed=False; tested=False', flush=True)
