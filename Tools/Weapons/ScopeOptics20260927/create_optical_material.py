"""Author/save only the new peripheral lens material; no PIE, render or tests."""
import json
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT / 'Tools/Weapons/ScopeOptics20260927'
RECEIPTS = PROJECT / 'Saved/ScopeOptics20260927'
DEST = '/Game/Weapons/ScopeOptics20260927'
NAME = 'M_ScopePeripheralOptics'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Unexpected project')

L = u.MaterialEditingLibrary
path = DEST + '/' + NAME
mat = u.find_object(None, path + '.' + NAME) or u.load_object(None, path + '.' + NAME)
if mat is None:
    mat = u.AssetToolsHelpers.get_asset_tools().create_asset(NAME, DEST, u.Material, u.MaterialFactoryNew())
if mat is None:
    raise RuntimeError('Material creation failed')
L.delete_all_material_expressions(mat)
mat.set_editor_property('material_domain', u.MaterialDomain.MD_POST_PROCESS)
mat.set_editor_property('blendable_location', u.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
mat.set_editor_property('blendable_priority', 5)

scene = L.create_material_expression(mat, u.MaterialExpressionSceneTexture, -650, -220)
scene.set_editor_property('scene_texture_id', u.SceneTextureId.PPI_POST_PROCESS_INPUT0)
scene.set_editor_property('filtered', True)
sources = {'SceneColor': scene}
for index, (name, value) in enumerate([('ScopeAlpha', 0.0), ('ScopePSO', 0.0), ('ScopeZoom', 1.0), ('Strength', 0.65)]):
    node = L.create_material_expression(mat, u.MaterialExpressionScalarParameter, -650, index * 100)
    node.set_editor_property('parameter_name', name)
    node.set_editor_property('default_value', value)
    sources[name] = node
eye = L.create_material_expression(mat, u.MaterialExpressionVectorParameter, -650, 430)
eye.set_editor_property('parameter_name', 'EyeOffset')
eye.set_editor_property('default_value', u.LinearColor(0, 0, 0, 0))
sources['EyeOffset'] = eye

effect = L.create_material_expression(mat, u.MaterialExpressionCustom, -160, 0)
effect.set_editor_property('code', (ROOT / 'peripheral_optics.hlsl').read_text(encoding='utf-8'))
effect.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT3)
inputs = []
for name in sources:
    pin = u.CustomInput()
    pin.set_editor_property('input_name', name)
    inputs.append(pin)
effect.set_editor_property('inputs', inputs)
for name, node in sources.items():
    if not L.connect_material_expressions(node, 'Color' if name == 'SceneColor' else '', effect, name):
        raise RuntimeError('Material connection failed: ' + name)
if not L.connect_material_property(effect, '', u.MaterialProperty.MP_EMISSIVE_COLOR):
    raise RuntimeError('Material emissive connection failed')
L.recompile_material(mat)
saved = u.EditorLoadingAndSavingUtils.save_packages([mat.get_outermost()], False)
if not saved:
    raise RuntimeError('Material package did not save')
RECEIPTS.mkdir(parents=True, exist_ok=True)
receipt = {'asset': path, 'saved': bool(saved), 'material_recompile_requested': True,
           'game_tested': False, 'rendered': False, 'scene_capture_added': False}
(RECEIPTS / 'material-save.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('SCOPE_OPTICS_MATERIAL_SAVED ' + json.dumps(receipt, ensure_ascii=False))
