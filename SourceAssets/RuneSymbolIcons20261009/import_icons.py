"""Import and save only the deployed rune icons, without launching play."""
from pathlib import Path
import json
import unreal as u

P=Path(__file__).resolve().parent
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End current play before saving the rune icons.')
deployment=json.loads((P/'deployment.json').read_text(encoding='utf-8'))
receipt={'complete':False,'saved_assets':[],'masters':deployment['masters'],'runtime_tested':False}
def record():
    (P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
record()
for row in deployment['icons']:
    folder,name=row['asset'].rsplit('/',1)
    task=u.AssetImportTask()
    for key,value in {'filename':row['png'],'destination_path':folder,'destination_name':name,
                      'automated':True,'replace_existing':True,'save':False}.items():task.set_editor_property(key,value)
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=u.load_asset(row['asset'])
    if not texture:raise RuntimeError('Import failed '+row['asset'])
    for key,value in {'srgb':True,'lod_group':u.TextureGroup.TEXTUREGROUP_UI,
                      'compression_settings':u.TextureCompressionSettings.TC_EDITOR_ICON,
                      'never_stream':True,'mip_gen_settings':u.TextureMipGenSettings.TMGS_NO_MIPMAPS}.items():
        texture.set_editor_property(key,value)
    u.EditorAssetLibrary.set_metadata_tag(texture,'AuthoringRevision','RuneSymbolIcons20261009')
    if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Save failed '+row['asset'])
    receipt['saved_assets'].append(texture.get_path_name());record()
receipt['complete']=True;record()
print('RUNE_SYMBOL_ICONS_SAVED '+str(len(receipt['saved_assets'])))
