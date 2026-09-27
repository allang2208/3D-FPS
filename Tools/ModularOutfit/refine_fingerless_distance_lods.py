"""Preserve shared finger openings when simplifying the assembled equipment skin."""
import json
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2'
s=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
for name,path in json.loads((R/'SkinCoverage/asset-receipt.json').read_text())['profiles'].items():
    mesh=u.load_asset(path)
    if not (u.FPSModularOutfitComponent.configure_outfit_lods(mesh) and s.regenerate_lod(mesh,3,True,False)):raise RuntimeError('Cannot regenerate '+name)
    mesh.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outer()],False) or u.EditorAssetLibrary.save_loaded_asset(mesh,False)):raise RuntimeError('Cannot save '+name)
    print('FINGERLESS_DISTANCE_SAVED',name,flush=True)
exec((P/'Tools/ModularOutfit/read_final_fingerless_clearance.py').read_text())
