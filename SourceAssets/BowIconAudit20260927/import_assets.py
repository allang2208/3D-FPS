"""Save matching Texture2D assets via the project batch bridge or headless UE."""
import hashlib,json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary
rows=json.loads((P/'icon-install-final-receipt.json').read_text(encoding='utf8'))['pngs']
paths={r['asset_folder']+'/'+r['name'] for r in rows}
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in paths]
if dirty:raise RuntimeError('Preserve unsaved icon packages '+str(dirty))
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active; end play before saving icon packages')
for row in rows:
    if hashlib.sha256(Path(row['png']).read_bytes()).hexdigest()!=row['sha256']:raise RuntimeError('PNG changed '+row['name'])
out=[]
for row in rows:
    task=u.AssetImportTask();task.filename=row['png'];task.destination_path=row['asset_folder'];task.destination_name=row['name']
    task.automated=True;task.replace_existing=True;task.save=False;A.import_asset_tasks([task])
    a=u.load_asset(task.destination_path+'/'+task.destination_name)
    if not isinstance(a,u.Texture2D):raise RuntimeError('Texture import failed '+row['name'])
    a.set_editor_property('srgb',True)
    a.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    a.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    a.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    E.set_metadata_tag(a,'BowIconSource','SourceAssets/BowIconAudit20260927/render-receipt.json')
    E.set_metadata_tag(a,'BowModularSource','SourceAssets/BowIconAudit20260927/render-receipt.json')
    E.set_metadata_tag(a,'ModificationIconPalette','neutral-grayscale-20260927')
    if not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+a.get_path_name())
    out.append(dict(name=row['name'],asset=a.get_path_name(),sha256=row['sha256'],saved=True))
    (P/'icon-import-receipt.json').write_text(json.dumps(dict(saved=out,gameplay_tested=False),indent=2),encoding='utf8')
print('BOW_MONOCHROME_TEXTURES_SAVED',len(out))
