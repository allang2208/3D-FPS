"""Read the current six melee definitions and their live asset material slots."""
import hashlib
import json
from pathlib import Path
import unreal as u

P = Path(u.Paths.project_dir()).resolve()
O = Path(__file__).parent
L = u.MaterialEditingLibrary
IDS = ['ue_rune_sword', 'ue_frost_crystal_sword', 'ue_highland_claymore',
       'ue_apprentice_staff', 'tool_axe', 'tool_pickaxe']
R = {'definitions': IDS, 'meshes': {}, 'materials': {}, 'masters': {},
     'missing': [], 'ignored_arms': [], 'existing_mapping': {}}

def load_json(name):
    return json.loads((P / 'Content/ColdSteelData' / name).read_text(encoding='utf-8-sig'))

paths = {}
def collect(value, origin, key=''):
    if isinstance(value, dict):
        for k, v in value.items():
            collect(v, origin + '/' + k, k)
    elif isinstance(value, list):
        for i, v in enumerate(value):
            collect(v, origin + '/' + str(i), key)
    elif isinstance(value, str) and value.startswith('/Game/'):
        if 'arms' in key.lower() or 'hands' in key.lower():
            R['ignored_arms'].append(value)
            return
        name = value.split('.')[0].rsplit('/', 1)[-1]
        if name.startswith(('SM_', 'SK_', 'M_', 'MI_')):
            paths.setdefault(value, []).append(origin)

for f in ['rune-sword-modules.json', 'frost-sword-modules.json',
          'highland-claymore-modules.json', 'shared-sword-pommels.json',
          'staff-gunsmith.json', 'tool-gunsmith.json', 'tool-enhance.json']:
    collect(load_json(f), f)
for f, ids in [('items.json', IDS[:3]), ('staffs.json', [IDS[3]]),
               ('production_tools.json', IDS[4:])]:
    data = load_json(f)
    for key in ids:
        collect(data[key], f + '/' + key)

def disk(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')

def sources(m, prop):
    node = L.get_material_property_input_node(m, prop)
    return None if node is None else {'name': node.get_name(), 'class': node.get_class().get_name(),
        'output': str(L.get_material_property_input_node_output_name(m, prop))}

def add_material(mat, usage):
    path = mat.get_path_name()
    if path in R['materials']:
        R['materials'][path]['usage'].append(usage)
        return
    chain = []
    base = mat
    while isinstance(base, u.MaterialInstance):
        chain.append(base.get_path_name())
        base = base.get_editor_property('parent')
    R['materials'][path] = {'base': base.get_path_name(), 'chain': chain,
        'usage': [usage], 'scalar_names': [str(x) for x in L.get_scalar_parameter_names(mat)]}
    bpath = base.get_path_name()
    if bpath in R['masters']:
        return
    nodes = L.get_material_expressions(base)
    graph = []
    for n in nodes:
        cls = n.get_class().get_name()
        if any(x in cls for x in ['Substrate', 'MaterialAttributes', 'Custom', 'ScalarParameter']):
            entry = {'class': cls, 'name': n.get_name()}
            if isinstance(n, u.MaterialExpressionCustom):
                entry.update(description=str(n.get_editor_property('description')),
                    code=str(n.get_editor_property('code')),
                    pins=[str(p.get_editor_property('input_name')) for p in n.get_editor_property('inputs')])
            if isinstance(n, u.MaterialExpressionScalarParameter):
                entry.update(parameter=str(n.get_editor_property('parameter_name')),
                    default=n.get_editor_property('default_value'))
            entry['inputs'] = [x.get_name() if x else None for x in L.get_inputs_for_material_expression(base, n)]
            graph.append(entry)
    R['masters'][bpath] = {'domain': str(base.get_editor_property('material_domain')),
        'blend': str(base.get_editor_property('blend_mode')),
        'shading': str(base.get_editor_property('shading_model')),
        'tangent_space_normal': base.get_editor_property('tangent_space_normal'),
        'attributes': base.get_editor_property('use_material_attributes'),
        'sha256': hashlib.sha256(disk(bpath).read_bytes()).hexdigest(),
        'outputs': {p: sources(base, getattr(u.MaterialProperty, 'MP_' + p)) for p in
                    ['BASE_COLOR', 'METALLIC', 'ROUGHNESS', 'NORMAL', 'MATERIAL_ATTRIBUTES', 'FRONT_MATERIAL']},
        'graph': graph}

for path, origins in sorted(paths.items()):
    obj = u.load_asset(path)
    if obj is None:
        R['missing'].append({'path': path, 'origins': origins})
        continue
    if isinstance(obj, (u.StaticMesh, u.SkeletalMesh)):
        slots = obj.get_editor_property('static_materials' if isinstance(obj, u.StaticMesh) else 'materials')
        entry = {'class': obj.get_class().get_name(), 'origins': origins, 'slots': []}
        for i, slot in enumerate(slots):
            mat = slot.get_editor_property('material_interface')
            name = str(slot.get_editor_property('material_slot_name'))
            entry['slots'].append({'index': i, 'slot': name, 'material': mat.get_path_name() if mat else None})
            if mat:
                add_material(mat, {'mesh': obj.get_path_name(), 'slot': name, 'index': i})
        R['meshes'][obj.get_path_name()] = entry
    elif isinstance(obj, u.MaterialInterface):
        add_material(obj, {'override': origins})

# Golden native runes replace the physical Azure blade/guard surface itself.
native_gold = '/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/MI_AzureRunesword_NativeGold'
add_material(u.load_asset(native_gold), {'runtime_surface': 'MeleeRuneVisual native golden blade and guard'})

# Whirlwind temporarily substitutes physical surface copies to keep temporal
# responsiveness. Include only the entries whose source is a current weapon.
for source, target in load_json('whirlwind-temporal-materials.json').items():
    if source in R['materials'] and not source.startswith('/Game/Characters/'):
        add_material(u.load_asset(target), {'temporal_surface_for': source})

reg = u.AssetRegistryHelpers.get_asset_registry()
for item in reg.get_assets_by_class(u.TopLevelAssetPath('/Script/FPSGAME', 'WeatherPresentationAssets'), True):
    obj = item.get_asset()
    for k, v in obj.get_editor_property('wet_materials').items():
        if str(k) in R['materials']:
            R['existing_mapping'].setdefault(str(k), []).append(v.get_path_name())

(O / 'audit.json').write_text(json.dumps(R, indent=2, ensure_ascii=False), encoding='utf-8')
u.log('CLOVEN_MELEE_AUDIT meshes=%d materials=%d masters=%d missing=%d' %
      (len(R['meshes']), len(R['materials']), len(R['masters']), len(R['missing'])))
