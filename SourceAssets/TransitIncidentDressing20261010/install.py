"""Import and save the second hall's authored incident dressing. No game/preview run."""
from pathlib import Path
from datetime import datetime
import copy,json,hashlib,runpy,shutil,traceback,re,itertools
import unreal as u
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1]
FLOW=PROJECT/'SourceAssets/DungeonFacilityFlow20261007';TARGET='/Game/GameMaps/L_Dungeon_Randomized'
R=runpy.run_path(str(ROOT/'recipe.py'));M=runpy.run_path(str(ROOT/'materials.py'))
save_world=runpy.run_path(str(PROJECT/'SourceAssets/ReceptionCoverage20261009/install.py'))['save']
light_state=runpy.run_path(str(PROJECT/'SourceAssets/TransitFinish20261010/install.py'))['original_lights']
E=u.EditorAssetLibrary;SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)

def import_mesh(item):
    path=item['mesh'];mesh=M['owned'](path)
    if mesh:
        if E.get_metadata_tag(mesh,'TransitIncident.Source')!=item['sha256']:raise RuntimeError('Preserve differing source '+path)
        return path
    task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path,task.destination_name=path.rsplit('/',1)
    task.automated=True;task.save=False;task.replace_existing=False;task.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_as_skeletal=False
    opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    data=opt.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
    data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.build_nanite=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;task.options=opt
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Import failed '+path)
    for i,slot in enumerate(mesh.static_materials):
        name=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][name])
        if not material:raise RuntimeError('Missing material '+name)
        mesh.set_material(i,material)
    build=SM.get_lod_build_settings(mesh,0);build.use_full_precision_u_vs=True;build.use_high_precision_tangent_basis=True;build.recompute_tangents=True
    SM.set_lod_build_settings(mesh,0,build)
    mesh.get_editor_property('body_setup').set_editor_property('collision_trace_flag',u.CollisionTraceFlag.CTF_USE_DEFAULT)
    E.set_metadata_tag(mesh,'TransitIncident.Source',item['sha256']);M['save'](mesh)
    return path

def prepare_support():
    rows=R['placements']();support=[]
    for row in rows:
        if 'settle_floor_cm' not in row:continue
        mesh=u.load_asset(row['mesh'])
        if not mesh:raise RuntimeError('Missing reused scene prop '+row['mesh'])
        b=mesh.get_bounds();rot=u.Rotator(pitch=row['pitch'],yaw=row['yaw'],roll=row['roll'])
        t=u.Transform(location=u.Vector(),rotation=rot,scale=u.Vector(1,1,1))
        corners=[u.MathLibrary.transform_location(t,u.Vector(b.origin.x+sx*b.box_extent.x,b.origin.y+sy*b.box_extent.y,b.origin.z+sz*b.box_extent.z)) for sx,sy,sz in itertools.product((-1,1),repeat=3)]
        row['position'][2]=round(row.pop('settle_floor_cm')-min(v.z for v in corners)+.12,5)
        support.append(dict(id=row['id'],mesh=row['mesh'],position=row['position'],rotation=[rot.pitch,rot.yaw,rot.roll]))
    (ROOT/'placements.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
    return support

def main():
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
    ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    if ed.get_game_world():raise RuntimeError('Preserve active gameplay')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
    if any(p.get_name().startswith(R['BASE']) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved incident assets')
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
        report['source_prop_support']=prepare_support();report['stage']='assets_saved';record()
        world=u.EditorLoadingAndSavingUtils.load_map(TARGET)
        generators=u.GameplayStatics.get_all_actors_of_class(world,u.AuthoredDungeonGenerator)
        if len(generators)!=1:raise RuntimeError('Expected one production generator')
        generator=generators[0];raw=generator.get_editor_property('module_catalog_json')
        (backup/'actual-catalog-before.json').write_text(raw,encoding='utf8');before=json.loads(raw);catalog=copy.deepcopy(before)
        contract=runpy.run_path(str(FLOW/'restore_entry_recipe.py'))['contract_hash'];bank=catalog['facility_flow']['layout_bank']
        if bank['contract_sha1']!=contract(catalog):raise RuntimeError('Preserve inconsistent layout contract')
        module=next(m for m in catalog['modules'] if m['id']==R['MODULE']);old=copy.deepcopy(module);R['apply_module'](module)
        # Narrow merge preconditions protect parallel edits and the accepted light setup.
        for key in ('lights','ports','cells','min','max','anchors','props'):
            if module.get(key)!=old.get(key):raise RuntimeError('Unrelated room field changed '+key)
        for key in ('parts','runtime_actors'):
            if [p for p in module[key] if not R['added'](p)]!=[p for p in old[key] if not R['added'](p)]:raise RuntimeError('Unrelated room content changed '+key)
        if [m for m in catalog['modules'] if m['id']!=R['MODULE']]!=[m for m in before['modules'] if m['id']!=R['MODULE']]:raise RuntimeError('Other rooms changed')
        bank['contract_sha1']=contract(catalog)
        assets=[a for a in generator.get_editor_property('module_assets') if a];known={a.get_path_name() for a in assets}
        for path in module['runtime_assets']:
            a=u.load_asset(path)
            if not a:raise RuntimeError('Missing runtime dependency '+path)
            if a.get_path_name() not in known:known.add(a.get_path_name());assets.append(a)
        generator.modify();generator.set_editor_property('module_assets',assets);generator.set_editor_property('module_catalog_json',json.dumps(catalog,ensure_ascii=False))
        save_world(world,TARGET)
        (FLOW/'Config/catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf8')
        (FLOW/'Config/layout-bank-v1.json').write_text(json.dumps(bank,ensure_ascii=False,separators=(',',':')),encoding='utf8')
        report.update(stage='production_saved',light_count_preserved=len(old['lights']),other_modules_preserved=True,
            layout_entries_preserved=bank['entries']==before['facility_flow']['layout_bank']['entries'],
            added_parts=len(R['settled_placements']()),blood_decals=len(R['blood_marks']()))
        report['maps'].append(dict(path=TARGET,saved=True));record()
        for target in R['SUBJECTS']:
            world=u.EditorLoadingAndSavingUtils.load_map(target);lights=light_state(world);changes=R['apply_subject'](world)
            if light_state(world)!=lights:raise RuntimeError('Established lights changed')
            save_world(world,target);report['maps'].append(dict(path=target,saved=True,changes=changes));record()
        report['stage']='maps_saved';record();print('TRANSIT_INCIDENT_SAVED',len(report['saved_assets']),'assets;',len(report['maps']),'maps;',report['added_parts'],'parts;',report['blood_decals'],'blood decals')
    except Exception:
        report['error']=traceback.format_exc();record();raise
    finally:
        if previous and '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():u.EditorLoadingAndSavingUtils.load_map(previous)
if __name__=='__main__':main()
