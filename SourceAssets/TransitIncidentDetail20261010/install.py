"""Import detailed incident props and replace only their mesh references in saved maps."""
from pathlib import Path
from datetime import datetime
import copy,json,runpy,shutil,traceback,re
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'));M=runpy.run_path(str(ROOT/'materials.py'))
save_world=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
E=u.EditorAssetLibrary;SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

def import_mesh(item):
    path=item['mesh'];mesh=M['owned'](path)
    if mesh:
        if E.get_metadata_tag(mesh,'TransitIncidentDetail.Source')!=item['sha256']:raise RuntimeError('Preserve differing asset '+path)
        return path
    t=u.AssetImportTask();t.filename=item['fbx'];t.destination_path,t.destination_name=path.rsplit('/',1)
    t.automated=True;t.save=False;t.replace_existing=False;t.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True
    d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.build_nanite=False
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    t.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.static_materials):
        key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));mat=u.load_asset(item['materials'][key])
        if not mat:raise RuntimeError('Missing material '+key)
        mesh.set_material(i,mat)
    build=SM.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;build.use_high_precision_tangent_basis=True;build.recompute_tangents=True
    SM.set_lod_build_settings(mesh,0,build);mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
    E.set_metadata_tag(mesh,'TransitIncidentDetail.Source',item['sha256']);M['save'](mesh);return path

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    if any(p.get_name().startswith(R['BASE']) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved detail assets')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    report=dict(stage='preparing',revision=R['REVISION'],saved_assets=[],maps=[],game_run=False,rendered=False,tested=False)
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
        report['saved_assets'].extend(M['install']());record()
        for item in R['manifest']():report['saved_assets'].append(import_mesh(item));record()
        report['stage']='assets_saved';record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET);generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json');before=json.loads(raw);catalog=copy.deepcopy(before)
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash'];bank=catalog['facility_flow']['layout_bank']
        if bank['contract_sha1']!=contract(catalog):raise RuntimeError('Preserve inconsistent layout contract')
        module=next(m for m in catalog['modules'] if m['id']==R['MODULE']);old=copy.deepcopy(module)
        changes=R['apply_module'](module)
        for key in ('lights','runtime_actors','ports','cells','min','max','anchors','props'):
            if module.get(key)!=old.get(key):raise RuntimeError('Preserve unrelated room field '+key)
        # The requested refinement never moves a room part or changes its gameplay flags.
        for a,b in zip(old['parts'],module['parts']):
            if {k:v for k,v in a.items() if k not in ('mesh','incident_detail_revision')}!={k:v for k,v in b.items() if k not in ('mesh','incident_detail_revision')}:raise RuntimeError('Part pose changed')
        bank['contract_sha1']=contract(catalog)
        superseded=set(R['replacements']())|R['old_materials']();serialized=json.dumps(catalog,ensure_ascii=False)
        referenced={path for path in superseded if path in serialized}
        assets=[a for a in generator.get_editor_property('module_assets') if a and (a.get_path_name().split('.')[0] not in superseded or a.get_path_name().split('.')[0] in referenced)]
        known={a.get_path_name() for a in assets}
        for path in module['runtime_assets']:
            a=u.load_asset(path)
            if not a:raise RuntimeError('Missing runtime dependency '+path)
            if a.get_path_name() not in known:known.add(a.get_path_name());assets.append(a)
        generator.modify();generator.set_editor_property('module_assets',assets);generator.set_editor_property('module_catalog_json',serialized)
        save_world(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='production_saved',replacements=changes,existing_light_count=len(old['lights']),poses_preserved=True,blood_and_interactions_preserved=True)
        report['maps'].append(dict(path=TARGET,saved=True));record()
        for target in R['SUBJECTS']:
            world=u.EditorLoadingAndSavingUtils.load_map(target);changed=R['apply_subject'](world);save_world(world,target)
            report['maps'].append(dict(path=target,saved=True,changed=changed));record()
        report['stage']='maps_saved';record();print('TRANSIT_INCIDENT_DETAIL_SAVED',len(report['saved_assets']),'assets;',len(changes),'mesh references;',len(report['maps']),'maps')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)
if __name__=='__main__':main()
