import unreal,json
from pathlib import Path
out=Path('D:/FPS3D/FPSGAME/SourceAssets/GASPTraversal20260910/Native')
b=json.loads((out/'bounds.json').read_text())
path='/Game/Movement/Traversal/Native/SK_TraversalArms_AnimatedBounds'
m=unreal.EditorAssetLibrary.duplicate_asset('/Game/Movement/Traversal/Native/SK_TraversalArms',path) if not unreal.EditorAssetLibrary.does_asset_exist(path) else unreal.load_asset(path)
old=m.get_imported_bounds();center=[old.origin.x,old.origin.y,old.origin.z];extent=[old.box_extent.x,old.box_extent.y,old.box_extent.z]
positive=[max(0,b['max'][i]-center[i]-extent[i]) for i in range(3)]
negative=[max(0,center[i]-extent[i]-b['min'][i]) for i in range(3)]
m.set_editor_property('positive_bounds_extension',unreal.Vector(*positive));m.set_editor_property('negative_bounds_extension',unreal.Vector(*negative))
assert unreal.EditorAssetLibrary.save_loaded_asset(m,False)
unreal.log('TRAVERSAL_BOUNDS_SAVED '+str(m.get_bounds()))
