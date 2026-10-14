"""Import derived hall details and save scoped map changes without running gameplay."""
from pathlib import Path
from datetime import datetime
import copy,hashlib,json,runpy,shutil,traceback,re
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007'
R=runpy.run_path(str(ROOT/'recipe.py'));G=runpy.run_path(str(R['GROUND']))
TARGET='/Game/GameMaps/L_Dungeon_Randomized'
PREV=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionGroundLighting20261009/install.py'))
save=PREV['save'];old_lights=PREV['old_lights']
E=u.EditorAssetLibrary;SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

def import_mesh(item):
    path=item['mesh'];mesh=u.load_asset(path) if E.does_asset_exist(path) else None
    replace=False
    if mesh and E.get_metadata_tag(mesh,'ReceptionFinish.Source')!=item['sha256']:
        if item.get('previous_sha256') and E.get_metadata_tag(mesh,'ReceptionFinish.Source')==item['previous_sha256']:
            replace=True
        else:raise RuntimeError('Preserve differing derived asset '+path)
    if not mesh or replace:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path,task.destination_name=path.rsplit('/',1)
        task.automated=True;task.save=False;task.replace_existing=replace;task.replace_existing_settings=replace;task.factory=u.FbxFactory()
        opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
        opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.build_nanite=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Import failed '+path)
    mesh.modify()
    for i,slot in enumerate(mesh.static_materials):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name))
        material=u.load_asset(item['materials'][name])
        if not material:raise RuntimeError('Missing reused material '+name)
        mesh.set_material(i,material)
    build=SM.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;build.use_high_precision_tangent_basis=True;build.recompute_tangents=True
    SM.set_lod_build_settings(mesh,0,build)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
    settings=mesh.get_editor_property('nanite_settings').copy();settings.enabled=True;settings.explicit_tangents=True
    settings.generate_fallback=u.NaniteGenerateFallback.ENABLED;settings.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
    settings.fallback_percent_triangles=1.;settings.fallback_relative_error=0.
    mesh.set_editor_property('nanite_settings',settings)
    if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Mesh build failed '+path)
    E.set_metadata_tag(mesh,'ReceptionFinish.Source',item['sha256'])
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Asset save failed '+path)
    return path

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    previous=ed.get_editor_world().get_path_name().split('.')[0] if ed.get_editor_world() else None
    report=dict(stage='preparing',revision=R['REVISION'],maps=[],saved_assets=[],runtime_tested=False,rendered=False)
    def record():(ROOT/'Receipts/install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    backup=ROOT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
    for target in (TARGET,*G['SUBJECTS']):
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
        for item in R['manifest']():
            report['saved_assets'].append(import_mesh(item));record()
        report['stage']='assets_saved';record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Missing production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json')
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8')
        before=json.loads(raw);out=copy.deepcopy(before)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash']
        if out['facility_flow']['layout_bank']['contract_sha1']!=contract(out):raise RuntimeError('Preserve inconsistent layout bank')
        module=next(m for m in out['modules'] if m['id']==R['MODULE'])
        original_lights=[copy.deepcopy(p) for p in module['lights'] if not G['is_added'](p)]
        R['apply_module'](module)
        if [p for p in module['lights'] if not G['is_added'](p)]!=original_lights:raise RuntimeError('Protected original lamps changed')
        if [m for m in out['modules'] if m['id']!=R['MODULE']]!=[m for m in before['modules'] if m['id']!=R['MODULE']]:raise RuntimeError('Other rooms changed')
        bank=out['facility_flow']['layout_bank'];bank['contract_sha1']=contract(out)
        assets=list(generator.get_editor_property('module_assets'));known={a.get_path_name() for a in assets if a}
        for path in module['runtime_assets']:
            a=u.load_asset(path)
            if not a:raise RuntimeError('Missing runtime asset '+path)
            if a.get_path_name() not in known:known.add(a.get_path_name());assets.append(a)
        generator.modify();generator.set_editor_property('module_assets',assets)
        generator.set_editor_property('module_catalog_json',json.dumps(out,ensure_ascii=False))
        save(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='production_saved',protected_lamps=len(original_lights),original_lights_preserved=True,
            protected_light_sha256=hashlib.sha256(json.dumps(original_lights,sort_keys=True).encode()).hexdigest(),
            other_rooms_preserved=True,layout_entries_preserved=bank['entries']==before['facility_flow']['layout_bank']['entries'],
            bank_contract_sha1=bank['contract_sha1'],gallery_lamps_aligned=6,main_door_lights_added=1,
            vent_body_position_cm=[-540,-1581,412],vent_lid_position_cm=[-598.5,-1581,280])
        report['maps'].append(dict(path=TARGET,saved=True));record()
        for target in G['SUBJECTS']:
            world=u.EditorLoadingAndSavingUtils.load_map(target);before_lights=old_lights(world)
            changes=R['apply_subject'](world)
            if old_lights(world)!=before_lights:raise RuntimeError('Protected subject lamps changed')
            save(world,target);report['maps'].append(dict(path=target,saved=True,changes=changes));record()
        report['stage']='maps_saved';record()
        print('RECEPTION_FINISH_SAVED',len(report['maps']),'maps;',len(report['saved_assets']),'derived meshes; protected lamps',len(original_lights))
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)

if __name__=='__main__':main()
