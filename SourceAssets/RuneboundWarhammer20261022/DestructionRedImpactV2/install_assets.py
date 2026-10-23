"""Save two new red materials without overwriting the prior blue-violet assets."""
import json
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
ROOT = P.parents[2]
D = '/Game/Weapons/RuneboundWarhammer20261022/DestructionRedImpactV2'
DONOR = '/Game/Weapons/RuneboundWarhammer20261022/DestructionManaRuneV1'
TAG, OWNER = 'RuneboundRedImpactOwner', 'RuneboundDestructionRedImpact20261023'
E, L, A = u.EditorAssetLibrary, u.MaterialEditingLibrary, u.AssetToolsHelpers.get_asset_tools()
receipt = {'complete': False, 'assets': [], 'tested': False, 'game_started': False}

def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')

def own_material(name):
    path = D+'/'+name
    if any(str(pkg.get_name()) == path for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve dirty target '+path)
    mat = u.load_asset(path) if E.does_asset_exist(path) else None
    if mat and E.get_metadata_tag(mat, TAG) != OWNER:
        raise RuntimeError('Preserve unowned target '+path)
    if not mat:
        source = u.load_asset(DONOR+'/'+name)
        if not source:
            raise RuntimeError('Missing material donor '+name)
        mat = A.duplicate_asset(name, D, source)
        if not mat:
            raise RuntimeError('Could not duplicate '+name)
        E.set_metadata_tag(mat, TAG, OWNER)
    return mat

def node(mat, cls, **props):
    result = L.create_material_expression(mat, cls)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result

def wire(source, output, target, pin):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Could not connect '+str(pin))

def save(mat):
    L.layout_material_expressions(mat)
    if L.recompile_material(mat):
        raise RuntimeError('Material compile failed '+mat.get_path_name())
    E.set_metadata_tag(mat, TAG, OWNER)
    if not E.save_loaded_asset(mat, False):
        raise RuntimeError('Material save failed '+mat.get_path_name())
    receipt['assets'].append(mat.get_path_name())
    record()

project_dir = Path(u.Paths.project_dir()).resolve()
if project_dir not in (ROOT, P/'AuthorHost'):
    raise RuntimeError('Wrong authoring project')
receipt['author_project'] = str(project_dir)
record()
mat = own_material('M_RuneboundDestructionRuneSurface')
expressions = list(L.get_material_expressions(mat))
custom = next(n for n in expressions if isinstance(n, u.MaterialExpressionCustom))
custom.set_editor_property('code', (P/'DestructionRune.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description', 'Crimson native rune waves, red fracture and synchronized impact pulse')
impact = next((n for n in expressions if isinstance(n, u.MaterialExpressionScalarParameter)
               and str(n.get_editor_property('parameter_name')) == 'RuneImpact'), None)
if not impact:
    impact = node(mat, u.MaterialExpressionScalarParameter, parameter_name='RuneImpact', default_value=0.)
pins = list(custom.get_editor_property('inputs'))
if not any(str(pin.get_editor_property('input_name')) == 'RuneImpact' for pin in pins):
    pin = u.CustomInput(); pin.set_editor_property('input_name', 'RuneImpact')
    pins.append(pin); custom.set_editor_property('inputs', pins)
wire(impact, '', custom, 'RuneImpact')

# Recolour only the actual native ink, retaining the surrounding PBR surface.
if not any(str(n.get_editor_property('desc')) == 'RuneboundRedInkV2' for n in expressions):
    surface = next(n for n in expressions if isinstance(n, u.MaterialExpressionSubstrateShadingModels))
    input_names = [str(n) for n in L.get_material_expression_input_names(surface)]
    base_index = next(i for i, name in enumerate(input_names) if name.replace(' ', '').lower() == 'basecolor')
    base = L.get_inputs_for_material_expression(mat, surface)[base_index]
    if not base:
        raise RuntimeError('Native base colour input missing')
    output = L.get_input_node_output_name_for_material_expression(surface, base)
    mask = u.load_asset('/Game/Weapons/RuneboundWarhammer20261022/PassiveV1/T_RuneboundNativeRuneMask')
    mask_sample = node(mat, u.MaterialExpressionTextureSample, texture=mask, sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    red = node(mat, u.MaterialExpressionConstant3Vector, constant=u.LinearColor(.22, .003, .0015, 1.))
    tint = node(mat, u.MaterialExpressionLinearInterpolate, desc='RuneboundRedInkV2')
    wire(base, output or '', tint, 'A'); wire(red, '', tint, 'B'); wire(mask_sample, 'R', tint, 'Alpha')
    wire(tint, '', surface, input_names[base_index])
    if not L.connect_material_property(tint, '', u.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('Could not connect legacy base colour')
mat.set_editor_property('used_with_skeletal_mesh', False)
mat.set_editor_property('used_with_nanite', True)
save(mat)

mote = own_material('M_RuneboundDestructionMote')
custom = next(n for n in L.get_material_expressions(mote) if isinstance(n, u.MaterialExpressionCustom))
custom.set_editor_property('code', (P/'DestructionMote.hlsl').read_text(encoding='utf-8'))
custom.set_editor_property('description', 'Red ember shards and directional spray with a warm red core')
save(mote)
receipt['complete'] = True
receipt['icon'] = 'Existing standard gray-white icon retained'
record()
print('RUNEBOUND_RED_IMPACT_SAVED '+json.dumps(receipt))
