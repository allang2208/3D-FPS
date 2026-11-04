"""Read the active rune materials and their actual shader inputs; no asset writes."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
DATA = PROJECT / 'Content/ColdSteelData'
L = u.MaterialEditingLibrary
result = {'materials': {}, 'bindings': {}, 'missing': [], 'catalogs': {}}
targets = set()
meshes = set()

def collect(value):
    if isinstance(value, dict):
        for v in value.values(): collect(v)
    elif isinstance(value, list):
        for v in value: collect(v)
    elif isinstance(value, str) and value.startswith('/Game/'):
        name = value.split('/')[-1]
        if name.startswith(('M_', 'MI_')): targets.add(value)
        elif name.startswith(('SM_', 'SK_')): meshes.add(value)

for path in DATA.glob('*-modules.json'):
    collect(json.loads(path.read_text(encoding='utf-8-sig')))
for path in DATA.glob('*gunsmith.json'):
    doc = json.loads(path.read_text(encoding='utf-8-sig'))
    for col in doc.get('columns', []):
        if 'rune' in col['key'] or col['key'] == 'blade_2':
            result['catalogs'][path.name + ':' + col['key']] = col
            collect(col)

for rel in [
    'MeleeRunes20260915/SurfaceV2/M_SilverRuneSurfaceV2',
    'FrostSpiritBurst20260922/M_SilverRuneSurface_FrostSpirit',
    'HighlandClaymore20260922/WildRune/M_SilverRuneSurface_HighlandWild',
    'AzureRunesword20260913/NativeRuneGold20260922/MI_AzureRunesword_NativeGold',
    'AzureRunesword20260913/SilverRune20261030/MI_AzureRunesword_NativeSilver',
    'SteelWarhammer20261014/Runes/ShaftWrapV2/M_SilverRuneSurface_WarhammerShaftV2',
    'RuneboundWarhammer20261022/ModulesV1/Runes/M_SilverRuneSurface_RuneboundWarhammerShaftV1',
    'ThunderGodHammer20261028/ModulesV1/Runes/M_SilverRuneSurface_ThunderGodHammerShaftV1',
    'ThunderGodHammer20261028/ExclusiveRunesV1/M_SilverRuneSurface_ThunderExclusiveV1',
    'ThunderGodHammer20261028/LeiMingRefineV2/M_SilverRuneSurface_LeiMingRefineV2',
    'RuneboundWarhammer20261022/SwiftManaRuneV1/M_RuneboundSwiftRuneSurface',
    'RuneboundWarhammer20261022/DestructionRedImpactV2/M_RuneboundDestructionRuneSurface',
]: targets.add('/Game/Weapons/' + rel)

for path in sorted(meshes):
    obj = u.load_asset(path)
    if not obj: result['missing'].append(path); continue
    slots = obj.get_editor_property('static_materials') if isinstance(obj,u.StaticMesh) else obj.get_editor_property('materials')
    mats = [s.material_interface.get_path_name() for s in slots if s.material_interface]
    result['bindings'][path] = mats
    targets.update(mats)

def relevant(mat):
    return any(x in mat.get_name() for x in ('SilverRuneSurface', 'BladeRuneSurface', 'NativeGold',
        'NativeSilver','StaffRuneCraft', 'RuneboundSwiftRuneSurface','RuneboundDestructionRuneSurface'))

def read_mat(path):
    obj = u.load_asset(path)
    if not obj: result['missing'].append(path); return
    if isinstance(obj,u.MaterialInstanceConstant):
        parent = obj.get_editor_property('parent')
        if parent: read_mat(parent.get_path_name())
        if relevant(obj): result['bindings'][obj.get_path_name()] = [parent.get_path_name()]
        return
    if not isinstance(obj,u.Material) or not relevant(obj) or obj.get_path_name() in result['materials']: return
    row = {'nodes': [], 'outputs': {}}
    for name in ['MP_FRONT_MATERIAL','MP_EMISSIVE_COLOR','MP_OPACITY']:
        n = L.get_material_property_input_node(obj,getattr(u.MaterialProperty,name))
        row['outputs'][name] = n.get_name() if n else None
    for n in L.get_material_expressions(obj):
        info = {'name':n.get_name(),'class':n.get_class().get_name(),
                'input_names':list(L.get_material_expression_input_names(n)),
                'input_nodes':[x.get_name() if x else None for x in L.get_inputs_for_material_expression(obj,n)]}
        if isinstance(n,u.MaterialExpressionCustom): info['code'] = n.get_editor_property('code')
        if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):
            v=n.get_editor_property('default_value')
            info.update(parameter=str(n.get_editor_property('parameter_name')),value=[v.r,v.g,v.b,v.a] if isinstance(v,u.LinearColor) else v)
        row['nodes'].append(info)
    result['materials'][obj.get_path_name()] = row

for path in sorted(targets): read_mat(path)
temporal = json.loads((DATA/'whirlwind-temporal-materials.json').read_text(encoding='utf-8-sig'))
for path in list(result['materials']):
    if path in temporal: read_mat(temporal[path])
result['pie'] = bool(u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor())
result['dirty'] = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(ROOT/'material-state.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print('RUNE_MATERIAL_STATE '+json.dumps({'materials':len(result['materials']),'missing':result['missing'],'pie':result['pie']},ensure_ascii=False))
