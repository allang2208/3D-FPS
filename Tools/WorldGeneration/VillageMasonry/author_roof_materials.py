"""Author the village timber and slate permutations from the currently bound Normandy finishes."""
from pathlib import Path
import json
import os
import sys

import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wall_material_sampling import FLAT, enable_flat

SOURCE = '/Game/UnrealNormandy/MaterialInstances'
DEST = '/Game/WorldGeneration/TemperateHills/AbandonedVillage/ExteriorMaterials'
LIB = u.MaterialEditingLibrary
ED = u.EditorAssetLibrary


# Scalar overrides shared by each active triplanar layer. Keeping the source functions
# intact lets other Normandy materials continue painting and tuning these channels.
NEUTRAL = {
    'RoughnessPower': 'Power_0',
    'AO_Power': 'Power_1',
    'Roughness_Multiplier': 'Multiply_3',
    'AO_Multiplier': 'Multiply_4',
}


def duplicate_or_load(source, name):
    dest = DEST + '/' + name
    obj = u.load_asset(dest) if ED.does_asset_exist(dest) else ED.duplicate_asset(source, dest)
    if not obj:
        raise RuntimeError('Cannot prepare ' + dest)
    return obj


def save(obj):
    if not ED.save_loaded_asset(obj, only_if_is_dirty=False):
        raise RuntimeError('Cannot save ' + obj.get_path_name())


def slate_settings(source):
    # Duplicate the original MIC to preserve overrides including static component masks.
    master = duplicate_or_load(source.parent.get_path_name(), 'M_VillageSlateTriplanar')
    calls = LIB.get_material_expressions(master)
    for layer in range(3):
        vendor_name = f'MF_TextureSet0{layer}_Base_Triplanar'
        local_name = f'MF_VillageSlateLayer0{layer}'
        fn = duplicate_or_load('/Game/UnrealNormandy/MaterialFunctions/' + vendor_name, local_name)
        nodes = {node.get_name(): node for node in LIB.get_material_function_expressions(fn)}
        constant = next((node for node in nodes.values() if isinstance(node, u.MaterialExpressionConstant)
                         and node.get_editor_property('desc') == 'Village slate unit controls'), None)
        if not constant:
            constant = LIB.create_material_expression_in_function(fn, u.MaterialExpressionConstant, -1600, 900)
            constant.set_editor_property('r', 1.)
            constant.set_editor_property('desc', 'Village slate unit controls')
        for param, target in NEUTRAL.items():
            name = f'TS0{layer}_' + param
            if LIB.get_material_instance_scalar_parameter_value(source, name) != 1.:
                raise RuntimeError('Cannot specialize a non-unit control: ' + name)
            node = nodes['MaterialExpression' + target]
            upstream = LIB.get_inputs_for_material_function_expression(fn, node)
            if len(upstream) != 2:
                raise RuntimeError('Input count changed for ' + name)
            if upstream[1] != constant:
                if (not isinstance(upstream[1], u.MaterialExpressionScalarParameter) or
                        str(upstream[1].get_editor_property('parameter_name')) != name):
                    raise RuntimeError('Input changed for ' + name)
                inputs = LIB.get_material_expression_input_names(node)
                if len(inputs) < 2 or not LIB.connect_material_expressions(constant, '', node, str(inputs[1])):
                    raise RuntimeError(f'Cannot bind {name} at {inputs}')
        LIB.update_material_function(fn)
        save(fn)
        call, = [n for n in calls if isinstance(n, u.MaterialExpressionMaterialFunctionCall) and
                 n.get_editor_property('material_function') and
                 n.get_editor_property('material_function').get_name() in (vendor_name, local_name)]
        if call.get_editor_property('material_function') != fn and not call.set_material_function(fn):
            raise RuntimeError('Cannot bind ' + local_name)
    errors = LIB.recompile_material(master)
    if errors:
        raise RuntimeError(str(errors))
    save(master)
    settings = duplicate_or_load(source.get_path_name(), 'MI_VillageSlateSettings')
    if settings.parent != master:
        LIB.set_material_instance_parent(settings, master)
        LIB.update_material_instance(settings)
        save(settings)
    return settings


def main():
    result = {}
    ED.make_directory(DEST)
    names = os.environ.get('VILLAGE_EXTERIOR_MATERIAL', '').split() or ['MI_Wood_00A', 'MI_Slate_00A', 'MI_Wood_00B']
    for name in names:
        if name not in ('MI_Wood_00A', 'MI_Slate_00A', 'MI_Wood_00B'):
            raise RuntimeError('Unknown exterior finish ' + name)
        parent = u.load_asset(SOURCE + '/' + name)
        if not parent or LIB.get_material_instance_scalar_parameter_value(parent, 'NormalGlobal_Intensity') != 0.:
            raise RuntimeError('The shared normal still affects ' + name)
        appearance_parent = slate_settings(parent) if name == 'MI_Slate_00A' else parent
        child_name = name + '_VillageExterior'
        path = DEST + '/' + child_name
        if ED.does_asset_exist(path):
            child = u.load_asset(path)
            if not child or child.parent not in (parent, appearance_parent):
                raise RuntimeError('Different parent at ' + path)
        else:
            child = u.AssetToolsHelpers.get_asset_tools().create_asset(child_name, DEST,
                u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
            if not child:
                raise RuntimeError('Could not create ' + path)
        if child.parent != appearance_parent:
            LIB.set_material_instance_parent(child, appearance_parent)
            LIB.update_material_instance(child)
        enable_flat(child)
        if not ED.save_loaded_asset(child, only_if_is_dirty=False):
            raise RuntimeError('Could not save ' + path)
        result[path] = {'source': parent.get_path_name(), 'parent': child.parent.get_path_name(), 'switch': FLAT}
    if output := os.environ.get('VILLAGE_EXTERIOR_RECEIPT'):
        Path(output).write_text(json.dumps(result, indent=2), encoding='utf-8')


main()
