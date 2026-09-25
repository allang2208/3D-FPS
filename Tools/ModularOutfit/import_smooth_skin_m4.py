"""Import/save the V2 smooth original-shape M4 and publish its saved profile."""
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/Tools/ModularOutfit/import_original_shape_m4.py',init_globals={
 'AUTHOR_ROOT':'D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/SmoothSkinV2',
 'ASSET_DEST':'/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4SmoothV2',
 'SMOOTH_SKIN':True})
