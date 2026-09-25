"""Rebuild the corrected V3 mesh using its already saved texture inputs."""
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/Tools/ModularOutfit/import_original_shape_m4.py',init_globals={
 'AUTHOR_ROOT':'D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924/OriginalShapeBareM4/RefinedSkinV3',
 'ASSET_DEST':'/Game/Characters/ModularOutfit20260924/OriginalShapeBareM4RefinedV3',
 'SMOOTH_SKIN':True,'REFINED_SKIN':True,'RESUME_TEXTURES':True})
