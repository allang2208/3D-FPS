"""Read the installed cloud inputs needed for Blizzard authoring; no rendering."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import emitters
paths = [
    '/Game/UnrealNormandy/Materials/M_Master_StormCloud',
    '/Game/UnrealNormandy/Materials/M_Master_Cloud',
    '/Game/UnrealNormandy/MaterialInstances/MI_StormCloud_00A',
    '/Game/UnrealNormandy/VFX/NS_StormClouds_00A',
    '/Game/UnrealNormandy/VFX/NS_StormClouds_Rolling_00A',
    '/Game/UnrealNormandy/Textures/T_Particle_Cloud_00A_Masks',
    '/Game/UnrealNormandy/Textures/T_CloudNoise_00A',
    '/Game/Skills/IceSpike/S_IceImpact',
]
results = []
for path in paths:
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Required installed source is missing: ' + path)
    row = {'path': asset.get_path_name(), 'class': asset.get_class().get_name()}
    if isinstance(asset, u.MaterialInterface):
        lib = u.MaterialEditingLibrary
        row['scalars'] = {str(n): lib.get_material_instance_scalar_parameter_value(asset, n) if isinstance(asset, u.MaterialInstanceConstant) else None for n in lib.get_scalar_parameter_names(asset)}
        row['vectors'] = {str(n): str(lib.get_material_instance_vector_parameter_value(asset, n)) if isinstance(asset, u.MaterialInstanceConstant) else None for n in lib.get_vector_parameter_names(asset)}
        row['textures'] = {str(n): str(lib.get_material_instance_texture_parameter_value(asset, n)) if isinstance(asset, u.MaterialInstanceConstant) else None for n in lib.get_texture_parameter_names(asset)}
        if isinstance(asset, u.Material):
            row['domain'] = str(asset.get_editor_property('material_domain'))
            row['blend'] = str(asset.get_editor_property('blend_mode'))
            row['texture_nodes'] = []
            row['particle_color_nodes'] = []
            row['opacity_graph'] = []
            row['base_color_graph'] = []
            for expression in lib.get_material_expressions(asset):
                if isinstance(expression, u.MaterialExpressionParticleColor):
                    row['particle_color_nodes'].append(expression.get_name())
                if isinstance(expression, u.MaterialExpressionTextureSample):
                    texture = expression.get_editor_property('texture')
                    row['texture_nodes'].append({'node': expression.get_name(), 'texture': texture.get_path_name() if texture else None})
            for prop, key in [(u.MaterialProperty.MP_OPACITY, 'opacity_graph'), (u.MaterialProperty.MP_BASE_COLOR, 'base_color_graph')]:
                pending = [lib.get_material_property_input_node(asset, prop)]
                seen = set()
                while pending:
                    expression = pending.pop()
                    if not expression or expression.get_name() in seen:
                        continue
                    seen.add(expression.get_name())
                    item = {'node': expression.get_name(), 'class': expression.get_class().get_name()}
                    if isinstance(expression, u.MaterialExpressionScalarParameter) or isinstance(expression, u.MaterialExpressionVectorParameter):
                        item['parameter'] = str(expression.get_editor_property('parameter_name'))
                    if isinstance(expression, u.MaterialExpressionComponentMask):
                        item['channels'] = ''.join(n for n in 'rgba' if expression.get_editor_property(n))
                    row[key].append(item)
                    pending.extend(lib.get_inputs_for_material_expression(asset, expression))
    if isinstance(asset, u.Texture):
        row['srgb'] = asset.get_editor_property('srgb')
        row['compression'] = str(asset.get_editor_property('compression_settings'))
    if isinstance(asset, u.NiagaraSystem):
        row['emitters'] = emitters(asset)
    results.append(row)
folder = ROOT / 'Saved/BlizzardCloud20261001'
folder.mkdir(parents=True, exist_ok=True)
(folder / 'cloud-sources.json').write_text(json.dumps(results, indent=2), encoding='utf-8')
print('BLIZZARD_CLOUD_SOURCES ' + json.dumps(results))
