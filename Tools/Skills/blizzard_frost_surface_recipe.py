"""Remove the repeated 5x5 artwork from Blizzard's existing ground frost decal."""
import unreal as u
from build_fireball_assets import LIB

TAG = 'Blizzard.FrostSingleField20261115'
UV_CODE = ('float2 warp=float2(sin(UV.y*7.1+UV.x*3.7),cos(UV.x*6.3-UV.y*4.1))*.045; '
           'return clamp(UV+warp,.002,.998);')


def apply(material):
    changed = 0
    for node in LIB.get_material_expressions(material):
        if not isinstance(node, u.MaterialExpressionCustom):
            continue
        code = str(node.get_editor_property('code'))
        description = str(node.get_editor_property('description'))
        if code.replace(' ', '') == 'returnUV*5;' or description == TAG:
            node.set_editor_property('code', UV_CODE)
            node.set_editor_property('description', TAG)
            changed += 1
    if not changed:
        raise RuntimeError('Cannot find Blizzard frost tiled UV source')
    u.EditorAssetLibrary.set_metadata_tag(material, TAG, '1')
    LIB.recompile_material(material)
    return {'uv_nodes_updated': changed, 'texture_repetitions': 1,
            'room_mask_and_frost_opacity_preserved': True}
