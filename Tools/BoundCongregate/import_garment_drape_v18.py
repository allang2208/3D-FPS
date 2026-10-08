"""Import the continuous garments and matching corpse, then change the visual asset."""
from pathlib import Path
import unreal as u
import json, hashlib, shutil, subprocess, sys

PROJECT=Path('D:/FPS3D/FPSGAME')
# Later garment cuts reuse this saved import/capture/corpse pipeline.
REVISION=globals().get('BC_GARMENT_REVISION','GarmentDrapeV18')
VERSION=globals().get('BC_GARMENT_VERSION','V18')
OUT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006'/REVISION
BASE='/Game/Monsters/BoundCongregate'
DEST=BASE+'/'+REVISION
SOURCE=globals().get('BC_GARMENT_SOURCE',BASE+'/GarmentContinuityV14/SK_BoundCongregate_SurfaceFitV12_GarmentV14')
NAME='SK_BoundCongregate_'+REVISION
STAGE=globals().get('BC_V18_IMPORT_STAGE','all')
E=u.EditorAssetLibrary
AT=u.AssetToolsHelpers.get_asset_tools()
report={'revision':REVISION,'saved':False,'gameplay_tested':False,'assets':[],
        'source_fbx_sha256':hashlib.sha256((OUT/(NAME+'.fbx')).read_bytes()).hexdigest(),
        'native_changes':True,'preserved':'anatomy, tentacle rig, animations and current Blueprint gameplay tuning'}

if STAGE=='finish':
    report=json.loads((OUT/'delivery.json').read_text(encoding='utf8'))
    if report.get('prepared') is not True:raise RuntimeError('Prepare the candidate before finishing.')

def record():
    (OUT/'delivery.json').write_text(json.dumps(report,indent=2),encoding='utf8')

def save(asset):
    if not asset or not E.save_loaded_asset(asset,False):
        raise RuntimeError('Save failed: '+str(asset))
    path=asset.get_path_name()
    if path not in report['assets']:report['assets'].append(path)
    record()

def duplicate(source,path):
    return u.load_asset(path) or E.duplicate_asset(source.get_path_name(),path)

