"""Import the reweighted M27 into new packages without touching the live BP."""
from pathlib import Path
import json
import sys
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/MantisM27/BindingV2')
SOURCE=ROOT/'Delivery'
OWNER='/Game/Monsters/MantisM27'
DEST=OWNER+'/BindingV2'
LIB=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
REPORT=ROOT/'ue_binding_receipt.json'
manifest=json.loads((SOURCE/'motion_manifest.json').read_text(encoding='utf-8'))
report={'name':'螳螂-M27','revision':'BindingV2','assets_saved':False,'blueprint_connected':False,
        'saved':False,'assets':[],'tested':False,'runtime_tested':False,'visual_tested':False,
        'user_review_pending':True,'previous_binding':'ProductionV1 rejected: foot and blade stretching',
        'changes':manifest['binding_changes']}

def receipt():
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')

def save(asset):
    if not asset or not asset.get_path_name().startswith(DEST+'/'):
        raise RuntimeError('BindingV2 save target is absent or outside its revision folder.')
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('Could not save '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']:report['assets'].append(asset.get_path_name())
    receipt()

def options(skeleton=None,animation=False):
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True;opt.import_mesh=not animation;opt.import_animations=animation
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=not animation;opt.skeleton=skeleton
    data=opt.skeletal_mesh_import_data
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('use_t0_as_ref_pose',False)
    data.set_editor_property('update_skeleton_reference_pose',False)
    if animation:
        data=opt.anim_sequence_import_data
        data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('preserve_local_transform',True)
    return opt

def import_file(filename,name,folder,opt):
    task=u.AssetImportTask();task.filename=str(filename);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    task.options=opt;task.factory=u.FbxFactory()
    TOOLS.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset or not task.imported_object_paths:raise RuntimeError('Import did not produce '+folder+'/'+name)
    return asset

def run():
    try:
        if not hasattr(u,'MantisM27Monster'):raise RuntimeError('M27 native authoring class unavailable.')
        material=u.load_asset(OWNER+'/ProductionV1/Materials/M_M27_OriginalPBR')
        if not material:raise RuntimeError('Original M27 PBR material unavailable.')
        mesh=import_file(SOURCE/manifest['mesh_file'],'SK_MantisM27_BindingV2',DEST,options())
        skeleton=mesh.skeleton
        slots=list(mesh.materials)
        for slot in slots:slot.material_interface=material
        mesh.set_editor_property('materials',slots)
        mesh.set_editor_property('enable_per_poly_collision',False)
        editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
        settings=editor.get_lod_build_settings(mesh,0)
        settings.recompute_normals=False;settings.recompute_tangents=True
        settings.use_mikk_t_space=True;settings.use_full_precision_u_vs=True
        editor.set_lod_build_settings(mesh,0,settings)
        policy=u.load_asset(DEST+'/LOD_MantisM27_BindingV2')
        if not policy:
            factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings.static_class())
            policy=TOOLS.create_asset('LOD_MantisM27_BindingV2',DEST,u.SkeletalMeshLODSettings,factory)
        lods=[]
        for fraction,screen in [(1.,1.),(.5,.45),(.2,.2),(.08,.09)]:
            row=u.SkeletalMeshLODGroupSettings();reduction=row.get_editor_property('reduction_settings')
            reduction.set_editor_property('num_of_triangles_percentage',fraction)
            reduction.set_editor_property('base_lod',0)
            reduction.set_editor_property('max_bones_per_vertex',4)
            reduction.set_editor_property('enforce_bone_boundaries',True)
            row.set_editor_property('reduction_settings',reduction)
            row.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));lods.append(row)
        policy.set_editor_property('lod_groups',lods);save(policy)
        mesh.set_editor_property('lod_settings',policy)
        if not editor.regenerate_lod(mesh,4,False,False):raise RuntimeError('M27 distance LOD creation failed.')
        sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/MantisM27')
        from finish_lods import configure
        from finish_contacts import configure_contacts
        configure(mesh,policy);configure_contacts(mesh)
        LIB.set_metadata_tag(mesh,'Source','Original Meshy surface and UV; connected-region BindingV2; fitted arm joints and rigid foot/scythe cores')
        LIB.set_metadata_tag(mesh,'ReviewStatus','BindingV2 saved; user runtime review pending')
        save(mesh.physics_asset);save(skeleton);save(mesh)
        report.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=mesh.physics_asset.get_path_name(),
                      material=material.get_path_name(),lod_count=4,lod_triangle_ratios=[1,.5,.2,.08],
                      blade_sockets_force_animation=True,physics_body_count=15)
        receipt()
        clips={}
        for role,info in manifest['clips'].items():
            clip=import_file(SOURCE/info['file'],'A_M27_'+role+'_BindingV2',DEST+'/Animations',options(skeleton,True))
            clip.set_preview_skeletal_mesh(mesh);clip.set_editor_property('enable_root_motion',False)
            LIB.set_metadata_tag(clip,'SourceRevision','M27 BindingV2; existing timing and component motion fitted to corrected bind pose')
            save(clip);clips[role]={'asset':clip.get_path_name(),'duration_seconds':info['duration_seconds']}
        save(skeleton)
        report.update(assets_saved=True,clips=clips,stage='Rebound mesh, matched skeleton, ten clips, LODs and refitted physics saved; canonical BP connection pending')
        receipt();print('M27_BINDING_V2_ASSETS_SAVED '+str(REPORT),flush=True)
    except Exception as error:
        report['error']=str(error);receipt();raise

if __name__=='__main__':run()
