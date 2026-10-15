"""Create a fresh corpse copy from the living mesh and export its actual surface."""
import json,shutil
from pathlib import Path
import unreal as u
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/HeQueBoss20261014/SoftDeathV02'
DEST='/Game/Monsters/HeQue/SoftCorpseV02';E=u.EditorAssetLibrary
for folder in ('HeQue','Records','Before'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE before corpse authoring')
if any(p.get_path_name().startswith('/Game/Monsters/HeQue') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved HeQue assets')
bp=u.load_asset('/Game/Monsters/HeQue/BP_HeQue');source=u.get_default_object(bp.generated_class()).get_editor_property('visual_mesh')
if not source:raise RuntimeError('HeQue living mesh is missing')
old=PROJECT/'Content'/(source.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
backup=ROOT/'Before'/old.name
if not backup.exists():shutil.copy2(old,backup)
corpse_path=DEST+'/SK_HeQue_SoftCorpseV02';skeleton_path=DEST+'/SKEL_HeQue_SoftCorpseV02'
corpse=u.load_asset(corpse_path) or E.duplicate_asset(source.get_path_name(),corpse_path)
skeleton=u.load_asset(skeleton_path) or E.duplicate_asset(source.skeleton.get_path_name(),skeleton_path)
data=u.load_asset(DEST+'/DA_HeQue_SoftCorpseV02')
bound=data and data.get_editor_property('corpse_mesh')==corpse
if not bound:
    if not u.M14SoftBodyData.export_surface(corpse,str(ROOT/'HeQue/surface.bin'),[]):raise RuntimeError('HeQue surface export failed')
    if not E.save_loaded_asset(corpse,False) or not E.save_loaded_asset(skeleton,False):raise RuntimeError('Fresh corpse copy save failed')
elif not (ROOT/'HeQue/surface.bin').exists():raise RuntimeError('Original surface export missing; do not export an already rebound corpse')
item=dict(key='HeQue',source=source.get_path_name(),corpse=corpse_path,skeleton=skeleton_path,
    source_skeleton=source.skeleton.get_path_name(),characters=['HeQue'])
(ROOT/'sources.json').write_text(json.dumps([item],indent=2),encoding='utf8')
print('HEQUE_CORPSE_V02_SOURCE '+json.dumps(item),flush=True)
