"""Save three new mesh assets and merge only this sword's three option entries."""
import copy,json,shutil
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/XuanChiZhenYue20261004/CommonBlades20261005'
E=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('Exit PIE before importing the three blade modules; no assets changed')
spec=json.loads((P/'exports.json').read_text(encoding='utf-8'))
material=u.load_asset(spec['material'])
if not material:raise RuntimeError('Current silver relief material is required')
receipt={'complete':False,'assets':[],'catalog_saved':False,'game_tested':False}
def record():(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Asset save failed: '+asset.get_path_name())
    receipt['assets'].append(asset.get_path_name());record()
world=E.get_editor_world()
if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
for row in spec['options']:
    asset_path=D+'/Meshes/'+row['mesh']
    mesh=u.load_asset(asset_path)
    if not mesh:
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_as_skeletal=False;options.import_mesh=True
        options.import_materials=False;options.import_textures=False;options.import_animations=False
        cfg=options.static_mesh_import_data
        cfg.combine_meshes=True;cfg.auto_generate_collision=False;cfg.generate_lightmap_u_vs=False
        cfg.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        cfg.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE;cfg.build_nanite=False
        task=u.AssetImportTask();task.filename=str(P/'Export'/(row['mesh']+'.fbx'))
        task.destination_path=D+'/Meshes';task.destination_name=row['mesh']
        task.automated=True;task.replace_existing=False;task.save=False;task.options=options
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        mesh=u.load_asset(asset_path)
        if not mesh or not task.imported_object_paths:raise RuntimeError('Import failed: '+asset_path)
    mesh.set_material(0,material)
    build=u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_lod_build_settings(mesh,0)
    build.recompute_normals=False;build.recompute_tangents=True;build.use_mikk_t_space=True
    build.use_full_precision_u_vs=True
    u.get_editor_subsystem(u.StaticMeshEditorSubsystem).set_lod_build_settings(mesh,0,build)
    save(mesh)

path=ROOT/'Content/ColdSteelData/xuanchi-zhenyue-modules.json'
before=path.read_bytes();catalog=json.loads(before.decode('utf-8-sig'))
backup=P/'Before';backup.mkdir(exist_ok=True)
if not (backup/path.name).exists():(backup/path.name).write_bytes(before)
for row in spec['options']:
    variant=copy.deepcopy(catalog['slots']['blade_1']['factory'])
    asset=D+'/Meshes/'+row['mesh'];variant['mesh']=asset+'.'+row['mesh']
    variant['rune_dimensions_cm']=row['rune_dimensions_cm']
    variant['trace_tip_cm']=row['trace_tip_cm']
    variant['appearance']={'extended_edge':'延展中段与长锋，保留原装剑根及云螭浅刻纹',
        'heavy_spine':'宽肩厚脊与双侧开刃，保留云螭浅刻纹及亮银金属',
        'feather_edge':'收窄剑身与轻薄剑脊，保留连续剑根及云螭浅刻纹'}[row['option']]
    catalog['slots']['blade_1'][row['option']]=variant
if path.read_bytes()!=before:raise RuntimeError('Catalog changed during merge; saved mesh assets retained')
temp=path.with_suffix('.common-blades.tmp')
temp.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(path)
receipt['catalog_saved']=True;receipt['complete']=True;record()
print('XUANCHI_COMMON_BLADES_SAVED '+json.dumps(receipt))
