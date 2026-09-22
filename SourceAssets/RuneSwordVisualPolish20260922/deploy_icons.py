"""Deploy the declared 29 PNGs and corresponding UE textures as one bridge batch."""
from pathlib import Path
from datetime import datetime
import json,shutil,hashlib
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
D='/Game/ColdSteelData/AttachmentIcons20260913'
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is active; icon asset saving requires PIE to end.')
rows=json.loads((P/'icon_manifest.json').read_text(encoding='utf-8'))
receipt={'time':datetime.now().isoformat(),'icons':[]}
for row in rows:
    key=row['key'];source=P/'Icons'/(key+'.png');deployed=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'/source.name
    shutil.copy2(source,deployed)
    result=u.ModelingService.import_texture(str(deployed),D+'/'+key,True,'Default',True)
    if not result.success:raise RuntimeError(result.message)
    tex=u.load_asset(D+'/'+key)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('srgb',True)
    if not u.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Icon save failed '+key)
    receipt['icons'].append({'key':key,'png':str(deployed),'sha256':hashlib.sha256(deployed.read_bytes()).hexdigest(),'asset':tex.get_path_name(),'saved':True})
    (P/'icon_deploy_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('RUNE_POLISH_ICONS_DEPLOYED',len(receipt['icons']))
