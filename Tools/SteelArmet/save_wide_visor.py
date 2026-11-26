"""Save only the wider owner visor, in a new package independent of live equipment."""
import hashlib, json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/SteelArmet20261019/FirstPersonWide20261020'
DEST='/Game/Characters/ModularOutfit20260924/SteelArmet20261019/FirstPersonWide20261020'
E=u.EditorAssetLibrary
source=R/'Textures/T_SteelArmet_Visor.png'
authored=json.loads((R/'visor.json').read_text())
if not authored.get('completed'):raise RuntimeError('Author the wider visor first')
sha=hashlib.sha256(source.read_bytes()).hexdigest()
path=DEST+'/T_SteelArmet_VisorWide'
tex=u.load_asset(path)
if not tex or E.get_metadata_tag(tex,'SteelArmetSourceSHA')!=sha:
    if tex and '-run=' not in u.SystemLibrary.get_command_line().lower():
        editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():
            raise RuntimeError('End play before replacing an already imported visor')
    task=u.AssetImportTask()
    task.filename=str(source)
    task.destination_path=DEST
    task.destination_name='T_SteelArmet_VisorWide'
    task.automated=True
    task.replace_existing=True
    task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    tex=u.load_asset(path)
    if not tex:raise RuntimeError('Wider visor import failed')
    for name,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
        compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
        mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True,
        address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP).items():
        tex.set_editor_property(name,value)
    E.set_metadata_tag(tex,'SteelArmetSourceSHA',sha)
    E.set_metadata_tag(tex,'SteelArmetVisorRevision','first-person-wide-20261020')
    if not E.save_loaded_asset(tex,False):raise RuntimeError('Wider visor save failed')
receipt=dict(completed=True,visor_texture=tex.get_path_name(),source_sha256=sha,
    clear_center_height_fraction=authored['clear_center_height_fraction'],
    clear_max_width_fraction=authored['clear_max_width_fraction'],runtime_tested=False)
(R/'saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('STEEL_ARMET_WIDE_VISOR_SAVED',tex.get_path_name(),flush=True)
