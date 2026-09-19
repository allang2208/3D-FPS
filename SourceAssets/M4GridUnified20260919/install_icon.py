import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;ROOT=O.parents[1];LIVE=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';BACK=O/'Before';BACK.mkdir(exist_ok=True)
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;report=[]
keys=['ue_m4a1_magazine_ext_mag','magazine_ext_mag']
for key in keys:
 source=O/'Icons'/((key if key!='magazine_ext_mag' else 'ue_m4a1_magazine_ext_mag')+'.png');target=LIVE/(key+'.png')
 before=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
 for suffix in ['.png','.uasset']:
  old=LIVE/(key+suffix)
  if old.exists() and not (BACK/old.name).exists():shutil.copy2(old,BACK/old.name)
 shutil.copy2(source,target)
 t=u.AssetImportTask();t.filename=str(target);t.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False;A.import_asset_tasks([t])
 tex=u.load_asset(t.destination_path+'/'+key)
 if not isinstance(tex,u.Texture2D):raise RuntimeError('Texture import failed '+key)
 tex.srgb=True;tex.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;tex.lod_group=u.TextureGroup.TEXTUREGROUP_UI;tex.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS
 E.set_metadata_tag(tex,'AttachmentIconRule','Front-left; gun-up; horizontal orthographic; current M4 unified factory grille model; transparent 1024 RGBA')
 saved=E.save_loaded_asset(tex,False)
 report.append({'key':key,'png':str(target),'sha256_before':before,'sha256_after':hashlib.sha256(target.read_bytes()).hexdigest(),'texture':tex.get_path_name(),'texture_saved':saved,'shared_reference':'M4 fallback only; three rifles use dedicated PNGs' if key=='magazine_ext_mag' else None})
 (O/'install_receipt.json').write_text(json.dumps(report,indent=2))
 if not saved:raise RuntimeError('Texture save blocked '+key)
u.log('EXTMAG_ICONS_INSTALLED '+str(len(report)))
