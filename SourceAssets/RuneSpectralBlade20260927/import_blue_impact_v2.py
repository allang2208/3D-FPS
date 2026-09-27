"""Rebuild blue materials and import only the new hit particle, preserving sword meshes."""
import runpy
runpy.run_path('D:/FPS3D/FPSGAME/SourceAssets/RuneSpectralBlade20260927/import_spectral_blade.py',init_globals={
    'SPECTRAL_MESH_NAMES':('SM_SpectralImpactParticle',),
    'SPECTRAL_RECEIPT_NAME':'BlueImpactV2/import_receipt.json'})
