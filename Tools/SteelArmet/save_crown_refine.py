"""Save isolated crown-refined meshes with the active helmet's existing materials."""
import gc, hashlib, importlib.util, json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME')
R=P/'SourceAssets/SteelArmet20261019/CrownRefine20261020'
DEST='/Game/Characters/ModularOutfit20260924/SteelArmet20261019/CrownRefine20261020'
E=u.EditorAssetLibrary
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,str(P/path))
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result
dynamic=module('crown_dynamic','Tools/BlueMageSetIcons/save_icons.py').dynamic
static_io=module('crown_static','Tools/ChainmailPants/save_assets.py')
static_io.DEST=DEST
authored=json.loads((R/'authored.json').read_text())
if not authored.get('completed'):raise RuntimeError('Finish crown authoring first')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('End play before saving crown-refined mesh assets')
config=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
source=config['head_equipment']['ue_steel_armet']['static_mesh']
old=u.load_asset(source)
if not old:raise RuntimeError('Active helmet missing '+source)
mats=[slot.material_interface for slot in old.get_editor_property('static_materials')]
if len(mats)!=len(authored['material_slots']) or any(not m for m in mats):
    raise RuntimeError('Active helmet materials differ from the crown source')
receipt=dict(completed=False,source_mesh=source,materials=[m.get_path_name() for m in mats],
             saved={},runtime_tested=False)
def record():(R/'saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record()
for key,file,suffix in [('mesh','helmet.json','SM_SteelArmet'),
                        ('pickup','helmet.json','Pickups/SM_SteelArmet_Pickup'),
                        ('icon','display.json','Icons/SM_SteelArmet_Icon')]:
    raw=(R/'Authored'/file).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    path=DEST+'/'+suffix;asset=u.load_asset(path)
    if not asset or E.get_metadata_tag(asset,'SteelArmetSourceSHA')!=sha:
        dm=dynamic(json.loads(raw))
        result=static_io.static(dm,path,mats);asset=u.load_asset(result)
        E.set_metadata_tag(asset,'SteelArmetSourceSHA',sha)
        E.set_metadata_tag(asset,'EquipmentDefinition','ue_steel_armet')
        static_io.save(asset)
        del dm
    receipt[key]=asset.get_path_name()
    receipt['saved'][key]=dict(asset=asset.get_path_name(),sha256=sha)
    record();print('STEEL_ARMET_CROWN_SAVED',key,flush=True)
    del asset;gc.collect();u.SystemLibrary.collect_garbage()
task=u.AssetImportTask()
task.filename=str(R/'ue_steel_armet.png')
task.destination_path=DEST+'/Textures';task.destination_name='T_SteelArmet_Icon'
task.automated=True;task.replace_existing=True;task.save=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
tex=u.load_asset(DEST+'/Textures/T_SteelArmet_Icon')
if not tex:raise RuntimeError('Crown icon import failed')
for name,value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
    compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
    mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,srgb=True,
    address_x=u.TextureAddress.TA_CLAMP,address_y=u.TextureAddress.TA_CLAMP).items():
    tex.set_editor_property(name,value)
static_io.save(tex)
receipt.update(completed=True,icon_texture=tex.get_path_name(),
    icon_sha256=hashlib.sha256((R/'ue_steel_armet.png').read_bytes()).hexdigest())
record()
print('STEEL_ARMET_CROWN_COMPLETE',flush=True)
