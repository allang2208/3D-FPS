"""Revise existing AKM finish graphs and parameters; no mesh or weather rebinding."""
import json
import shutil
from pathlib import Path
import unreal as u

O = Path(__file__).parent
P = Path(u.Paths.project_dir()).resolve()
if P != Path('D:/FPS3D/FPSGAME').resolve():
    raise RuntimeError('Wrong project')
R = json.loads((O / 'recipe.json').read_text())
E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
RP = O / 'apply_receipt.json'
receipt = json.loads(RP.read_text()) if RP.exists() else {
    'version': R['version'], 'graphs': {}, 'instances': {}, 'overrides': {},
    'backups': {}, 'complete': False, 'geometry_changed': False, 'tested': False}
commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
dirty = set()
if not commandlet:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE active; stop preview before AKM R02 save')
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}


def record():
    RP.write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def load(path):
    obj = u.load_asset(path)
    if not obj:
        raise RuntimeError('Missing current AKM asset ' + path)
    return obj


def backup(path):
    if path in receipt['backups']:
        return
    rel = path.split('.')[0].removeprefix('/Game/') + '.uasset'
    target = O / 'Before' / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(P / 'Content' / rel, target)
    receipt['backups'][path] = str(target)
    record()


def save(obj):
    if not E.save_loaded_asset(obj, False):
        raise RuntimeError('Asset save failed ' + obj.get_path_name())


def find_finish(m):
    nodes = L.get_material_expressions(m)
    color = next((n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
        and str(n.get_editor_property('description')) == 'AKM R01 authored colour and wear retained'), None)
    rough = next((n for n in nodes if isinstance(n, u.MaterialExpressionCustom)
        and str(n.get_editor_property('description')) == 'AKM R01 source roughness detail retained'), None)
    if not color or not rough:
        raise RuntimeError('Missing R01 finish nodes ' + m.get_path_name())
    return nodes, color, rough


# Necessary write preconditions only: preserve unsaved work and ensure the
# selected objects are still this revision's private adapters/instances.
graphs = {row['path']: load(row['path']) for row in R['masters'].values()}
for t in R['targets'].values():
    if t['direct_override']:
        graphs[t['path']] = load(t['path'])
assets = {t['path']: load(t['path']) for t in R['targets'].values()}
for path, obj in {**graphs, **assets}.items():
    if path.split('.')[0] in dirty:
        raise RuntimeError('Unsaved AKM material ' + path)
for path, graph in graphs.items():
    if E.get_metadata_tag(graph, 'WeaponSurfaceGraph') not in (R['previous_version'], R['version']):
        raise RuntimeError('Changed graph ownership ' + path)
    find_finish(graph)
for t in R['targets'].values():
    if not t['direct_override']:
        mi = assets[t['path']]
        if mi.get_editor_property('parent').get_path_name() != t['parent']:
            raise RuntimeError('Changed AKM parent ' + t['path'])

for path, graph in graphs.items():
    if path in receipt['graphs']:
        continue
    backup(path)
    nodes, color, rough = find_finish(graph)
    contrast = next((n for n in nodes if isinstance(n, u.MaterialExpressionScalarParameter)
        and str(n.get_editor_property('parameter_name')) == 'R02_SourceColorContrast'), None)
    if not contrast:
        contrast = L.create_material_expression(graph, u.MaterialExpressionScalarParameter)
        contrast.set_editor_property('parameter_name', 'R02_SourceColorContrast')
        contrast.set_editor_property('default_value', .58)
        contrast.set_editor_property('group', 'AKM Authored Finish')
    inputs = list(color.get_editor_property('inputs'))
    if not any(str(p.get_editor_property('input_name')) == 'SourceContrast' for p in inputs):
        pin = u.CustomInput()
        pin.set_editor_property('input_name', 'SourceContrast')
        inputs.append(pin)
        color.set_editor_property('inputs', inputs)
    if not L.connect_material_expressions(contrast, '', color, 'SourceContrast'):
        raise RuntimeError('Cannot connect AKM source contrast')
    color.set_editor_property('code', (O / 'FinishColor.hlsl').read_text())
    rough.set_editor_property('code', (O / 'FinishRoughness.hlsl').read_text())
    # Direct runtime materials use defaults. MI overrides are set separately.
    direct = next((t for t in R['targets'].values() if t['direct_override'] and t['path'] == path), None)
    defaults = direct or next(t for t in R['targets'].values() if t['parent'] == path)
    for n in L.get_material_expressions(graph):
        if isinstance(n, u.MaterialExpressionScalarParameter):
            name = str(n.get_editor_property('parameter_name'))
            if name in defaults['scalars']:
                n.set_editor_property('default_value', defaults['scalars'][name])
        elif isinstance(n, u.MaterialExpressionVectorParameter):
            name = str(n.get_editor_property('parameter_name'))
            if name in defaults['vectors']:
                n.set_editor_property('default_value', u.LinearColor(*defaults['vectors'][name], 1.))
    E.set_metadata_tag(graph, 'WeaponSurfaceGraph', R['version'])
    errors = L.recompile_material(graph)
    if errors:
        raise RuntimeError('Material compilation failed ' + path + ': ' + str(errors))
    save(graph)
    receipt['graphs'][path] = {'saved': True}
    if direct:
        receipt['overrides'][path] = {'saved': True, 'role': direct['role']}
    record()
    if len(receipt['graphs']) % 10 == 0:
        print('WEAPON_SURFACE_AKM_R02_GRAPHS', len(receipt['graphs']), flush=True)

for t in R['targets'].values():
    path = t['path']
    if t['direct_override'] or path in receipt['instances']:
        continue
    mi = assets[path]
    backup(path)
    for name, value in t['scalars'].items():
        L.set_material_instance_scalar_parameter_value(mi, name, value)
    for name, value in t['vectors'].items():
        L.set_material_instance_vector_parameter_value(mi, name, u.LinearColor(*value, 1.))
    L.update_material_instance(mi)
    E.set_metadata_tag(mi, 'WeaponSurfaceRevision', R['version'])
    save(mi)
    receipt['instances'][path] = {'saved': True, 'role': t['role']}
    record()

receipt['complete'] = True
record()
current = {'version': R['version'], 'recipe': str(O / 'recipe.json'),
    'meshes': R['bindings'], 'runtime_override_materials': list(receipt['overrides']),
    'geometry_changed': False, 'tested': False}
(O.parent / 'current_surface_bindings.json').write_text(json.dumps(current, indent=2), encoding='utf-8')
print('WEAPON_SURFACE_AKM_R02_SAVED', len(receipt['graphs']), 'graphs including',
    len(receipt['overrides']), 'runtime overrides;', len(receipt['instances']),
    'instances; same meshes and weather mappings; tested=False', flush=True)
