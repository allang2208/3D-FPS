"""Save the one updated GuanLei icon, then publish its saved model and tier."""
from pathlib import Path
import datetime,hashlib,json,os,runpy,shutil
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
key='ue_thunder_god_hammer_head_mount_guan_lei_seat'
folder='/Game/ColdSteelData/AttachmentIcons20260913';asset_path=folder+'/'+key
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if asset_path in dirty:raise RuntimeError('Preserving unsaved GuanLei icon')
source=P/'GuanLeiC8_FramedIcon.png'
dest=R/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
backup=P/'Backups'/('Icon-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
if dest.exists():shutil.copy2(dest,backup/dest.name)
pending=dest.with_suffix('.guanlei-c8-pending');shutil.copy2(source,pending);os.replace(pending,dest)
task=u.AssetImportTask();task.filename=str(dest);task.destination_path=folder;task.destination_name=key
task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
tex=u.load_asset(asset_path)
if not tex:raise RuntimeError('Icon import failed')
tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
u.EditorAssetLibrary.set_metadata_tag(tex,'AuthoringRevision','GuanLeiReturnC8')
if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed')
(P/'icon_import_receipt.json').write_text(json.dumps({'saved':True,'asset':tex.get_path_name(),
    'source':str(source),'runtime_png':str(dest),'backup':str(backup),
    'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'generator':'built-in imagegen',
    'actual_model_reference':str(P/'GuanLeiC8_IconSource.png'),'prompt':str(P/'icon_prompt.txt'),
    'gameplay_tested':False},ensure_ascii=False,indent=2),encoding='utf-8')
print('GUANLEI_C8_PRODUCTION_ICON_SAVED')
runpy.run_path(str(P/'publish.py'),run_name='__main__')
