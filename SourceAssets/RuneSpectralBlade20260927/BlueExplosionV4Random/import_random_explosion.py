"""Save the randomized impact shader while preserving all existing meshes and blade materials."""
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/SourceAssets/RuneSpectralBlade20260927/import_spectral_blade.py',init_globals={
    'SPECTRAL_MATERIAL_NAMES':('M_SpectralImpact',),
    'SPECTRAL_MESH_NAMES':(),
    'SPECTRAL_RECEIPT_NAME':'BlueExplosionV4Random/import_receipt.json'})
