"""Save CPU surface access on the existing death-only mesh; preserve live assets."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchCorpseContact20261002')
path = '/Game/Monsters/WitchRebuilt/CorpseFollow/SK_WitchRebuilt_CorpseFollow'
mesh = u.load_asset(path)
if not mesh:
    raise RuntimeError('Missing saved connected corpse mesh: '+path)
u.SkeletalMeshEditorSubsystem.set_allow_cpu_access(mesh, True)
u.EditorAssetLibrary.set_metadata_tag(mesh, 'CorpseSurfaceGrounding',
    'LOD0 CPU surface: bounded core/foot skin sampling once on freeze; core first then connected legs')
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('Corpse surface access save failed')
result = dict(mesh=mesh.get_path_name(), assets_saved=True, lod0_cpu_access=True,
    live_mesh_preserved=True, physics_asset_preserved=True, runtime_tested=False)
(root/'assets.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
