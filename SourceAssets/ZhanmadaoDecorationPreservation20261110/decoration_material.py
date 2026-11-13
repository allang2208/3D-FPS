"""Blade-specific protection for Zhanmadao native decoration, not steel tint."""
import runpy
from pathlib import Path

P = Path(__file__).resolve().parent
COMMON = runpy.run_path(str(P.parent / 'ChixiaoInlayPreservation20261110/inlay_material.py'))
REVISION = 'ZhanmadaoDecorationPreservation20261110V1'
PREFIX = 'M_TangDaoBladeRuneSurface_Zhanmadao_'
WARM_CODE = '''// Reuse each blade's native UV0 atlas: neutral/cool steel has no
// positive red chroma; warm root detail and gilded ornament do.
float chroma=NativeColor.r-max(NativeColor.g,NativeColor.b);
return smoothstep(.002,.020,chroma)/3.0;
'''
CYAN_CODE = '''// Zhufeng author_blade.py writes Metallic=.98-.25*band.
// This native channel distinguishes the cyan inlay from the blue-gray steel,
// without protecting the entire cool blade or adding another texture sample.
return smoothstep(.01,.05,.98-NativeMetallic)/3.0;
'''
PROFILES = {
    **{PREFIX + key + '_0_BeiweiV1': ('T_Zhanmadao_BaseColor_V1', WARM_CODE, 'NativeColor', 'RGB')
       for key in ['factory', 'extended_edge', 'heavy_spine', 'feather_edge']},
    PREFIX + 'yanling_edge_0_BeiweiV1': ('T_TangDao_BaseColor', WARM_CODE, 'NativeColor', 'RGB'),
    PREFIX + 'tengyun_dragon_0_BeiweiV1': ('T_TangDao_Tengyun_BaseColor', WARM_CODE, 'NativeColor', 'RGB'),
    PREFIX + 'zhufeng_V1': ('T_Zhufeng_ORM_V1', CYAN_CODE, 'NativeMetallic', 'B'),
}


def apply_decoration_protection(material):
    if COMMON['apply_inlay_protection'](material):
        return True
    name = material.get_name().removesuffix('_Whirlwind')
    profile = PROFILES.get(name)
    if not profile:
        return False
    texture, code, input_name, channel = profile
    return COMMON['apply_surface_protection'](material, texture, REVISION, code,
                                              input_name, channel, 'ZhanmadaoDecorationRevision')
