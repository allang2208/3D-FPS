"""Deploy only the nine corrected icon masters to fifteen existing runtime keys."""
import unreal as u
import json, shutil, hashlib
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE is active; defer icon import without stopping play')
rows=json.loads((P/'sources.json').read_text(encoding='utf-8'))['parts']
DEST='/Game/ColdSteelData/AttachmentIcons20260913'
disk=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
targets={DEST+'/'+key for row in rows for key in row['keys']}
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name() in targets:raise RuntimeError('Unsaved target: '+pkg.get_name())
archive=ROOT/'trash/warhammer-icons-replaced-20261014';archive.mkdir(parents=True,exist_ok=True)
baseline=[]
for row in rows:
    for key in row['keys']:
        for suffix in ('.png','.uasset','.uexp','.ubulk'):
            old=disk/(key+suffix);backup=archive/(key+suffix)
            if old.exists():
                if not backup.exists():shutil.copy2(old,backup)
                baseline.append({'original':str(old.relative_to(ROOT)),'backup':str(backup.relative_to(ROOT)),
                                 'sha256':hashlib.sha256(backup.read_bytes()).hexdigest()})
manifest=archive/'manifest.json'
if not manifest.exists():manifest.write_text(json.dumps({'reason':'User requested approved metal-frame icon correction',
    'retained_source_assets':True,'files':baseline},ensure_ascii=False,indent=2),encoding='utf-8')
receipt={'complete':False,'game_tested':False,'masters':len(rows),'assets':[],'mapping':[],
         'archive':str(archive),'texture_settings':{'group':'UI','compression':'EditorIcon','srgb':True,'never_stream':True,'mips':False}}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
record();tools=u.AssetToolsHelpers.get_asset_tools()
for row in rows:
    source=P/'Final'/(row['id']+'.png')
    for key in row['keys']:
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=key
        task.automated=True;task.replace_existing=True;task.save=False
        tools.import_asset_tasks([task]);texture=u.load_asset(DEST+'/'+key)
        if not texture:raise RuntimeError('Icon import failed: '+key)
        texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
        texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True)
        texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):raise RuntimeError('Save failed: '+key)
        shutil.copy2(source,disk/(key+'.png'))
        receipt['assets'].append(texture.get_path_name())
        receipt['mapping'].append({'key':key,'master':str(source.relative_to(ROOT)),'source_model':row['runtime_mesh']})
        record()
receipt['complete']=True;record()
print('WARHAMMER_ICONS_SAVED '+str(len(receipt['assets'])))
