"""Save the authored V3 impact material; reuse the already imported six-triangle mesh."""
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/SourceAssets/RuneSpectralBlade20260927/import_spectral_blade.py',init_globals={
    'SPECTRAL_MATERIAL_NAMES':('M_SpectralImpact',),
    'SPECTRAL_MESH_NAMES':(),
    'SPECTRAL_RECEIPT_NAME':'BlueExplosionV3/import_receipt.json'})
