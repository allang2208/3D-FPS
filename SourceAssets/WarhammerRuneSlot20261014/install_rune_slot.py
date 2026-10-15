"""Replace the selectable neck column with an empty rune slot; retain the neck mesh."""
import unreal as u,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[1]
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():raise RuntimeError('PIE is active; defer without stopping play')
DATA=ROOT/'Content/ColdSteelData';ICONS=DATA/'AttachmentIcons20260913';DEST='/Game/ColdSteelData/AttachmentIcons20260913'
mapping=[{'key':'category_rune','source':'blade_2_resonance_rune.png','role':'rune category representative glyph only'},
         {'key':'rune_false','source':'FramedFirearms/bipod_false.png','role':'neutral empty-slot mark'}]
targets={DEST+'/'+row['key'] for row in mapping}
for pkg in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if pkg.get_name() in targets:raise RuntimeError('Unsaved target: '+pkg.get_name())
before=P/'Before';before.mkdir(parents=True,exist_ok=True)
for name in ('warhammer-gunsmith.json','warhammer-modules.json'):
    if not (before/name).exists():shutil.copy2(DATA/name,before/name)
receipt={'complete':False,'game_tested':False,'slot':'rune','replaced_selectable_slot':'neck',
    'fixed_physical_module':'neck','new_rune_effects':[],'assets':[],'icon_mapping':mapping}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
record();A=u.AssetToolsHelpers.get_asset_tools()
for row in mapping:
    source=ICONS/row['source'];key=row['key']
    texture=u.load_asset(DEST+'/'+key)
    if not texture:
        task=u.AssetImportTask();task.filename=str(source);task.destination_path=DEST;task.destination_name=key
        task.automated=True;task.save=False;A.import_asset_tasks([task]);texture=u.load_asset(DEST+'/'+key)
        if not texture:raise RuntimeError('Texture import failed: '+key)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True)
    texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):raise RuntimeError('Save failed: '+key)
    shutil.copy2(source,ICONS/(key+'.png'));receipt['assets'].append(texture.get_path_name());record()
path=DATA/'warhammer-gunsmith.json';catalog=json.loads(path.read_text(encoding='utf-8-sig'))
column=next(c for c in catalog['columns'] if c['key'] in ('neck','rune'))
column.update(key='rune',name='符文',default='无符文',description='未刻印符文，保留战锤原有的金属表面。')
path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
path=DATA/'warhammer-modules.json';modules=json.loads(path.read_text(encoding='utf-8-sig'))
# Appearance metadata is separate from the physical module list. The neck remains
# in module_slots and resolves to its only factory mesh for every valid loadout.
modules['slots'].setdefault('rune',{})['factory']={'appearance':'未刻印符文 · 原有金属表面'}
modules['slots']['neck']['factory']['appearance']='固定锤颈套箍'
path.write_text(json.dumps(modules,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt['complete']=True;record();print('WARHAMMER_RUNE_SLOT_SAVED')
