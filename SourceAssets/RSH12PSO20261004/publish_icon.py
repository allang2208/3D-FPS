"""Promote the existing framed PSO option image to its shared key, without re-rendering."""
import json,shutil
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];E=u.EditorAssetLibrary
folder=P/'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
source=folder/'ue_pkm_lowpoly_optic_pso1_4x.png';dest=folder/'optic_pso1_4x.png'
root='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
if not dest.exists():shutil.copy2(source,dest)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if editor and editor.get_game_world():raise RuntimeError('PIE is active; shared PNG is ready, save the Texture after play ends')
path=root+'/optic_pso1_4x'
texture=u.load_asset(path) if E.does_asset_exist(path) else E.duplicate_asset(root+'/ue_pkm_lowpoly_optic_pso1_4x',path)
if not texture or not E.save_loaded_asset(texture,False):raise RuntimeError('Cannot save shared PSO icon')
(O/'icon_receipt.json').write_text(json.dumps(dict(source=str(source),shared_png=str(dest),shared_texture=texture.get_path_name(),new_render=False),indent=2))
print('RSH_PSO_SHARED_ICON_SAVED',texture.get_path_name(),flush=True)
