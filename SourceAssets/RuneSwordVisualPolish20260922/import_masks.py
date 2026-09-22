"""Replace only native rune mask textures; no level or gameplay operations."""
from pathlib import Path
from datetime import datetime
import json,shutil
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
D='/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is active; native rune texture saving requires PIE to end.')
receipt=[]
for name in ['T_RuneSword_NativeMask','T_RuneSword_GuardNativeMask']:
    file=ROOT/'Content'/D.removeprefix('/Game/')/(name+'.uasset')
    if file.exists() and not (P/'Before'/file.name).exists():shutil.copy2(file,P/'Before'/file.name)
    t=u.AssetImportTask();t.filename=str(P/(name+'.png'));t.destination_path=D;t.destination_name=name
    t.automated=True;t.replace_existing=True;t.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    asset=u.load_asset(D+'/'+name)
    if not asset:raise RuntimeError('Mask import failed '+name)
    asset.set_editor_property('srgb',False)
    asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    asset.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Mask save failed '+name)
    receipt.append({'source':t.filename,'asset':asset.get_path_name(),'saved':True})
(P/'mask_import_receipt.json').write_text(json.dumps({'time':datetime.now().isoformat(),'assets':receipt},indent=2),encoding='utf-8')
print('RUNE_ROOT_MASKS_IMPORTED',len(receipt))
