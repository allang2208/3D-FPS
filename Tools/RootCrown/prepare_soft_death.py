"""Export a separate corpse source while preserving the current living mesh."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014/SoftDeathV01')
DEST='/Game/Monsters/RootCrown/SoftDeathV01';E=u.EditorAssetLibrary
ROOT.mkdir(exist_ok=True);folder=ROOT/'RootCrown';folder.mkdir(exist_ok=True)
source=u.load_asset('/Game/Monsters/RootCrown/RigV01/SK_RootCrown')
path=DEST+'/SK_RootCrown_SoftCorpse'
if any(p.get_path_name().startswith('/Game/Monsters/RootCrown') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved Root Crown assets')
corpse=u.load_asset(path) or E.duplicate_asset(source.get_path_name(),path)
data=u.load_asset(DEST+'/DA_RootCrown_SoftCorpse')
if data and data.get_editor_property('corpse_mesh')==corpse:
    if not (folder/'surface.bin').exists():raise RuntimeError('Original corpse surface missing')
else:
    if not u.M14SoftBodyData.export_surface(corpse,str(folder/'surface.bin'),[]):raise RuntimeError('Root Crown surface export failed')
    if not E.save_loaded_asset(corpse,False):raise RuntimeError('Root Crown corpse copy could not be saved')
item=dict(key='RootCrown',characters=['RootCrownRig'],source=source.get_path_name(),corpse=path,skeleton=source.skeleton.get_path_name(),tested=False)
(ROOT/'sources.json').write_text(json.dumps([item],indent=2),encoding='utf8')
print('ROOT_CROWN_SOFT_SOURCE_SAVED '+path)