try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError('PIE is active; preserve the current game.')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) or p in (SOURCE,BASE+'/BP_BoundCongregate') for p in dirty):
        raise RuntimeError('Retain unsaved owned assets.')
    bp=u.load_asset(BASE+'/BP_BoundCongregate')
    cdo=u.get_default_object(bp.generated_class())
    old=cdo.get_editor_property('visual_mesh')
    if old.get_path_name().split('.')[0] not in (SOURCE,DEST+'/'+NAME):
        raise RuntimeError('The active monster visual changed; retain it.')
    report['previous_mesh']=old.get_path_name()
    backup=OUT/'before';backup.mkdir(exist_ok=True)
    bp_file=PROJECT/'Content/Monsters/BoundCongregate/BP_BoundCongregate.uasset'
    if not (backup/bp_file.name).exists():shutil.copy2(bp_file,backup/bp_file.name)
    report['blueprint_backup']=str(backup/bp_file.name)
    folder=OUT/'SoftCorpse/BoundCongregate'
    if STAGE!='finish':
        u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
        u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
        source=u.load_asset(SOURCE)
        skeleton=duplicate(source.skeleton,DEST+'/SKEL_BoundCongregate_Garment'+VERSION)
        # Retain V17 melee on the current V14 skeleton as well as earlier locomotion.
        compatible=list(source.skeleton.get_editor_property('compatible_skeletons'))
        if source.skeleton not in compatible:compatible.append(source.skeleton)
        skeleton.set_editor_property('compatible_skeletons',compatible)
        options=u.FbxImportUI()
        options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        options.import_as_skeletal=options.import_mesh=True
        options.import_animations=options.import_materials=options.import_textures=options.create_physics_asset=False
        options.skeleton=skeleton
        data=options.skeletal_mesh_import_data
        data.convert_scene=data.convert_scene_unit=True
        data.force_front_x_axis=False;data.import_uniform_scale=1
        data.set_editor_property('update_skeleton_reference_pose',False)
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        data.vertex_color_import_option=u.VertexColorImportOption.REPLACE
        task=u.AssetImportTask();task.filename=str(OUT/(NAME+'.fbx'))
        task.destination_path=DEST;task.destination_name=NAME
        task.factory=u.FbxFactory();task.options=options
        task.automated=task.replace_existing=task.replace_existing_settings=True;task.save=False
        AT.import_asset_tasks([task])
        mesh=u.load_asset(DEST+'/'+NAME)
        if not mesh:raise RuntimeError('Skeletal import failed.')
        old_materials={str(slot.get_editor_property('imported_material_slot_name')):
                       slot.get_editor_property('material_interface') for slot in source.get_editor_property('materials')}
        # Blender may suffix reused proxy materials with .001. They are hidden
        # build inputs; normalize only their suffix, retaining the live fabrics.
        for key,material in list(old_materials.items()):
            if '_Proxy' in key:old_materials.setdefault(key.split('_Proxy')[0]+'_Proxy',material)
        slots=list(mesh.get_editor_property('materials'))
        for slot in slots:
            key=str(slot.get_editor_property('imported_material_slot_name'))
            material=old_materials.get(key)
            if not material:raise RuntimeError('Missing existing material '+key)
            slot.set_editor_property('material_interface',material)
        mesh.set_editor_property('materials',slots)
        for field in ('positive_bounds_extension','negative_bounds_extension','physics_asset'):
            mesh.set_editor_property(field,source.get_editor_property(field))
        if not u.BoundCongregate.build_garment_simulation(mesh):
            raise RuntimeError('Garment mapping failed.')
        report['cloth_assets']=[]
        for cloth in mesh.get_editor_property('mesh_clothing_assets'):
            config=next(c for c in cloth.get_editor_property('cloth_configs').values()
                        if c.get_class().get_name()=='ChaosClothConfig')
            # Refuse to activate with the old in-memory builder. The new per-vertex
            # attachment drive and authored hem travel must be serialized together.
            if config.get_editor_property('bUseCCD') or abs(config.get_editor_property('CollisionThickness')-.7)>.001 or abs(config.get_editor_property('Density')-.52)>.001:
                raise RuntimeError('Unexpected loaded garment builder; do not activate the candidate.')
            report['cloth_assets'].append(cloth.get_name())
        E.set_metadata_tag(mesh,'GarmentRevision',REVISION)
        E.set_metadata_tag(mesh,'ClothCollisionRevision','V13-bone-local-capsule-dimensions')
        E.set_metadata_tag(mesh,'GarmentMaterials','Unmodified live source material references; retained weave UV scale and wear masks')
        for asset in (skeleton,mesh):save(asset)
        # New garment topology needs its own complete continuous-death embedding.
        corpse=duplicate(mesh,DEST+'/Corpse/SK_BoundCongregate_Corpse'+VERSION)
        corpse_skeleton=duplicate(skeleton,DEST+'/Corpse/SKEL_BoundCongregate_Corpse'+VERSION)
        corpse_data=u.load_asset(DEST+'/Corpse/DA_BoundCongregate_Corpse'+VERSION)
        if not corpse_data:
            factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
            corpse_data=AT.create_asset('DA_BoundCongregate_Corpse'+VERSION,DEST+'/Corpse',u.M14SoftBodyData,factory)
        folder=OUT/'SoftCorpse/BoundCongregate';folder.mkdir(parents=True,exist_ok=True)
        u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilationFinishAll')
        u.BoundCongregate.prepare_corpse_mesh(corpse)
        if not u.M14SoftBodyData.export_surface(corpse,str(folder/'surface.bin'),[]):
            raise RuntimeError('Corpse surface export failed.')
        for asset in (corpse,corpse_skeleton,corpse_data):save(asset)
        report['prepared']=True
        print('BOUND_CONGREGATE_GARMENT_'+VERSION+'_PREPARED',flush=True)
    else:
        mesh=u.load_asset(DEST+'/'+NAME)
        corpse=u.load_asset(DEST+'/Corpse/SK_BoundCongregate_Corpse'+VERSION)
        corpse_skeleton=u.load_asset(DEST+'/Corpse/SKEL_BoundCongregate_Corpse'+VERSION)
        corpse_data=u.load_asset(DEST+'/Corpse/DA_BoundCongregate_Corpse'+VERSION)
    if STAGE=='all':
        subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',
                        str(PROJECT/'Tools/BoundCongregate/author_soft_corpse.py'),'--garment-'+VERSION.lower()],
                       check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    if STAGE!='prepare':
        if not u.M14SoftBodyData.build_corpse(corpse,corpse_skeleton,corpse_data,
                                           str(folder/'cage.json'),str(folder/'embedding.bin')):
            raise RuntimeError('Corpse binding failed.')
        sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'))
        import corpse_materials
        corpse_materials.DEST=DEST+'/Corpse/Materials'
        saved=set();slots=list(mesh.get_editor_property('materials'))
        for slot in slots:
            slot.set_editor_property('material_interface',corpse_materials.make(slot.get_editor_property('material_interface'),saved))
        corpse.set_editor_property('materials',slots)
        u.M14SoftBodyData.bind_to_living_mesh(mesh,corpse_data)
        for asset in (corpse,corpse_skeleton,corpse_data,mesh):save(asset)
        cdo.set_editor_property('visual_mesh',mesh)
        u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
        report.update(saved=True,mesh=mesh.get_path_name(),corpse=corpse.get_path_name(),blueprint=bp.get_path_name())
        print('BOUND_CONGREGATE_GARMENT_'+VERSION+'_SAVED',flush=True)
except Exception as error:
    report['error']=str(error)
    raise
finally:
    record()
