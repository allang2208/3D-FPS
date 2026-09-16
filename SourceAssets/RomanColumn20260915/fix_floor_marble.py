import unreal
D='/Game/Props/RomanColumn20260915'; FLOOR=D+'/SM_MarbleFloorTiles'; MY=D+'/M_WhiteMarble_V2'
SV=unreal.ModelingService
a=unreal.EditorAssetLibrary.load_asset(FLOOR)
old=a.get_editor_property('static_materials')[0].get_editor_property('material_interface')
print('[floor] current slot0 =', old.get_path_name().split('.')[-1] if old else 'EMPTY')
if old and old.get_class().get_name()=='MaterialInstanceConstant':
    print('[floor] its parent =', old.get_editor_property('parent').get_path_name().split('.')[-1])
print('[floor] new material loadable:', unreal.EditorAssetLibrary.load_asset(MY) is not None)
r=SV.set_asset_materials(FLOOR, MY, True)
print('[floor] assign:', getattr(r,'success',None), getattr(r,'message',''))
print('[floor] save:', unreal.EditorAssetLibrary.save_asset(FLOOR, False))
b=unreal.EditorAssetLibrary.load_asset(FLOOR)
print('[floor] verify slot0 =', b.get_editor_property('static_materials')[0].get_editor_property('material_interface').get_path_name().split('.')[-1])
