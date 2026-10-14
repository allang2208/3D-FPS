"""Save the original rounded-card selection flame material; no preview or game launch."""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/Dealer20261004/SelectionV5/Materials'
NAME = 'M_DealerSelectedFlame'
TARGET = DEST + '/' + NAME
E = u.EditorAssetLibrary
L = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()
receipt = {'version': 5, 'complete': False, 'saved_assets': [], 'runtime_tested': False, 'rendered': False}


def record():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
         if p.get_name() == TARGET]
if dirty:
    raise RuntimeError('Preserve unsaved Dealer selection target: ' + ', '.join(dirty))
record()
mat = u.load_asset(TARGET)
if mat and E.get_metadata_tag(mat, 'DealerSelectionRevision') != '5':
    raise RuntimeError('Preserve unowned material ' + TARGET)
if not mat:
    mat = A.create_asset(NAME, DEST, u.Material, u.MaterialFactoryNew())
if not mat:
    raise RuntimeError('Cannot create ' + TARGET)
for expression in list(L.get_material_expressions(mat)):
    L.delete_material_expression(mat, expression)
for key, value in {'blend_mode': u.BlendMode.BLEND_TRANSLUCENT,
                   'shading_model': u.MaterialShadingModel.MSM_UNLIT, 'two_sided': True,
                   'disable_depth_test': True, 'translucency_pass': u.MaterialTranslucencyPass.MTP_AFTER_DOF,
                   'enable_responsive_aa': True}.items():
    mat.set_editor_property(key, value)
count = 0


def node(cls, **props):
    global count
    n = L.create_material_expression(mat, cls, -1600 + (count % 7) * 240, (count // 7) * 250)
    count += 1
    for key, value in props.items():
        n.set_editor_property(key, value)
    return n


def wire(a, b, pin=0):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(b)[pin])
    if not L.connect_material_expressions(a, '', b, pin):
        raise RuntimeError('Cannot connect selection material ' + str(pin))


inputs = {'UV': node(u.MaterialExpressionTextureCoordinate),
          'Reveal': node(u.MaterialExpressionScalarParameter, parameter_name='Reveal', default_value=0.0),
          'Age': node(u.MaterialExpressionScalarParameter, parameter_name='Age', default_value=0.0),
          'Seed': node(u.MaterialExpressionScalarParameter, parameter_name='Seed', default_value=0.0)}
custom = node(u.MaterialExpressionCustom, code=(ROOT / 'SelectedFlame.hlsl').read_text(encoding='utf-8'),
              output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
pins = []
for key in inputs:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', key)
    pins.append(pin)
custom.set_editor_property('inputs', pins)
for key, expression in inputs.items():
    wire(expression, custom, key)
color = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
wire(custom, color)
wire(custom, alpha)
exposure = node(u.MaterialExpressionEyeAdaptationInverse)
wire(color, exposure, 0)
wire(node(u.MaterialExpressionConstant, r=1.0), exposure, 1)
if not L.connect_material_property(exposure, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Cannot connect selection emissive')
if not L.connect_material_property(alpha, '', u.MaterialProperty.MP_OPACITY):
    raise RuntimeError('Cannot connect selection opacity')
errors = L.recompile_material(mat)
if errors:
    raise RuntimeError('Dealer selection material compile failed: ' + str(errors))
E.set_metadata_tag(mat, 'DealerSelectionRevision', '5')
if not E.save_loaded_asset(mat, False):
    raise RuntimeError('Cannot save ' + TARGET)
receipt['saved_assets'].append(mat.get_path_name())
receipt['complete'] = True
receipt['geometry_reused'] = '/Game/Weapons/Dealer20261004/Meshes/SM_DealerResult'
record()
print('DEALER_SELECTION_V5_SAVED material=1 tested=false rendered=false')
