"""Install into existing runtime paths so F6/native and placed references receive the repair."""
import unreal as u, json, shutil, sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
PROJECT=OUT.parents[2]
BASE='/Game/Monsters/HundredEyedSlag'
REV='HundredEyedSlagHeroHandV4_20260930'
LIB=u.EditorAssetLibrary; TOOLS=u.AssetToolsHelpers.get_asset_tools()
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
# A fresh, exclusive background process can dirty loaded clips when their skeleton expands.
# Preserve the unsaved-asset guard whenever this script is used in an interactive editor.
command_line=u.SystemLibrary.get_command_line().lower()
OWN_BACKGROUND_PROCESS='-run=pythonscript' in command_line and '-herohandbackgroundimport' in command_line

def begin(paths):
    if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve(): raise RuntimeError('Wrong project')
    if u.EditorLevelLibrary.get_game_world() is not None: raise RuntimeError('Active PIE preserved; asset installation pending')
    dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    conflict=dirty.intersection(paths)
    if conflict and not OWN_BACKGROUND_PROCESS:
        raise RuntimeError('Unsaved target assets preserved: '+str(sorted(conflict)))
    for path in paths:
        source=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        backup=OUT/'Before'/(path.removeprefix('/Game/')+'.uasset')
        if source.exists() and not backup.exists(): backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,backup)

def save(asset):
    LIB.set_metadata_tag(asset,'HundredEyedSlag.Revision',REV)
    if not LIB.save_loaded_asset(asset,False): raise RuntimeError('Save failed '+asset.get_path_name())

def imp(file,path,options=None):
    folder,name=path.rsplit('/',1)
    task=u.AssetImportTask(); task.filename=str(file); task.destination_name=name; task.destination_path=folder
    task.automated=True; task.save=False; task.replace_existing=True; task.replace_existing_settings=True
    if options is not None: task.options=options
    TOOLS.import_asset_tasks([task])
    asset=u.load_asset(path)
    if asset is None or path not in [p.split('.')[0] for p in task.imported_object_paths]:
        raise RuntimeError('Import did not replace target '+path+'; imported='+str(task.imported_object_paths))
    return asset

def meshes():
    paths=[BASE+'/PolishV2/SK_HundredEyedSlag_V2',BASE+'/V1/SK_HundredEyedSlag_V1']
    lod_path=BASE+'/RuntimeV3/LOD_HundredEyedSlag_RuntimeV3'
    physics_paths=[BASE+'/PolishV2/PA_HundredEyedSlag_V2',BASE+'/V1/PA_HundredEyedSlag_V2']
    skeleton_path=BASE+'/V1/SK_HundredEyedSlag_V1_Skeleton'
    begin(paths+[skeleton_path]+physics_paths)
    skeleton=u.load_asset(skeleton_path)
    lod=u.load_asset(lod_path)
    if skeleton is None or lod is None: raise RuntimeError('Saved RuntimeV3 skeleton/LOD settings required')
    reports=[]
    for path in paths:
        op=u.FbxImportUI(); op.automated_import_should_detect_type=False; op.override_full_name=True
        op.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH; op.import_as_skeletal=True
        op.import_mesh=True; op.import_animations=False; op.import_materials=False; op.import_textures=False
        op.create_physics_asset=False; op.skeleton=skeleton
        data=op.skeletal_mesh_import_data
        data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        data.set_editor_property('use_t0_as_ref_pose',False); data.set_editor_property('update_skeleton_reference_pose',False)
        mesh=imp(OUT/'Delivery/SK_HundredEyedSlag_HeroHandV4.fbx',path,op)
        mesh.set_editor_property('enable_per_poly_collision',False)
        slots=list(mesh.get_editor_property('materials'))
        for slot in slots: slot.material_interface=u.load_asset(BASE+'/PolishV2/Materials/M_HundredEyedSlag_Skin_V2')
        mesh.set_editor_property('materials',slots)
        build=S.get_lod_build_settings(mesh,0); build.set_editor_property('recompute_normals',False)
        build.set_editor_property('recompute_tangents',True); build.set_editor_property('use_mikk_t_space',True)
        S.set_lod_build_settings(mesh,0,build)
        mesh.set_editor_property('lod_settings',lod)
        if not S.regenerate_lod(mesh,3,False,False): raise RuntimeError('Game LOD generation failed '+path)
        physics=u.HundredEyedSlagMonster.build_fitted_physics_asset(mesh)
        if physics is None: raise RuntimeError('Anatomical physics fit failed '+path)
        save(skeleton); save(physics); save(mesh)
        tags=LIB.get_tag_values(path)
        report={'path':mesh.get_path_name(),'lod0_triangles':str(tags.get('Triangles','')),
            'lods':[{'index':i,'vertices':S.get_num_verts(mesh,i),'sections':S.get_num_sections(mesh,i)} for i in range(S.get_lod_count(mesh))],
            'physics':physics.get_path_name(),'skeleton':skeleton.get_path_name(),'saved':True}
        reports.append(report); (OUT/'mesh_installation.json').write_text(json.dumps(reports,indent=2))
        print('V4_GAME_MESH_SAVED '+json.dumps(report))

def animations():
    contracts=json.loads((OUT/'animation_contract.json').read_text())['actions']
    targets=[]
    for c in contracts:
        role=c['name']; targets.append((c,BASE+'/V1/Animations/A_HundredEyedSlag_'+role))
        if role in ('Run','Move','Death'): targets.append((c,BASE+'/PolishV2/Animations/A_HundredEyedSlag_'+role+'_V2'))
    skeleton_path=BASE+'/V1/SK_HundredEyedSlag_V1_Skeleton'
    begin([path for c,path in targets]+[skeleton_path])
    skeleton=u.load_asset(BASE+'/V1/SK_HundredEyedSlag_V1_Skeleton')
    mesh=u.load_asset(BASE+'/PolishV2/SK_HundredEyedSlag_V2')
    sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
    from meshy_animation_units import match_bind_root_scale
    report=[]
    for c,path in targets:
        op=u.FbxImportUI(); op.automated_import_should_detect_type=False; op.override_full_name=True
        op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION; op.import_as_skeletal=True
        op.import_mesh=False; op.import_animations=True; op.import_materials=False; op.import_textures=False; op.skeleton=skeleton
        op.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        op.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
        clip=imp(OUT/'Delivery/Animations'/(c['action']+'.fbx'),path,op)
        units=match_bind_root_scale(clip,mesh); clip.set_preview_skeletal_mesh(mesh); save(clip)
        report.append({'role':c['name'],'path':clip.get_path_name(),'seconds':clip.get_play_length(),'units':units,'saved':True})
        (OUT/'animation_installation.json').write_text(json.dumps(report,indent=2))
        print('V4_ANIMATION_SAVED '+c['name']+' '+path)
    save(skeleton)

def install(phase):
    var='Interchange.FeatureFlags.Import.FBX'; previous=u.SystemLibrary.get_console_variable_int_value(var)
    u.SystemLibrary.execute_console_command(None,var+' 0')
    try: {'meshes':meshes,'animations':animations}[phase]()
    finally: u.SystemLibrary.execute_console_command(None,var+' '+str(previous))
