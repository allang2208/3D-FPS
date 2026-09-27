"""Save the finished model's menu texture at the attachment UI content path.

Only asset production; no editor launch, PIE, audit or acceptance render.
Run in a Python commandlet when UE is closed, otherwise through the mutex bridge.
"""
from pathlib import Path
from datetime import datetime
import json
import unreal as u

P = Path(__file__).resolve().parent
library = u.EditorAssetLibrary
editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world() is not None:
    raise RuntimeError('End active PIE before saving the attachment icon.')
source = '/Game/Weapons/HighlandClaymore20260922/ThornCrown20260927/Textures/T_ThornCrown_MenuIcon'
target = '/Game/ColdSteelData/AttachmentIcons20260913/ue_highland_claymore_pommel_highland_thorn_crown'
if library.does_asset_exist(target):
    raise RuntimeError('Menu texture already exists; preserve it and inspect ownership before rerunning.')
texture = library.duplicate_asset(source, target)
if texture is None:
    raise RuntimeError('Could not duplicate the authored Thorn Crown icon.')
texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('srgb', True)
if not library.save_loaded_asset(texture, False):
    raise RuntimeError('Could not save the Thorn Crown menu texture.')
(P / 'menu_icon_receipt.json').write_text(json.dumps({
    'time': datetime.now().isoformat(),
    'asset': texture.get_path_name(),
    'source': source,
    'saved': True,
    'tested': False,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print('THORN_CROWN_MENU_ICON_SAVED ' + texture.get_path_name())
