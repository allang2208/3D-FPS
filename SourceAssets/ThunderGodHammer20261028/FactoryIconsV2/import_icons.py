"""Import and save the exact runtime icon keys through the live editor bridge."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[2]
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
A=u.AssetToolsHelpers.get_asset_tools();D='/Game/ColdSteelData/AttachmentIcons20260913';receipt={'complete':False,'saved':[],'runtime_tested':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
record()
for row in json.loads((P/'deployment_manifest.json').read_text(encoding='utf-8'))['runtime_png_keys']:
    task=u.AssetImportTask();task.filename=row['destination'];task.destination_path=D;task.destination_name=row['key'];task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    A.import_asset_tasks([task]);tex=u.load_asset(D+'/'+row['key'])
    if not tex:raise RuntimeError('Icon import failed '+row['key'])
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True);tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()],False):raise RuntimeError('Icon save failed '+row['key'])
    receipt['saved'].append(tex.get_path_name());record()
receipt['complete']=True;record();print('THUNDER_FACTORY_ICONS_SAVED',len(receipt['saved']))
