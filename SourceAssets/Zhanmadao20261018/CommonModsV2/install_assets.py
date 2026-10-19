"""Import fitted common modules and replace icon packages in the existing editor."""
import json,runpy,sys
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2];D='/Game/Weapons/Zhanmadao20261018/CommonModsV2'
sys.path.insert(0,str(P))
if Path(u.Paths.project_dir()).resolve()!=ROOT:raise RuntimeError('Wrong project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if not editor:raise RuntimeError('This is a game-only process; asset import requires the editor or our own commandlet')
    if editor and editor.is_in_play_in_editor():raise RuntimeError('End PIE before saving fitted modules and replacement icons; nothing changed')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith(D+'/') or '/ue_zhanmadao_' in package.get_name():
        raise RuntimeError('Preserved unsaved target package: '+package.get_name())
A=u.AssetToolsHelpers.get_asset_tools();L=u.EditorAssetLibrary
receipt={'complete':False,'assets_saved':False,'assets':[],'game_tested':False,'native_build_required':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def loaded(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Required shared asset missing: '+path)
    return obj
def save(obj):
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):raise RuntimeError('Save failed: '+obj.get_path_name())
    if obj.get_path_name() not in receipt['assets']:receipt['assets'].append(obj.get_path_name())
    record()
materials={'M_Zhanmadao_Surface_V1':loaded('/Game/Weapons/Zhanmadao20261018/V1/Materials/M_Zhanmadao_Surface_V1')}
for name in ['Leather','Steel','Textile']:materials['M_SharedGrip_'+name]=loaded('/Game/Weapons/SharedSwordGrips20260927/Materials/M_SharedGrip_'+name)
loaded('/Game/Weapons/AnimationProfiles20261001/Melee/DA_Sword_LongGrip')
variants=json.loads((P/'variant_exports.json').read_text(encoding='utf-8'))
grips=json.loads((P/'grip_exports.json').read_text(encoding='utf-8'))
editor_world=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor_world.get_editor_world() if editor_world else None
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
rows=variants['options']+variants['adapters']+grips['options']
for row in rows:
    path=D+'/Meshes/'+row['mesh'];mesh=u.load_asset(path)
    if not mesh:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
        cfg=opt.static_mesh_import_data;cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
        cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;cfg.build_nanite=True
        task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'));task.destination_name=row['mesh'];task.destination_path=D+'/Meshes'
        task.options=opt;task.automated=True;task.replace_existing=False;task.save=False
        A.import_asset_tasks([task]);mesh=loaded(path)
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name)
        if key not in materials:raise RuntimeError('Unmapped material: '+key)
        mesh.set_material(i,materials[key])
    # FBXNIM_IMPORT_NORMALS preserves authored normals and builds Mikk tangents;
    # use import settings directly because editor subsystems are absent in a commandlet.
    nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;nanite.explicit_tangents=True;nanite.fallback_relative_error=0
    mesh.set_editor_property('nanite_settings',nanite);save(mesh)
jobs=runpy.run_path(str(P/'deploy_icons.py'))['deploy']()
for job in jobs:
    task=u.AssetImportTask();task.filename=job['file'];task.destination_path,task.destination_name=job['asset'].rsplit('/',1)
    task.factory=u.TextureFactory();task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    A.import_asset_tasks([task]);tex=loaded(job['asset'])
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON)
    tex.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);tex.set_editor_property('srgb',True);tex.set_editor_property('never_stream',True);save(tex)
receipt['assets_saved']=True;record()
coverage=runpy.run_path(str(P/'publish_catalog.py'))['publish']()
receipt.update(complete=True,common_options=coverage['common_count'],new_meshes=len(rows),saved_icons=len(jobs),catalog_saved=True)
record();print('ZHANMADAO_COMMON_MODS_AND_STANDARD_ICONS_SAVED '+json.dumps(receipt))
