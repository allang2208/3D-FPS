"""Install the intact staff wall finish into the four existing sample maps."""
import hashlib,json,re,shutil
from pathlib import Path
from datetime import datetime
import unreal as u

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1];OUT=ROOT/'IntactTilesV4'
BASE='/Game/Dungeons/StaffLiving20261002/IntactTilesV4'
CFG=json.loads((ROOT/'Config/room.json').read_text('utf8'))
MAN=json.loads((OUT/'Authored/manifest.json').read_text('utf8'))
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
RP=OUT/'install.json'
report=json.loads(RP.read_text('utf8')) if RP.exists() else dict(meshes={},maps={},backups=[])
report.update(wall_finish='intact',layout_revision=4,tests_run=False,game_run=False,rendered=False,editor_opened=False)
def record():RP.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
meshes={}
for item in MAN['objects']:
    path=item['asset'];digest=hashlib.sha256(Path(item['fbx']).read_bytes()).hexdigest()
    mesh=u.load_asset(path)
    if mesh and report['meshes'].get(item['name'],{}).get('source_sha256')!=digest:
        raise RuntimeError('Preserve different existing wall asset '+path)
    if not mesh:
        task=u.AssetImportTask();task.filename=item['fbx'];task.destination_path=BASE+'/Meshes';task.destination_name=item['name']
        task.automated=True;task.replace_existing=False;task.save=False
        opts=u.FbxImportUI();opts.import_mesh=True;opts.import_materials=False;opts.import_textures=False;opts.import_as_skeletal=False
        opts.automated_import_should_detect_type=False;opts.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        data=opts.static_mesh_import_data;data.combine_meshes=True;data.convert_scene=True;data.convert_scene_unit=True
        data.transform_vertex_to_absolute=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task.options=opts;task.factory=u.FbxFactory();AT.import_asset_tasks([task]);mesh=u.load_asset(path)
        if not mesh:raise RuntimeError('Tile mesh import failed '+path)
        for index,slot in enumerate(mesh.get_editor_property('static_materials')):
            key=re.sub(r'[._][0-9]{3}$','',str(slot.material_slot_name));material=u.load_asset(item['materials'][key])
            if not material:raise RuntimeError('Missing existing glaze material '+item['materials'][key])
            mesh.set_material(index,material)
        build=sub.get_lod_build_settings(mesh,0);build.set_editor_property('use_full_precision_u_vs',True)
        build.set_editor_property('use_high_precision_tangent_basis',True);build.set_editor_property('recompute_tangents',True)
        sub.set_lod_build_settings(mesh,0,build)
        nanite=mesh.get_editor_property('nanite_settings').copy();nanite.enabled=True;nanite.explicit_tangents=True
        nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES
        nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0;mesh.set_editor_property('nanite_settings',nanite)
        if not u.PlazaInstanceTools.build_nanite_data(mesh):raise RuntimeError('Tile production build failed '+path)
        if not E.save_loaded_asset(mesh,False):raise RuntimeError('Tile mesh save failed '+path)
    report['meshes'][item['name']]=dict(path=path,source_sha256=digest,triangles=item['triangles'])
    meshes[item['room_id']]=mesh;record()
report['stage']='assets_saved';record()

AA=u.get_editor_subsystem(u.EditorActorSubsystem) or u.new_object(u.EditorActorSubsystem)
backup=OUT/'Backups'/datetime.now().strftime('%Y%m%d-%H%M%S');backup.mkdir(parents=True,exist_ok=True)
targets=[(CFG['maps'][r['id']],[r['id']],False) for r in CFG['rooms']]
targets.append((CFG['sample_map'],[r['id'] for r in CFG['rooms']],True))
for target,rids,combined in targets:
    if report['maps'].get(target,{}).get('layout_revision')==4:continue
    disk=PROJECT/'Content'/(target.removeprefix('/Game/')+'.umap');dst=backup/disk.name
    shutil.copy2(disk,dst);report['backups'].append(dict(original=str(disk),backup=str(dst),sha256=hashlib.sha256(dst.read_bytes()).hexdigest()));record()
    world=u.EditorLoadingAndSavingUtils.load_map(target)
    if not world:raise RuntimeError('Cannot load staff sample '+target)
    labels={'StaffSubject_'+rid+'_Tiles':meshes[rid] for rid in rids}
    if combined:
        for x in (16,48):labels['StaffSubject_Link_'+str(x)+'_Tiles']=meshes['Link']
    changed=[]
    for actor in AA.get_all_level_actors():
        label=actor.get_actor_label()
        if label not in labels or 'StaffLiving.Subject' not in [str(t) for t in actor.tags]:continue
        component=actor.get_component_by_class(u.StaticMeshComponent)
        if not component:raise RuntimeError('Owned tile component missing '+label)
        component.set_static_mesh(labels[label]);changed.append(label)
    missing=set(labels)-set(changed)
    if missing:raise RuntimeError('Cannot bind tile replacements: '+str(missing))
    if not u.EditorLoadingAndSavingUtils.save_map(world,target):raise RuntimeError('Map save failed '+target)
    report['maps'][target]=dict(stage='map_saved',layout_revision=4,changed_components=changed);record()
    u.log('STAFF_INTACT_TILES_MAP_SAVED '+target)

draft=json.loads((ROOT/'Config/modules-draft.json').read_text('utf8'))
remap={r['replaces']:r['asset'] for r in MAN['objects']}
for module in draft['modules']:
    for part in module['parts']:
        name=part['mesh'].rsplit('/',1)[-1]
        if name in remap:part['mesh']=remap[name]
    module['wall_finish']='intact'
CFG.update(wall_finish='intact',layout_revision=4,revision='staff_living_intact_tiles_v4_20261002')
for room in CFG['rooms']:room['wall_finish']='intact'
for name,data in [('room.json',CFG),('modules-draft.json',draft)]:
    target=ROOT/'Config'/name;shutil.copy2(target,backup/name)
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
report.update(stage='samples_saved',console_command='open '+CFG['sample_map']);record()
u.log('STAFF_INTACT_TILES_DELIVERY_SAVED')
