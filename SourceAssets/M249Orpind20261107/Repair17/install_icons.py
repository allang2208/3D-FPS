"""Save the actual delivered catalog images as UI textures."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
r=Path(__file__).resolve().parent;p=r.parents[2];root='ColdSteelData/AttachmentIcons20260913'
specs=[(30,root+'/FramedFirearms'),(45,root)]
saved=[]
for capacity,dest in specs:
    key='ue_m249_magazine_m249_side_mag_'+str(capacity);source=r/'Icons'/(key+'.png');live=p/'Content'/dest/source.name
    live.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,live)
    t=u.AssetImportTask();t.filename=str(live);t.destination_path='/Game/'+dest;t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);a=u.load_asset('/Game/'+dest+'/'+key)
    if not a:raise RuntimeError('Texture import '+key)
    a.srgb=True;a.lod_group=u.TextureGroup.TEXTUREGROUP_UI;a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.never_stream=True;a.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    if not u.EditorAssetLibrary.save_loaded_asset(a,False):raise RuntimeError('Save '+key)
    saved.append(dict(capacity=capacity,path=a.get_path_name(),png=str(live),sha256=hashlib.sha256(live.read_bytes()).hexdigest(),framed=capacity==30))
(r/'icons_receipt.json').write_text(json.dumps(dict(saved=saved,extended_frame_generation='imagegen refused request with violence category; actual model render used',runtime_tested=False),indent=2))
print('M249_SIDE_MAG_ICONS_SAVED',len(saved),flush=True)
