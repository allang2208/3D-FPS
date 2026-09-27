"""Save scope-aware copies of the accepted laser materials; no game or tests."""
import json
import shutil
from pathlib import Path
import unreal as u

PROJECT = Path('D:/FPS3D/FPSGAME')
DEST = '/Game/Weapons/ScopeOptics20260927'
SOURCE = '/Game/Weapons/TacticalDevices20260913/Effects'
if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Unexpected project')

L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
VERSION = 'scope-laser-v1'
TEMPORAL_VERSION = 'laser-temporal-v1'
packages = []
assets = []

def connect(source, output, target, pin):
    if not L.connect_material_expressions(source, output, target, pin):
        raise RuntimeError('Material connection failed: ' + pin)

def attenuate(mat, alpha, prop, scoped_gain):
    original = L.get_material_property_input_node(mat, prop)
    output = L.get_material_property_input_node_output_name(mat, prop)
    if original is None:
        raise RuntimeError('Missing original material input: ' + str(prop))
    gain = L.create_material_expression(mat, u.MaterialExpressionLinearInterpolate)
    gain.set_editor_property('const_a', 1.0)
    gain.set_editor_property('const_b', scoped_gain)
    connect(alpha, '', gain, 'Alpha')
    multiply = L.create_material_expression(mat, u.MaterialExpressionMultiply)
    connect(original, output, multiply, 'A')
    connect(gain, '', multiply, 'B')
    if not L.connect_material_property(multiply, '', prop):
        raise RuntimeError('Material property connection failed')

def configure_temporal_response(mat, kind):
    # A projected laser spot can jump between surfaces; a beam also changes
    # length at occluders. Rigid-object velocity alone cannot describe either.
    # Keep depth testing and the pre-lens pass; AfterMotionBlur disables depth
    # testing in UE 5.8 and is therefore unsuitable for a world-space laser.
    if E.get_metadata_tag(mat, 'LaserTemporalVersion') != TEMPORAL_VERSION:
        responsiveness = next((node for node in L.get_material_expressions(mat)
                               if isinstance(node, u.MaterialExpressionTemporalResponsivenessOutput)), None)
        if responsiveness is None:
            responsiveness = L.create_material_expression(mat, u.MaterialExpressionTemporalResponsivenessOutput)
        full_response = L.create_material_expression(mat, u.MaterialExpressionConstant)
        full_response.set_editor_property('r', 1.0)
        full_response.set_editor_property('desc', 'Laser: reject stale temporal history')
        connect(full_response, '', responsiveness, '')
        E.set_metadata_tag(mat, 'LaserTemporalVersion', TEMPORAL_VERSION)
    mat.set_editor_property('disable_depth_test', False)
    if kind == 'Beam':
        mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        mat.set_editor_property('enable_responsive_aa', True)
        # Write the response into the velocity pass, including the faint beam
        # during scope fade. Do not use camera/depth-only velocity for this mesh.
        mat.set_editor_property('output_translucent_velocity', True)
        mat.set_editor_property('is_translucency_velocity_from_depth', False)
        mat.set_editor_property('opacity_mask_clip_value', 0.01)

for kind in ['Dot', 'Beam']:
    name = 'M_ScopeAwareLaser' + kind
    path = DEST + '/' + name
    source_path = SOURCE + '/M_Laser' + kind
    disk = PROJECT / 'Content' / (path.removeprefix('/Game/') + '.uasset')
    before = PROJECT / 'Saved/LaserTemporal20260927/Before' / disk.name
    if disk.exists() and not before.exists():
        before.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(disk, before)
    mat = u.find_object(None, path + '.' + name) or u.load_object(None, path + '.' + name)
    if mat is None:
        mat = E.duplicate_asset(source_path, path)
    if mat is None:
        raise RuntimeError('Could not duplicate laser material: ' + source_path)
    if E.get_metadata_tag(mat, 'ScopeLaserVersion') != VERSION:
        alpha = L.create_material_expression(mat, u.MaterialExpressionScalarParameter)
        alpha.set_editor_property('parameter_name', 'ScopeAlpha')
        alpha.set_editor_property('default_value', 0.0)
        alpha.set_editor_property('use_custom_primitive_data', True)
        alpha.set_editor_property('primitive_data_index', 0)
        attenuate(mat, alpha, u.MaterialProperty.MP_EMISSIVE_COLOR, 0.10 if kind == 'Dot' else 0.12)
        if kind == 'Beam':
            attenuate(mat, alpha, u.MaterialProperty.MP_OPACITY, 0.0)
        # Keep physical occlusion and composite before the peripheral lens pass.
        mat.set_editor_property('disable_depth_test', False)
        if kind == 'Beam':
            mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
        E.set_metadata_tag(mat, 'ScopeLaserVersion', VERSION)
        E.set_metadata_tag(mat, 'ScopeLaserSource', source_path)
    configure_temporal_response(mat, kind)
    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Laser material compilation failed: ' + str(errors))
    L.get_statistics(mat)  # Finish material shader compilation before saving.
    packages.append(mat.get_outermost())
    assets.append(path)

saved = u.EditorLoadingAndSavingUtils.save_packages(packages, False)
if not saved:
    raise RuntimeError('Laser material packages did not save')
receipt = {'assets': assets, 'saved': bool(saved), 'source_assets_modified': False,
           'material_recompile_requested': True, 'temporal_version': TEMPORAL_VERSION,
           'temporal_responsiveness': 1.0, 'beam_depth_and_velocity': True,
           'game_tested': False, 'rendered': False}
out = PROJECT / 'Saved/ScopeOptics20260927'
out.mkdir(parents=True, exist_ok=True)
(out / 'laser-material-save.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
(PROJECT / 'Saved/LaserTemporal20260927/material-save.json').write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('SCOPE_LASER_MATERIALS_SAVED ' + json.dumps(receipt, ensure_ascii=False))
