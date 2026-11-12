"""Import only the M249 category and factory artwork into the existing UI textures."""
from pathlib import Path
import hashlib
import json
import unreal as ue

project=Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
here=project/'SourceAssets/M249Orpind20261107/BipodIcon42'
record=json.loads((here/'deployment.json').read_text())
folder='/Game/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
disk=project/'Content'/folder[6:]
receipt=here/'saved.json'
saved=json.loads(receipt.read_text()) if receipt.exists() else {}
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

if '-run=' not in ue.SystemLibrary.get_command_line().lower() and ue.get_editor_subsystem(ue.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('M249_BIPOD_ICON_WAIT_FOR_PIE')
dirty={p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for key in record['pngs']:
    path=folder+'/'+key
    package=disk/(key+'.uasset')
    png=disk/(key+'.png')
    if digest(png)!=record['master_sha256'] or path in dirty or digest(package)!=saved.get(path,record['before'][package.name]):
        raise RuntimeError('Production texture changed: '+path)
    if path in saved: continue
    task=ue.AssetImportTask()
    task.filename=str(png)
    task.destination_path=folder
    task.destination_name=key
    task.replace_existing=True
    task.automated=True
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Import failed: '+path)
    tex=ue.load_asset(path)
    tex.set_editor_property('lod_group',ue.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',ue.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('srgb',True)
    tex.set_editor_property('never_stream',True)
    tex.set_editor_property('mip_gen_settings',ue.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not ue.EditorAssetLibrary.save_loaded_asset(tex,False):raise RuntimeError('Save failed: '+path)
    saved[path]=digest(package)
    receipt.write_text(json.dumps(saved,indent=2))
print('M249_BIPOD_ICONS_SAVED',len(saved),flush=True)
