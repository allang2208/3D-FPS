"""Author distant LODs while keeping the accepted base geometry and cloth bindings."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/WitchRebuilt20260921/Revision12'
PATH = '/Game/Monsters/WitchRebuilt/SK_WitchRebuilt'
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve() != ROOT / 'FPSGAME.uproject':
    raise RuntimeError('Unexpected editor project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Existing PIE preserved; distance LOD installation deferred')
if any(p.get_path_name() == PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved Witch mesh preserved')
source = ROOT / 'Content/Monsters/WitchRebuilt/SK_WitchRebuilt.uasset'
backup = OUT / 'Before/SK_WitchRebuilt.uasset'
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(source, backup)
mesh = u.load_asset(PATH)
editor = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
before = {'lod_count': editor.get_lod_count(mesh), 'lod0_vertices': editor.get_num_verts(mesh, 0),
          'lod0_sections': editor.get_num_sections(mesh, 0)}
if not u.WitchRebuiltMonster.configure_distance_lods(mesh):
    raise RuntimeError('Witch LOD authoring refused this base mesh')
if not editor.regenerate_lod(mesh, 3, False, False):
    raise RuntimeError('Witch distance LOD generation failed; package not saved')
lods = [{'lod': i, 'vertices': editor.get_num_verts(mesh, i), 'sections': editor.get_num_sections(mesh, i)} for i in range(editor.get_lod_count(mesh))]
if len(lods) != 3 or lods[0]['vertices'] != before['lod0_vertices'] or lods[0]['sections'] != before['lod0_sections']:
    raise RuntimeError('Base mesh/count differs after generation; package not saved')
if not (0 < lods[2]['vertices'] < lods[1]['vertices'] < lods[0]['vertices']):
    raise RuntimeError('Generated LODs did not reduce the vertex budget; package not saved')
u.EditorAssetLibrary.set_metadata_tag(mesh, 'WitchDistanceLODs', 'Distance12: original LOD0 cloth, 50%/20% triangle targets, near-cloth runtime LOD0 guard')
if not u.EditorAssetLibrary.save_loaded_asset(mesh, False):
    raise RuntimeError('Distance LOD save failed')
report = {'mesh': PATH, 'before': before, 'lods': lods,
          'cloth_assets': [a.get_name() for a in mesh.get_editor_property('mesh_clothing_assets')],
          'triangle_targets': [1., .5, .2], 'screen_sizes': [None, .09, .035],
          'cloth_resume_cm': 2000, 'cloth_suspend_cm': 2400, 'cloth_fade_s': .35,
          'backup': str(backup), 'backup_sha256': hashlib.sha256(backup.read_bytes()).hexdigest(),
          'saved': True, 'runtime_tested': False}
(OUT / 'distance_lods.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
