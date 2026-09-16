import time, unreal
D='/Game/Props/RomanColumn20260915'; SEG=D+'/SM_BalustradeSegment_20'; STONE=D+'/M_RomanStone_V2'
SV = unreal.ModelingService
print('[seg] stone loadable:', unreal.EditorAssetLibrary.load_asset(STONE) is not None)
r = SV.set_asset_materials(SEG, STONE, True)
print('[seg] assign call:', getattr(r,'success',None), getattr(r,'message',''))
saved = unreal.EditorAssetLibrary.save_asset(SEG, False)
print('[seg] save_asset:', saved)
a = unreal.EditorAssetLibrary.load_asset(SEG)
m = a.get_editor_property('static_materials')[0].get_editor_property('material_interface')
print('[seg] verify slot0 =', m.get_path_name().split('.')[-1])
