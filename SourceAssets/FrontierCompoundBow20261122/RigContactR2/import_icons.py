from pathlib import Path
import json,os,unreal as u
source=Path(__file__).resolve().parent/'Export'
rows=[('bow_frontier_compound',source,'/Game/ColdSteelData/Icons')]
for slot in ('riser','arrow_rest'):
    rows.append(('bow_frontier_compound_'+slot+'_false',source/'PartIcons','/Game/ColdSteelData/AttachmentIcons20260913/FramedBows'))
saved={}
for name,src,folder in rows:
    t=u.AssetImportTask();t.filename=str(src/(name+'.png'));t.destination_path=folder
    t.destination_name=name+'_r2';t.automated=True;t.replace_existing=True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    a=u.load_asset(folder+'/'+name+'_r2');a.lod_group=u.TextureGroup.TEXTUREGROUP_UI
    a.compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON;a.mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS;a.srgb=True
    if not u.EditorLoadingAndSavingUtils.save_packages([a.get_outermost()],False):raise RuntimeError(name)
    saved[name]=a.get_path_name()
(Path(os.environ['FRONTIER_BATCH'])/'icons.json').write_text(json.dumps(saved,indent=2),encoding='utf8')
