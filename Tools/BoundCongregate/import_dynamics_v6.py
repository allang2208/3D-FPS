"""Save the surface-bound root lining, passive dynamics mesh and matching corpse."""
from pathlib import Path
import unreal as u,json,subprocess,sys
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006';OUT=ROOT/'TentacleDynamicsV6'
BASE='/Game/Monsters/BoundCongregate';DEST=BASE+'/DynamicsV6'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
report={'saved':False,'revision':'DynamicsV6','assets':[],'gameplay_tested':False}
def record():(OUT/'delivery.json').write_text(json.dumps(report,indent=2),encoding='utf8')
def save(asset):
    if not asset or not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+str(asset))
    if asset.get_path_name() not in report['assets']:report['assets'].append(asset.get_path_name())
    record()
def duplicate(source,path):return u.load_asset(path) or E.duplicate_asset(source.get_path_name(),path)
def main():
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) or p==BASE+'/BP_BoundCongregate' for p in dirty):raise RuntimeError('Unsaved owned assets retained')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
    old=u.load_asset(BASE+'/RigV3/SK_BoundCongregate_RigV3');bp=u.load_asset(BASE+'/BP_BoundCongregate')
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=options.import_mesh=True
    options.import_animations=options.import_materials=options.import_textures=options.create_physics_asset=False
    options.skeleton=old.skeleton
    d=options.skeletal_mesh_import_data;d.convert_scene=d.convert_scene_unit=True;d.force_front_x_axis=False;d.import_uniform_scale=1
    d.set_editor_property('update_skeleton_reference_pose',True)
    d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=str(OUT/'SK_BoundCongregate_DynamicsV6.fbx');task.destination_path=DEST
    task.destination_name='SK_BoundCongregate_DynamicsV6';task.factory=u.FbxFactory();task.options=options
    task.automated=task.replace_existing=task.replace_existing_settings=True;task.save=False
    AT.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+task.destination_name)
    if not mesh:raise RuntimeError('Skeletal import failed')
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        key=str(slot.get_editor_property('imported_material_slot_name')).split('_Proxy')[0]
        if key.startswith('BC_Sleeve'):key='BC_RagFabric'
        if key=='BC_AttackTentacle':key='BC_Flesh'
        material=u.load_asset(BASE+'/Materials/M_'+key)
        if not material:raise RuntimeError('Missing material '+key)
        slot.set_editor_property('material_interface',material)
    mesh.set_editor_property('materials',slots)
    # Reference bounds are too small for an unfurled organ; retain visibility
    # without enabling per-frame bounds recomputation for the whole character.
    mesh.set_editor_property('positive_bounds_extension',u.Vector(220,420,300))
    mesh.set_editor_property('negative_bounds_extension',u.Vector(220,420,0))
    physics=duplicate(old.get_editor_property('physics_asset'),DEST+'/PA_BoundCongregate_DynamicsV6')
    if not u.BoundCongregate.build_surface_physics(mesh,physics):raise RuntimeError('Physics build failed')
    if not u.BoundCongregate.build_garment_simulation(mesh):raise RuntimeError('Cloth mapping failed')
    E.set_metadata_tag(mesh,'TentacleIsolation','V6-supported-root-lining-inertial-chain')
    for asset in [physics,mesh.skeleton,mesh]:save(asset)
    corpse=duplicate(mesh,DEST+'/Corpse/SK_BoundCongregate_CorpseV6')
    skeleton=duplicate(mesh.skeleton,DEST+'/Corpse/SKEL_BoundCongregate_CorpseV6')
    data=u.load_asset(DEST+'/Corpse/DA_BoundCongregate_CorpseV6')
    if not data:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
        data=AT.create_asset('DA_BoundCongregate_CorpseV6',DEST+'/Corpse',u.M14SoftBodyData,factory)
    root=OUT/'SoftCorpse/BoundCongregate';root.mkdir(parents=True,exist_ok=True)
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilationFinishAll')
    u.BoundCongregate.prepare_corpse_mesh(corpse)
    if not u.M14SoftBodyData.export_surface(corpse,str(root/'surface.bin'),[]):raise RuntimeError('Surface export failed')
    subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',str(PROJECT/'Tools/BoundCongregate/author_soft_corpse.py'),'--dynamics-v6'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if not u.M14SoftBodyData.build_corpse(corpse,skeleton,data,str(root/'cage.json'),str(root/'embedding.bin')):raise RuntimeError('Corpse build failed')
    sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'));import corpse_materials
    corpse_materials.DEST=DEST+'/Corpse/Materials';saved=set();slots=list(mesh.get_editor_property('materials'))
    for slot in slots:slot.set_editor_property('material_interface',corpse_materials.make(slot.get_editor_property('material_interface'),saved))
    corpse.set_editor_property('materials',slots);u.M14SoftBodyData.bind_to_living_mesh(mesh,data)
    for asset in [corpse,skeleton,data,mesh]:save(asset)
    cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('visual_mesh',mesh)
    cdo.set_editor_property('mesh_yaw',u.BoundCongregate.reference_facing_yaw(mesh))
    cdo.set_editor_property('tentacle_windup_seconds',1.1)
    # Keep the accepted three-times release duration; dynamics do not retime attacks.
    cdo.set_editor_property('tentacle_strike_seconds',.62/3.)
    # Preserve movement, bite, hit, damage, capture and pulling references.
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(saved=True,mesh=mesh.get_path_name(),blueprint=bp.get_path_name(),corpse=corpse.get_path_name())
    record();print('BOUND_CONGREGATE_DYNAMICS_V6_SAVED',flush=True)
try:main()
except Exception as error:report['error']=str(error);record();raise
