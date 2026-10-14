"""Import detailed facility fittings and save the production and two transit maps."""
from pathlib import Path
from datetime import datetime
import copy,json,runpy,shutil,traceback,re
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'))
save_world=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
E=u.EditorAssetLibrary;SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
def import_mesh(item):
    path=item['mesh'];mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    source=E.get_metadata_tag(mesh,'FacilityDetailRepair.Source') if mesh else None
    if mesh and source not in (item['sha256'],item.get('previous_sha256','')):raise RuntimeError('Preserve differing asset '+path)
    if not mesh or source!=item['sha256'] or item.get('force_reimport'):
        if mesh and item.get('authored_tangents'):
            previous_import=mesh.get_editor_property('asset_import_data')
            if isinstance(previous_import,u.FbxStaticMeshImportData):previous_import.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
        t=u.AssetImportTask();t.filename=item['fbx'];t.destination_path,t.destination_name=path.rsplit('/',1)
        t.automated=True;t.save=False;t.replace_existing=bool(mesh);t.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
        opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True
        d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.one_convex_hull_per_ucx=True
        d.generate_lightmap_u_vs=False;d.build_nanite=False
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS if item.get('authored_tangents') else u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        t.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Import failed '+path)
    mesh.modify()
    for i,slot in enumerate(mesh.static_materials):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
        if not mat:raise RuntimeError('Missing material '+key)
        mesh.set_material(i,mat)
    build=SM.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;build.use_high_precision_tangent_basis=True;build.recompute_tangents=not item.get('authored_tangents',False)
    if item.get('tangent_basis')=='ue_legacy':build.use_mikk_t_space=False;build.recompute_tangents=True
    SM.set_lod_build_settings(mesh,0,build)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
    settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=item['nanite'];settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.;mesh.set_editor_property('nanite_settings',settings)
    if item['nanite'] and not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Mesh build failed '+path)
    E.set_metadata_tag(mesh,'FacilityDetailRepair.Source',item['sha256'])
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Asset save failed '+path)
    return path
def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    if any(p.get_name().startswith(R['BASE']) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved task assets')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    report=dict(stage='preparing',revision=R['REVISION'],saved_assets=[],maps=[],game_run=False,rendered=False,runtime_tested=False)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    for target in (TARGET,*R['SUBJECTS']):
        rel=target.removeprefix('/Game/')
        for path in [PROJECT/'Content'/(rel+'.umap'),*(PROJECT/'Content'/sub/rel for sub in ('__ExternalActors__','__ExternalObjects__'))]:
            if not path.exists():continue
            dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True)
            if path.is_dir():shutil.copytree(path,dest)
            else:shutil.copy2(path,dest)
    for path in (FLOW/'Config/catalog.json',FLOW/'Config/layout-bank-v1.json'):
        dest=backup/path.relative_to(PROJECT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
    report['backup']=str(backup);record()
    try:
        report['saved_assets'].extend(runpy.run_path(str(ROOT/'materials.py'))['install']());record()
        for item in R['manifest']():report['saved_assets'].append(import_mesh(item));record()
        report['stage']='assets_saved';record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET);generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json');catalog=json.loads(raw)
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash'];bank=catalog['facility_flow']['layout_bank']
        if bank['contract_sha1']!=contract(catalog):raise RuntimeError('Preserve inconsistent layout contract')
        changes=R['apply_catalog'](catalog)
        bank['contract_sha1']=contract(catalog)
        superseded=R['superseded']();serialized=json.dumps(catalog,ensure_ascii=False)
        assets=[a for a in generator.get_editor_property('module_assets') if a and (a.get_path_name().split('.')[0] not in superseded or a.get_path_name().split('.')[0] in serialized)]
        known={a.get_path_name() for a in assets}
        for module in catalog['modules']:
            if module['id']!='FacilityTransit':continue
            for path in module['runtime_assets']:
                a=u.load_asset(path)
                if not a:raise RuntimeError('Missing runtime dependency '+path)
                if a.get_path_name() not in known:known.add(a.get_path_name());assets.append(a)
        generator.modify();generator.set_editor_property('module_assets',assets);generator.set_editor_property('module_catalog_json',serialized)
        save_world(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='production_saved',replacements=changes,original_lights_preserved=True)
        report['maps'].append(dict(path=TARGET,saved=True));record()
        for target in R['SUBJECTS']:
            world=u.EditorLoadingAndSavingUtils.load_map(target);changed=R['apply_subject'](world);save_world(world,target)
            report['maps'].append(dict(path=target,saved=True,changed=changed));record()
        report['stage']='maps_saved';record();print('FACILITY_DETAIL_REPAIR_SAVED',len(report['saved_assets']),'assets;',len(report['maps']),'maps')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)
if __name__=='__main__':main()
