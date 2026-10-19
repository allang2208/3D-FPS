"""Save fitted blade packages and reuse the existing standard framed icon masters."""
import json,runpy,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2];DATA=ROOT/'Content/ColdSteelData'
D='/Game/Weapons/Zhanmadao20261018/TangDaoBladesV1'
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor:raise RuntimeError('Asset import requires an editor or our commandlet, not a game process')
    if editor.is_in_play_in_editor():raise RuntimeError('Preserved active PIE; no assets changed')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(D+'/') or '/ue_zhanmadao_blade_1_' in package.get_name():
        raise RuntimeError('Preserved unsaved target package: '+package.get_name())
A=u.AssetToolsHelpers.get_asset_tools()
receipt={'complete':False,'assets_saved':False,'assets':[],'game_tested':False,'native_build_required':True}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def loaded(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Required asset missing: '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+obj.get_path_name())
    receipt['assets'].append(obj.get_path_name());record()
source=json.loads((DATA/'tang-dao-modules.json').read_text(encoding='utf-8-sig'))
rows=json.loads((P/'blade_exports.json').read_text(encoding='utf-8'))['options']
editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor_world:u.SystemLibrary.execute_console_command(editor_world.get_editor_world(),'Interchange.FeatureFlags.Import.FBX 0')
for row in rows:
    name=row['mesh_name'];path=D+'/Meshes/'+name;mesh=u.load_asset(path)
    if not mesh:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        opt.lod_number=3;opt.auto_compute_lod_distances=True
        cfg=opt.static_mesh_import_data;cfg.combine_meshes=False;cfg.import_mesh_lods=True
        cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False;cfg.build_nanite=False
        cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
        task=u.AssetImportTask();task.filename=str(P/'Export'/(name+'.fbx'));task.destination_name=name;task.destination_path=D+'/Meshes'
        task.options=opt;task.automated=True;task.replace_existing=False;task.save=False
        A.import_asset_tasks([task]);mesh=loaded(path)
    materials=source['slots']['blade_1'][row['id']]['materials']
    for index,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in materials:raise RuntimeError('Unmapped source material: '+key)
        mesh.set_material(index,loaded(materials[key]))
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;nanite.explicit_tangents=True;nanite.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',nanite);save(mesh)
    icon_name='ue_zhanmadao_blade_1_'+row['id'];icons=DATA/'AttachmentIcons20260913'
    target=icons/(icon_name+'.png');shutil.copy2(icons/('ue_tang_dao_blade_1_'+row['id']+'.png'),target)
    task=u.AssetImportTask();task.filename=str(target);task.destination_name=icon_name
    task.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';task.factory=u.TextureFactory()
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    A.import_asset_tasks([task]);tex=loaded(task.destination_path+'/'+icon_name)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True);save(tex)
receipt['assets_saved']=True;record()
runpy.run_path(str(P/'publish_catalog.py'))['publish']()
receipt.update(complete=True,new_meshes=2,saved_icons=2,catalog_saved=True);record()
print('ZHANMADAO_TANGDAO_BLADES_SAVED '+json.dumps(receipt),flush=True)
