"""Save the rebuilt wrist and CC0 skin detail variant, then publish M4 profile."""
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/Tools/ModularOutfit/import_original_shape_m4.py',init_globals={
 'AUTHOR_ROOT':'D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/RefinedSkinV3',
 'ASSET_DEST':'/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4RefinedV3',
 'SMOOTH_SKIN':True,'REFINED_SKIN':True})
