"""Import the design-built meshes, update existing shared icons, then publish the recipe."""
import unreal as u,json,shutil
from pathlib import Path
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/CommonHammerHeads20261014/DesignV2'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong target project')
editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and editor and editor.is_in_play_in_editor():
    raise RuntimeError('PIE is active; preserve the running game and defer this asset import')
rows=json.loads((P/'exports.json').read_text(encoding='utf-8'))['parts']
icons='/Game/ColdSteelData/AttachmentIcons20260913'
targets={D+'/'+row['mesh'] for row in rows}|{icons+'/hammer_heads_'+row['id'] for row in rows}
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name() in targets:raise RuntimeError('Unsaved target: '+package.get_name())
materials={'factory':u.load_asset('/Game/Weapons/SteelWarhammer20261014/Materials/M_SteelWarhammerSurface'),
           'steel':u.load_asset('/Game/Weapons/CommonHammerHeads20261014/Materials/M_CommonHammerHeadSteel')}
if any(not m for m in materials.values()):raise RuntimeError('Existing steel material is unavailable')
A=u.AssetToolsHelpers.get_asset_tools();receipt={'complete':False,'tested':False,'assets':[],'revision':'DesignV2'}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
data=opt.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
for row in rows:
    path=D+'/'+row['mesh'];mesh=u.load_asset(path)
    if not mesh:
        task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'));task.destination_path=D;task.destination_name=row['mesh'];task.automated=True;task.save=False;task.options=opt
        A.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Mesh import failed: '+path)
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.material_slot_name)
        if 'CommonHammerHeadSteel' in name:mesh.set_material(i,materials['steel'])
        elif 'SteelWarhammerSurface' in name:mesh.set_material(i,materials['factory'])
        else:raise RuntimeError('Unknown material slot: '+name)
    save(mesh)
before=P/'Before';before.mkdir(exist_ok=True)
icon_dir=ROOT/'Content/ColdSteelData/AttachmentIcons20260913'
for row in rows:
    name='hammer_heads_'+row['id'];file=icon_dir/(name+'.png')
    for suffix in ('.png','.uasset'):
        old=file.with_suffix(suffix);backup=before/(name+suffix)
        if old.exists() and not backup.exists():shutil.copy2(old,backup)
    source=P/'Icons'/(row['id']+'.png')
    task=u.AssetImportTask();task.filename=str(source);task.destination_path=icons;task.destination_name=name;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);texture=u.load_asset(icons+'/'+name)
    if not texture:raise RuntimeError('Icon import failed: '+name)
    texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);texture.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);save(texture)
    shutil.copy2(source,file)
catalog_path=ROOT/'Content/ColdSteelData/warhammer-modules.json'
if not (before/catalog_path.name).exists():shutil.copy2(catalog_path,before/catalog_path.name)
catalog=json.loads(catalog_path.read_text(encoding='utf-8-sig'))
for row in rows:
    choice=catalog['slots']['hammer_heads'][row['id']]
    choice['mesh']=D+'/'+row['mesh']+'.'+row['mesh'];choice['location_cm']=row['location_cm'];choice['model_revision']='DesignV2'
catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt['complete']=True;(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');print(json.dumps(receipt))
