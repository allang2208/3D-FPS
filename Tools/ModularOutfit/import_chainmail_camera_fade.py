"""Save three view-only camera-fade materials; keep all existing meshes intact.

Run with Run-Authoring.ps1 (or the existing editor's serialized Python bridge).
This builds material assets, without gameplay, animation sampling or previews.
"""
import hashlib
import json
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/ChainmailCameraFade20260930'
DEST = '/Game/Characters/ModularOutfit20260924/ChainmailCameraFade20260930/Materials'
L = u.MaterialEditingLibrary
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def asset_file(path):
    return P / 'Content' / (path.split('.')[0].removeprefix('/Game/') + '.uasset')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    asset = u.load_asset(path)
    if not asset:
        raise RuntimeError('Missing camera-fade input: ' + path)
    return asset


def material(source, name):
    destination = DEST + '/' + name
    mat = u.load_asset(destination)
    if mat:
        if E.get_metadata_tag(mat, 'CameraFadeSource') != source:
            raise RuntimeError('Camera-fade destination belongs to a different source: ' + destination)
    else:
        mat = A.duplicate_asset(name, DEST, load(source))
        if not mat:
            raise RuntimeError('Cannot create camera-fade material: ' + name)
        E.set_metadata_tag(mat, 'CameraFadeSource', source)

    def node(cls, **properties):
        value = L.create_material_expression(mat, cls)
        for key, data in properties.items():
            value.set_editor_property(key, data)
        return value

    def wire(source_node, target, pin, output=''):
        if isinstance(pin, int):
            pin = str(L.get_material_expression_input_names(target)[pin])
        if not L.connect_material_expressions(source_node, output, target, pin):
            raise RuntimeError('Camera-fade material pin: ' + str(pin))

    def scalar(parameter, value):
        return node(u.MaterialExpressionScalarParameter, parameter_name=parameter, default_value=value)

    def custom(code, inputs, description):
        value = node(u.MaterialExpressionCustom, code=code, description=description,
                     output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
        pins = []
        for key in inputs:
            pin = u.CustomInput()
            pin.set_editor_property('input_name', key)
            pins.append(pin)
        value.set_editor_property('inputs', pins)
        for key, source_node in inputs.items():
            wire(source_node, value, key)
        return value

    expressions = L.get_material_expressions(mat)
    if not any(isinstance(n, u.MaterialExpressionScalarParameter)
               and str(n.get_editor_property('parameter_name')) == 'OutfitCameraFadeEnabled'
               for n in expressions):
        inputs = {'RestPosition': node(u.MaterialExpressionPreSkinnedPosition)}
        for side in ('Left', 'Right'):
            for point in ('Shoulder', 'Elbow', 'Wrist'):
                parameter = node(u.MaterialExpressionVectorParameter,
                    parameter_name='OutfitFade' + point + side, default_value=u.LinearColor(0, 0, 0, 0))
                # Vector parameter RGB and A are separate expression outputs.
                vector4 = node(u.MaterialExpressionAppendVector)
                wire(parameter, vector4, 'A')
                wire(parameter, vector4, 'B', 'A')
                inputs[point + side] = vector4
        region = custom((P / 'Tools/ModularOutfit/chainmail_camera_region.ush').read_text(),
                        inputs, 'Chainmail near camera anatomical region')
        interpolator = node(u.MaterialExpressionVertexInterpolator)
        wire(region, interpolator, '')
        world = node(u.MaterialExpressionWorldPosition,
                     world_position_shader_offset=u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
        distance = node(u.MaterialExpressionDistance)
        wire(world, distance, 'A')
        wire(node(u.MaterialExpressionCameraPositionWS), distance, 'B')
        opacity = custom(
            'float Near=max(0.0,HiddenDistanceCm);\n'
            'float Far=max(Near+0.1,VisibleDistanceCm);\n'
            'float Visible=smoothstep(Near,Far,CameraDistance);\n'
            'return saturate(1.0-saturate(Enabled)*saturate(Region)*(1.0-Visible));',
            {'Region': interpolator, 'CameraDistance': distance,
             'HiddenDistanceCm': scalar('OutfitFadeHiddenDistanceCm', 10.),
             'VisibleDistanceCm': scalar('OutfitFadeVisibleDistanceCm', 22.),
             'Enabled': scalar('OutfitCameraFadeEnabled', 0.)},
            'Chainmail bounded near camera fade')
        dither = node(u.MaterialExpressionMaterialFunctionCall,
                      material_function=load('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
        wire(opacity, dither, 0)
        if mat.get_editor_property('use_material_attributes'):
            # These production masters already use a single MakeAttributes.
            # Keep their colour/normal/POM/roughness and previous-frame WPO wires.
            attrs = [n for n in expressions if isinstance(n, u.MaterialExpressionMakeMaterialAttributes)]
            if len(attrs) != 1:
                raise RuntimeError('Ambiguous source material attributes: ' + name)
            wire(dither, attrs[0], 'OpacityMask')
        elif not L.connect_material_property(dither, '', u.MaterialProperty.MP_OPACITY_MASK):
            raise RuntimeError('Cannot connect camera-fade opacity: ' + name)
        mat.set_editor_property('blend_mode', u.BlendMode.BLEND_MASKED)
        mat.set_editor_property('opacity_mask_clip_value', .333333)
        L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        E.set_metadata_tag(mat, 'CameraFadeRegion', 'Native reference upper arm; proximal forearm transition; cuff protected')
        E.set_metadata_tag(mat, 'CameraFadeDistancesCm', 'Hidden=10; full visibility=22; local outfit MID enables only')

    errors = L.recompile_material(mat)
    if errors:
        raise RuntimeError('Camera-fade shader compilation: ' + str(errors))
    mat.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([mat.get_outer()], False)
            or E.save_loaded_asset(mat, False)):
        raise RuntimeError('Camera-fade material save failed: ' + name)
    return mat.get_path_name()


def main():
    recipe = read(P / 'Content/ColdSteelData/modular_outfits.json')['items']['ue_chainmail_shirt']
    if recipe.get('secondary_motion') != 'chainmail_shared_sway_v1':
        raise RuntimeError('Active outfit setup changed; preserve it')
    R.mkdir(parents=True, exist_ok=True)
    if not (R / 'before.json').exists():
        write(R / 'before.json', recipe)
    sources = read(P / 'SourceAssets/ChainmailSharedSway20260929/materials-saved.json')
    names = [('mail', 'M_Chainmail_CameraFade'), ('steel', 'M_CuffSteel_CameraFade'), ('lining', 'M_Lining_CameraFade')]
    slots = []
    for key, name in names:
        path = material(sources[key], name)
        slots.append({'slot': key, 'source': sources[key], 'material': path, 'sha256': digest(asset_file(path))})
        print('CHAINMAIL_CAMERA_MATERIAL_SAVED', path, flush=True)
    write(R / 'saved.json', {'materials': slots, 'source_rig_meshes': recipe['rig_meshes'],
                            'hidden_distance_cm': 10., 'visible_distance_cm': 22.,
                            'mesh_edits': 0, 'animation_edits': 0, 'runtime_tested': False})


if __name__ == '__main__':
    main()
