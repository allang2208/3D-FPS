"""Prepare a separate M-88 corpse and export anatomical production inputs."""
from pathlib import Path
import json
import unreal as u
P=Path('D:/FPS3D/FPSGAME')
OUT=P/'SourceAssets/BoundCongregateMeshy20261006/DeathV32'
BASE='/Game/Monsters/BoundCongregate'
DEST=BASE+'/DeathV32'
SOURCE=BASE+'/TentacleReachV29/SK_BoundCongregate_TentacleReachV29'
E=u.EditorAssetLibrary
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve PIE')
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if any(p.startswith(DEST) or p==SOURCE for p in dirty):raise RuntimeError('Preserve unsaved monster assets')
live=u.load_asset(SOURCE)
cdo=u.get_default_object(u.load_asset(BASE+'/BP_BoundCongregate').generated_class())
if cdo.get_editor_property('visual_mesh')!=live:raise RuntimeError('Live visual changed')
def duplicate(obj,path):return u.load_asset(path) or E.duplicate_asset(obj.get_path_name(),path)
corpse=duplicate(live,DEST+'/SK_BoundCongregate_CorpseV32')
skel=duplicate(live.skeleton,DEST+'/SKEL_BoundCongregate_CorpseV32')
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
data=u.load_asset(DEST+'/DA_BoundCongregate_CorpseV32') or u.AssetToolsHelpers.get_asset_tools().create_asset('DA_BoundCongregate_CorpseV32',DEST,u.M14SoftBodyData,factory)
if data.get_editor_property('corpse_mesh'):raise RuntimeError('Already bound; do not author a second proxy skeleton over it')
u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilationFinishAll')
u.BoundCongregate.prepare_corpse_mesh(corpse)
count=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).get_lod_count(corpse)
if count>1 and not u.SkeletalMeshEditorSubsystem.remove_lods(corpse,list(range(1,count))):raise RuntimeError('Remove unrebound corpse LODs failed')
if not u.M14SoftBodyData.export_surface(corpse,str(OUT/'surface.bin'),[]):raise RuntimeError('Surface export failed')
if not (OUT/'surface.bin.skin.json').is_file():raise RuntimeError('Updated authoring function is not loaded')
for a in (corpse,skel,data):
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
(OUT/'prepare.json').write_text(json.dumps(dict(prepared=True,source=SOURCE,corpse=corpse.get_path_name(),skeleton=skel.get_path_name(),tested=False),indent=2),encoding='utf8')
print('BOUND_DEATH_V32_PREPARED',flush=True)
