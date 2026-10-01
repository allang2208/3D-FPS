"""Refine only the two factory-magazine instances; retain current mesh and wet mapping.

New private graph topology, backed-up instances, no mesh write/FBX/rebake/test.
Run through WeaponSurface20260930/run_ue.ps1 or as the final SVD authoring stage.
"""
import json
import shutil
from pathlib import Path
import unreal as u

HERE = Path(__file__).parent
L, E = u.MaterialEditingLibrary, u.EditorAssetLibrary
recipe = json.loads((HERE / 'recipe.json').read_text())
MASTER = recipe['master']
VERSION = recipe['version']
PROJECT = Path(u.Paths.project_dir()).resolve()
if PROJECT != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project; no changes')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():
        raise RuntimeError('PIE active; preserve the current session')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    targets = {MASTER, recipe['mesh']} | {s['material'] for s in recipe['slots'].values()}
    if dirty & targets:
        raise RuntimeError('Target has unsaved edits: ' + str(dirty & targets))

def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing asset ' + path)
    return asset

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed ' + asset.get_path_name())

def node(m, cls, **props):
    n = L.create_material_expression(m, cls)
    for k, v in props.items():
        n.set_editor_property(k, v)
    return n

def wire(src, dst, pin):
    n, output = src if isinstance(src, tuple) else (src, '')
    if not L.connect_material_expressions(n, output, dst, pin):
        raise RuntimeError('Cannot connect ' + pin)

def custom(m, label, code, inputs, size):
    n = node(m, u.MaterialExpressionCustom, code=code, description=label,
             output_type=getattr(u.CustomMaterialOutputType, 'CMOT_FLOAT' + str(size)))
    pins = []
    for name in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', name)
        pins.append(pin)
    n.set_editor_property('inputs', pins)
    for name, value in inputs.items():
        wire(value, n, name)
    return n

mesh = load(recipe['mesh'])
slots = {str(s.material_slot_name): s.material_interface for s in mesh.get_editor_property('materials')}
instances = {}
for name, spec in recipe['slots'].items():
    expected = load(spec['material'])
    if slots.get(name) != expected:
        raise RuntimeError('Factory magazine binding changed; preserve current asset: ' + name)
    instances[name] = expected

# Existing self mappings continue to point to exactly the same material instances.
weather_path = '/Game/Weapons/SVDDragunov20260922/Accessories20260923/DA_SVD_AttachmentWetMaterials'
weather = dict(load(weather_path).get_editor_property('wet_materials'))
for mi in instances.values():
    if weather.get(mi.get_path_name()) != mi:
        raise RuntimeError('Current magazine wet mapping differs; preserve it')

rp = HERE / 'apply_receipt.json'
receipt = {'version': VERSION, 'master': MASTER, 'instances': {}, 'complete': False,
           'tested': False, 'mesh_changed': False, 'wet_table_changed': False}
def record():
    rp.write_text(json.dumps(receipt, indent=1, ensure_ascii=False), encoding='utf-8')

for name, mi in instances.items():
    package = mi.get_path_name().split('.')[0]
    rel = package.removeprefix('/Game/') + '.uasset'
    target = HERE / 'Before' / rel
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(PROJECT / 'Content' / rel, target)
    receipt['instances'][name] = {'path': mi.get_path_name(), 'backup': str(target),
                                'parent_before': mi.get_editor_property('parent').get_path_name(), 'saved': False}
record()

if E.does_asset_exist(MASTER):
    mat = load(MASTER)
    if E.get_metadata_tag(mat, 'WeaponSurfaceGraph') != VERSION:
        raise RuntimeError('Private graph belongs to another revision; preserve it')
else:
    original = instances['SM_SVD_Magazine_001'].get_base_material()
    if E.get_metadata_tag(original, 'WeaponSurfaceGraph') != 'WS1-SVD-Source-g1':
        raise RuntimeError('Factory magazine no longer uses the captured WS1 source graph')
    mat = E.duplicate_asset(original.get_path_name(), MASTER)
    if not mat:
        raise RuntimeError('Cannot create factory-magazine graph')
    expressions = list(L.get_material_expressions(mat))
    codes = {str(n.get_editor_property('description')): n for n in expressions if isinstance(n, u.MaterialExpressionCustom)}
    wet_normal = codes['WS_WetNormal']
    pins = [str(p.get_editor_property('input_name')) for p in wet_normal.get_editor_property('inputs')]
    old_normal = L.get_inputs_for_material_expression(mat, wet_normal)[pins.index('Base')]
    old_pin = L.get_input_node_output_name_for_material_expression(wet_normal, old_normal)
    ao_prop = u.MaterialProperty.MP_AMBIENT_OCCLUSION
    old_ao = L.get_material_property_input_node(mat, ao_prop)
    ao_pin = L.get_material_property_input_node_output_name(mat, ao_prop)
    uv = node(mat, u.MaterialExpressionTextureCoordinate, coordinate_index=0)
    def scalar(name):
        return node(mat, u.MaterialExpressionScalarParameter, parameter_name=name,
                    default_value=recipe['scalars'][name], group='Factory Magazine')
    relief = custom(mat, 'SVD factory magazine shallow longitudinal pressing',
                    (HERE / 'PanelNormal.hlsl').read_text(),
                    {'N': (old_normal, str(old_pin)), 'UV': uv,
                     'HeightMM': scalar('MagazineRibHeightMM'), 'RadiusMM': scalar('MagazineRibRadiusMM'),
                     'UVToMM': scalar('MagazineUVToMM')}, 4)
    normal = node(mat, u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    wire(relief, normal, '')
    wire(normal, wet_normal, 'Base')
    # Lift only the old embossed-panel AO; retain mouth, interior, seam and floorplate AO.
    ao = custom(mat, 'SVD factory magazine remove old crosshatch shadow',
                'return lerp(Source,max(Source,.94),Panel.a);',
                {'Source': (old_ao, ao_pin), 'Panel': relief}, 1)
    if not L.connect_material_property(ao, '', ao_prop):
        raise RuntimeError('Cannot connect magazine AO')
    mat.set_editor_property('used_with_skeletal_mesh', True)
    mat.set_editor_property('used_with_morph_targets', False)
    mat.set_editor_property('used_with_clothing', False)
    mat.set_editor_property('automatically_set_usage_in_editor', False)
    E.set_metadata_tag(mat, 'WeaponSurfaceGraph', VERSION)
    E.set_metadata_tag(mat, 'WeaponSurfaceSourceGraph', original.get_path_name())
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Magazine material compilation failed: ' + str(errors))
    save(mat)

for name, mi in instances.items():
    L.set_material_instance_parent(mi, mat)
    values = dict(recipe['scalars'], WS_Roughness=recipe['slots'][name]['roughness'])
    for param, value in values.items():
        L.set_material_instance_scalar_parameter_value(mi, param, float(value))
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', VERSION)
    save(mi)
    receipt['instances'][name].update(parent_after=MASTER, scalars=values, saved=True,
                                     wet_replacement=mi.get_path_name())
    record()
receipt['complete'] = True
receipt['source_normal'] = 'Existing full normal outside the factory sideplate relief region'
record()
print('SVD_FACTORY_MAGAZINE_SATIN02_SAVED', len(instances), flush=True)
