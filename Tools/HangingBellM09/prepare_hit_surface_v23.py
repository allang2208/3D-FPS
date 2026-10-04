import unreal as u,json
from pathlib import Path
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/HangingBellM09Meshy20261003/HitSurfaceV23/Records')
path='/Game/Monsters/HangingBellM09/V23/PA_M09_HitSurface'
A=u.EditorAssetLibrary
if not A.does_asset_exist(path):
    asset=A.duplicate_asset('/Game/Monsters/HangingBellM09/V04/SK_M09_PhysicsAsset',path)
    if not asset or not A.save_loaded_asset(asset,False):raise RuntimeError('Cannot create independent hit asset')
else:asset=u.load_asset(path)
(OUT/'prepared.json').write_text(json.dumps({'path':asset.get_path_name(),'status':'Placeholder copy; body authoring follows native build','original_physics_unchanged':True},indent=2),encoding='utf-8')
print('M09_HIT_ASSET_PREPARED')
