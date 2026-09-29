"""Finish the saved Body material author's LOD stage using the loaded editor API."""
import unreal as u
from pathlib import Path
import json
import hashlib

path = '/Game/Characters/ModularOutfit20260924/OriginalLeatherV2/Body/SK_Body_OriginalLeatherV2'
mesh = u.load_asset(path)
if not mesh: raise RuntimeError('The Body UV author asset was not saved')
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
info = mesh.get_editor_property('lod_info')
info[0].set_editor_property('has_been_simplified',False)
mesh.set_editor_property('lod_info',info)
configured = u.FPSModularOutfitComponent.configure_outfit_lods(mesh)
print('BODY_LOD_CONFIGURED',configured,flush=True)
if not configured: raise RuntimeError('Could not configure authored Body LODs')
if not editor.regenerate_lod(mesh,3,True,False): raise RuntimeError('Could not generate authored Body LODs')
if not u.EditorLoadingAndSavingUtils.save_packages([mesh.get_outer()],False): raise RuntimeError('Could not save authored Body LODs')
root = Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260927/OriginalLeatherV2')
(root/'Saved').mkdir(exist_ok=True)
(root/'Saved/BodyGeometry.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),
    authored_sha256=hashlib.sha256((root/'Baked/Body.json').read_bytes()).hexdigest(),lods=3),indent=2)+'\n')
print('BODY_LODS_SAVED',mesh.get_path_name(),flush=True)
