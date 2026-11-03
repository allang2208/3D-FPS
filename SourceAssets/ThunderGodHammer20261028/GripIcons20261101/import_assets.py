"""Install only the two requested grip icons at the keys used by M4GunsmithLayout."""
from pathlib import Path
import datetime, hashlib, json, os, shutil
import unreal as u

P = Path(__file__).resolve().parent
R = P.parents[2]
if Path(u.Paths.project_dir()).resolve() != R:
    raise RuntimeError('Wrong project')
mapping = json.loads((P / 'mapping.json').read_text(encoding='utf-8'))
folder = '/Game/ColdSteelData/AttachmentIcons20260913'
targets = {folder+'/'+row['key'] for row in mapping['items']}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_path_name() in targets:
        raise RuntimeError('Preserving unsaved target package: '+package.get_path_name())
for row in mapping['items']:
    if not (P / (row['id']+'_framed.png')).is_file():
        raise RuntimeError('Generated icon missing: '+row['id'])

backup = P / 'Backups' / datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
backup.mkdir(parents=True, exist_ok=True)
receipt = dict(complete=False, revision=mapping['revision'], icons=[], runtime_tested=False)
def record():
    (P / 'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
record()
asset_tools = u.AssetToolsHelpers.get_asset_tools()
for row in mapping['items']:
    key = row['key']
    source = P / (row['id']+'_framed.png')
    dest = R / 'Content/ColdSteelData/AttachmentIcons20260913' / (key+'.png')
    backed_up = []
    for suffix in ('.png', '.uasset', '.uexp', '.ubulk'):
        old = dest.with_suffix(suffix)
        if old.is_file():
            shutil.copy2(old, backup / old.name)
            backed_up.append(str(backup / old.name))
    pending = dest.with_suffix('.grip-icons-20261101-pending')
    shutil.copy2(source, pending)
    os.replace(pending, dest)
    task = u.AssetImportTask()
    task.filename = str(dest)
    task.destination_path = folder
    task.destination_name = key
    task.automated = True
    task.save = False
    task.replace_existing = True
    task.replace_existing_settings = True
    asset_tools.import_asset_tasks([task])
    tex = u.load_asset(folder+'/'+key)
    if not tex:
        raise RuntimeError('Icon import failed: '+key)
    tex.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb', True)
    tex.set_editor_property('never_stream', True)
    tex.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('max_texture_size', 1024)
    u.EditorAssetLibrary.set_metadata_tag(tex, 'AuthoringRevision', mapping['revision'])
    tex.modify()
    if not u.EditorLoadingAndSavingUtils.save_packages([tex.get_outermost()], False):
        raise RuntimeError('Icon save failed: '+key)
    receipt['icons'].append(dict(id=row['id'], asset=tex.get_path_name(), runtime_png=str(dest),
        source=str(source), sha256=hashlib.sha256(source.read_bytes()).hexdigest(), backups=backed_up,
        generator='built-in imagegen', source_model=row['runtime_mesh'],
        settings=dict(group='UI',compression='EditorIcon',srgb=True,never_stream=True,mipmaps=False)))
    record()
receipt['complete'] = True
record()
print('THUNDER_GRIP_ICONS_SAVED', len(receipt['icons']))
