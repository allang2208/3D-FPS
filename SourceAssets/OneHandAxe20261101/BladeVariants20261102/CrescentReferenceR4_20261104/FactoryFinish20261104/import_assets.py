"""Update only R4 PBR textures and its shared icon; retain saved mesh and material graph."""
import ast,json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;R4=P.parent
DEST='/Game/Weapons/TacticalHatchet20261101/ModulesV1'
ICON_DEST='/Game/ColdSteelData/AttachmentIcons20260913'
CONTENT=P.parents[4]/'Content'
A=u.AssetToolsHelpers.get_asset_tools();E=u.MaterialEditingLibrary
entry=json.loads((R4/'SwiftCrescent.json').read_text('utf-8'))
jobs=json.loads((R4/'icon_deployments.json').read_text('utf-8'))
receipt={'complete':False,'assets':[],'icons':[],'mesh_reimported':False,'material_graph_modified':False,'runtime_tested':False}
owned={DEST+'/Textures/'+Path(path).stem for path in entry['textures'].values()}|{ICON_DEST+'/'+job['key'] for job in jobs}
dirty={package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty&owned:raise RuntimeError('Owned textures have unsaved changes; preserved: '+str(dirty&owned))
helper=R4.parents[1]/'ModulesV1/import_modules.py';tree=ast.parse(helper.read_text('utf-8-sig'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'save','imported'}],type_ignores=[]),str(helper),'exec'),globals())
for package in sorted(owned):
    path=CONTENT/(package.removeprefix('/Game/')+'.uasset');backup=P/'Before/UE'/path.relative_to(CONTENT)
    backup.parent.mkdir(parents=True,exist_ok=True)
    if path.exists() and not backup.exists():shutil.copy2(path,backup)
factory=u.load_asset('/Game/Weapons/TacticalHatchet20261101/Materials/M_TacticalHatchet')
receipt['factory_material']=factory.get_path_name()
receipt['factory_textures']=[texture.get_path_name() for texture in E.get_used_textures(factory)]
for role,path in entry['textures'].items():
    texture=imported(path,Path(path).stem,DEST+'/Textures')
    texture.set_editor_property('srgb',role=='BaseColor')
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if role=='BaseColor' else u.TextureCompressionSettings.TC_NORMALMAP if role=='Normal' else u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if role=='Normal' else u.TextureGroup.TEXTUREGROUP_WEAPON)
    texture.set_editor_property('never_stream',False)
    if role=='Normal':texture.set_editor_property('flip_green_channel',True)
    u.EditorAssetLibrary.set_metadata_tag(texture,'FactoryFinishSource','Original hatchet '+role+'; UV-adapted body and cutting edge swatches')
    save(texture)
for job in jobs:
    texture=imported(job['source'],job['key'],ICON_DEST)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('srgb',True);texture.set_editor_property('never_stream',True)
    texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    texture.set_editor_property('max_texture_size',1024)
    save(texture);receipt['icons'].append(texture.get_path_name())
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
u.log('CRESCENT_FACTORY_FINISH_SAVED assets='+str(len(receipt['assets'])))
