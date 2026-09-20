"""Synchronize the deployed PNGs to their UE texture copies in the open editor."""
import unreal as u, json
from pathlib import Path

P = Path(__file__).parent
ROOT = P.parents[1]
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before importing pommel icons; keep the editor open.')
receipt = []
for name in ['ballast_hardened', 'ballast_rune', 'ballast_magic_orb']:
    key = 'ue_rune_sword_pommel_' + name
    source = ROOT / 'Content/ColdSteelData/AttachmentIcons20260913' / (key + '.png')
    path = '/Game/ColdSteelData/AttachmentIcons20260913/' + key
    result = u.ModelingService.import_texture(str(source), path, True, 'Default', True)
    if not result.success:
        raise RuntimeError(result.message)
    texture = u.load_asset(path)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError('Icon save failed: ' + path)
    receipt.append({'source': str(source), 'asset': texture.get_path_name(), 'saved': True})
    (P / 'icon_import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('POMMEL_ICON_SAVED', texture.get_path_name())
