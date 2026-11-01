"""Save two production icons, publish V9, and retire only Thor's two adaptations."""
from pathlib import Path
import datetime,hashlib,json,os,runpy,shutil
import unreal as u
P=Path(__file__).resolve().parent;R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
if not json.loads((P/'import_receipt.json').read_text(encoding='utf-8'))['complete']:raise RuntimeError('Models not saved')
folder='/Game/ColdSteelData/AttachmentIcons20260913'
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
ids=('guan_lei_seat','ji_lei_seat')
for id in ids:
 if folder+'/ue_thunder_god_hammer_head_mount_'+id in dirty:raise RuntimeError('Preserving unsaved icon '+id)
backup=P/'Backups'/('Icons-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'));backup.mkdir(parents=True)
receipt=dict(complete=False,icons=[],runtime_tested=False)
def record():(P/'icon_import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
record()
for id in ids:
 key='ue_thunder_god_hammer_head_mount_'+id;asset_path=folder+'/'+key
 source=P/'Icons'/(id+'_framed.png');dest=R/'Content/ColdSteelData/AttachmentIcons20260913'/(key+'.png')
 for suffix in ('.png','.uasset','.uexp','.ubulk'):
  old=dest.with_suffix(suffix)
  if old.is_file():shutil.copy2(old,backup/old.name)
 pending=dest.with_suffix('.seat-v9-pending');shutil.copy2(source,pending);os.replace(pending,dest)
 task=u.AssetImportTask();task.filename=str(dest);task.destination_path=folder;task.destination_name=key
 task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
 u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);tex=u.load_asset(asset_path)
 if not tex:raise RuntimeError('Icon import failed '+id)
 tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
 tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
 tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True)
 tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
 u.EditorAssetLibrary.set_metadata_tag(tex,'AuthoringRevision','SeatDistinctV9')
 if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed '+id)
 receipt['icons'].append(dict(id=id,asset=tex.get_path_name(),source=str(source),runtime_png=str(dest),backup=str(backup),sha256=hashlib.sha256(source.read_bytes()).hexdigest(),generator='built-in imagegen',actual_model_reference=str(P/'Icons'/(id+'_source.png')),prompt=str(P/'Icons'/(id+'_prompt.txt'))));record()
receipt['complete']=True;record();print('THUNDER_V9_TWO_PRODUCTION_ICONS_SAVED')
runpy.run_path(str(P/'publish.py'),run_name='__main__')
runpy.run_path(str(P/'retire_assets.py'),run_name='__main__')
