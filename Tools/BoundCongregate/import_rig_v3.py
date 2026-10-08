"""Save repaired mesh, four cloth islands, seven clips and matching soft corpse."""
from pathlib import Path
import unreal as u, json, subprocess, sys
PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006';OUT=ROOT/'RigRepairV3'
BASE='/Game/Monsters/BoundCongregate';DEST=BASE+'/RigV3'
E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
report=dict(complete=False,saved=[],revision='RigV3')
def record():(OUT/'ue_delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(a):
    if not a or not E.save_loaded_asset(a,False):raise RuntimeError('Save failed '+str(a))
    if a.get_path_name() not in report['saved']:report['saved'].append(a.get_path_name())
    record()
def imported(name,file,folder,skeleton,animation=False):
    o=u.FbxImportUI();o.automated_import_should_detect_type=False
    o.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_as_skeletal=True;o.import_mesh=not animation;o.import_animations=animation
    o.import_materials=o.import_textures=o.create_physics_asset=False;o.skeleton=skeleton
    d=o.anim_sequence_import_data if animation else o.skeletal_mesh_import_data
    d.convert_scene=d.convert_scene_unit=True;d.force_front_x_axis=False;d.import_uniform_scale=1
    if animation:
        d.set_editor_property('use_default_sample_rate',False)
        d.set_editor_property('custom_sample_rate',30)
        d.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    else:
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.factory=u.FbxFactory();task.options=o;task.automated=task.replace_existing=task.replace_existing_settings=True;task.save=False
    AT.import_asset_tasks([task]);a=u.load_asset(folder+'/'+name)
    if not a:raise RuntimeError('Import failed '+name)
    return a
def duplicate(source,path):return u.load_asset(path) or E.duplicate_asset(source.get_path_name(),path)
def main():
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('PIE active')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if any(p.startswith(DEST) or p==BASE+'/BP_BoundCongregate' for p in dirty):raise RuntimeError('Unsaved owned packages retained')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
    old=u.load_asset(BASE+'/SK_BoundCongregate');bp=u.load_asset(BASE+'/BP_BoundCongregate')
    mesh=u.load_asset(DEST+'/SK_BoundCongregate_RigV3')
    if not mesh or E.get_metadata_tag(mesh,'RigRepair')!='V3':
        mesh=imported('SK_BoundCongregate_RigV3',OUT/'SK_BoundCongregate_RigV3.fbx',DEST,old.skeleton)
        slots=list(mesh.get_editor_property('materials'))
        for slot in slots:
            key=str(slot.get_editor_property('imported_material_slot_name')).split('_Proxy')[0]
            if key.startswith('BC_Sleeve'):key='BC_RagFabric'
            mat=u.load_asset(BASE+'/Materials/M_'+key)
            if not mat:raise RuntimeError('Missing material '+key)
            slot.set_editor_property('material_interface',mat)
        mesh.set_editor_property('materials',slots)
        physics=duplicate(old.get_editor_property('physics_asset'),DEST+'/PA_BoundCongregate_RigV3')
        if not u.BoundCongregate.build_surface_physics(mesh,physics):raise RuntimeError('Physics build failed')
        if not u.BoundCongregate.build_garment_simulation(mesh):raise RuntimeError('Cloth build failed')
        E.set_metadata_tag(mesh,'RigRepair','V3')
        E.set_metadata_tag(mesh,'GarmentBindingVersion','V3-linear-backstop')
        save(physics);save(mesh);save(mesh.skeleton)
    elif E.get_metadata_tag(mesh,'GarmentBindingVersion')!='V3-linear-backstop':
        if not u.BoundCongregate.build_garment_simulation(mesh):raise RuntimeError('Cloth mapping update failed')
        E.set_metadata_tag(mesh,'GarmentBindingVersion','V3-linear-backstop');save(mesh)
    clips={};manifest=json.loads((OUT/'motion_manifest.json').read_text())
    for role,data in manifest['clips'].items():
        clip=imported(data['name'],data['file'],DEST+'/Animations',mesh.skeleton,True)
        clip.set_editor_property('loop',data['loop']);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        # This Blender bind skeleton carries centimetre conversion on the root.
        # Preserve it explicitly instead of taking the unit-scale animated root.
        clip.set_editor_property('root_motion_root_lock',u.RootMotionRootLock.REF_POSE)
        clip.set_preview_skeletal_mesh(mesh);save(clip);clips[role]=clip
    save(mesh.skeleton)
    corpse=duplicate(mesh,DEST+'/Corpse/SK_BoundCongregate_CorpseV3')
    skeleton=duplicate(mesh.skeleton,DEST+'/Corpse/SKEL_BoundCongregate_CorpseV3')
    data=u.load_asset(DEST+'/Corpse/DA_BoundCongregate_CorpseV3')
    if not data:
        factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
        data=AT.create_asset('DA_BoundCongregate_CorpseV3',DEST+'/Corpse',u.M14SoftBodyData,factory)
    corpse_root=OUT/'SoftCorpse/BoundCongregate';corpse_root.mkdir(parents=True,exist_ok=True)
    if data.get_editor_property('corpse_mesh')!=corpse:
        u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilationFinishAll')
        u.BoundCongregate.prepare_corpse_mesh(corpse)
        if not u.M14SoftBodyData.export_surface(corpse,str(corpse_root/'surface.bin'),[]):raise RuntimeError('Corpse surface export failed')
        subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',str(PROJECT/'Tools/BoundCongregate/author_soft_corpse.py'),'--rig-v3'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if not u.M14SoftBodyData.build_corpse(corpse,skeleton,data,str(corpse_root/'cage.json'),str(corpse_root/'embedding.bin')):raise RuntimeError('Corpse binding failed')
    sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'));import corpse_materials
    corpse_materials.DEST=DEST+'/Corpse/Materials';saved=set();slots=list(mesh.get_editor_property('materials'))
    for slot in slots:slot.set_editor_property('material_interface',corpse_materials.make(slot.get_editor_property('material_interface'),saved))
    corpse.set_editor_property('materials',slots);u.M14SoftBodyData.bind_to_living_mesh(mesh,data)
    for a in (corpse,skeleton,data,mesh):save(a)
    cdo=u.get_default_object(bp.generated_class());cdo.set_editor_property('visual_mesh',mesh);cdo.set_editor_property('mesh_yaw',u.BoundCongregate.reference_facing_yaw(mesh))
    for prop,role in [('idle_clip','Idle'),('move_clip','Walk'),('turn_left_clip','TurnLeft'),('turn_right_clip','TurnRight'),('bite_clip','Bite'),('hit_clip','Hit'),('death_clip','Death')]:cdo.set_editor_property(prop,clips[role])
    cdo.set_editor_property('animation_walk_speed',manifest['walk_speed_cm']);u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(complete=True,mesh=mesh.get_path_name(),blueprint=bp.get_path_name(),corpse=corpse.get_path_name(),clips={r:c.get_path_name() for r,c in clips.items()},cloth_islands=4)
    record();print('BOUND_CONGREGATE_RIG_V3_SAVED',flush=True)
try:main()
except Exception as error:report['error']=str(error);record();raise
