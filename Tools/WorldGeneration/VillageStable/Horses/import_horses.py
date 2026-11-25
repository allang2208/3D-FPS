"""Import one horse skin, its original PBR maps and the shared animation library."""
import hashlib
import json
from pathlib import Path
import unreal as ue
from stable_actors import ROOT

DEST=ROOT+'/Horses'
ART=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageStable/HorsesR7/Exchange'
LIB=ue.EditorAssetLibrary
AT=ue.AssetToolsHelpers.get_asset_tools()
MAT=ue.MaterialEditingLibrary


def save(asset):
    if not LIB.save_loaded_asset(asset,False):
        raise RuntimeError('Failed to save '+asset.get_path_name())


def import_file(path,name,folder=DEST,options=None):
    address=folder+'/'+name
    old=ue.load_asset(address) if LIB.does_asset_exist(address) else None
    sha=hashlib.sha256(path.read_bytes()).hexdigest()
    if old and LIB.get_metadata_tag(old,'StableHorseSource')==sha:
        return old
    task=ue.AssetImportTask()
    task.filename=str(path)
    task.destination_path=folder
    task.destination_name=name
    task.automated=True
    task.replace_existing=True
    task.save=False
    if options is not None:
        task.options=options
        task.factory=ue.FbxFactory()
    AT.import_asset_tasks([task])
    obj=ue.load_asset(address)
    if not obj or not task.imported_object_paths:
        raise RuntimeError('Could not import '+address)
    LIB.set_metadata_tag(obj,'StableHorseSource',sha)
    return obj


def finish_material():
    folder=DEST+'/Surfaces'
    sources=[('BaseColor','png',ue.TextureCompressionSettings.TC_DEFAULT),
             ('Normal','png',ue.TextureCompressionSettings.TC_NORMALMAP),
             ('MetalRough','jpg',ue.TextureCompressionSettings.TC_MASKS)]
    textures={}
    for role,ext,compression in sources:
        name='Warhorse_'+role
        tex=import_file(ART/(name+'.'+ext),'T_'+name,folder)
        tex.set_editor_property('compression_settings',compression)
        tex.set_editor_property('srgb',role=='BaseColor')
        if role=='Normal':
            tex.set_editor_property('flip_green_channel',True)
        save(tex)
        textures[role]=tex
    name='M_StableWarhorse'
    path=folder+'/'+name
    mat=ue.load_asset(path) if LIB.does_asset_exist(path) else AT.create_asset(name,folder,ue.Material,ue.MaterialFactoryNew())
    MAT.delete_all_material_expressions(mat)
    MAT.set_base_material_usage(mat,ue.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
    mat.set_editor_property('two_sided',True)
    samples={}
    for role,tex in textures.items():
        node=MAT.create_material_expression(mat,ue.MaterialExpressionTextureSample)
        node.set_editor_property('texture',tex)
        samples[role]=node
    for role,channel,prop in [('BaseColor','RGB','MP_BASE_COLOR'),('Normal','RGB','MP_NORMAL'),
                              ('MetalRough','G','MP_ROUGHNESS'),('MetalRough','B','MP_METALLIC')]:
        if not MAT.connect_material_property(samples[role],channel,getattr(ue.MaterialProperty,prop)):
            raise RuntimeError('Unbound horse material output '+prop)
    MAT.layout_material_expressions(mat)
    errors=MAT.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    stats=MAT.get_statistics(mat)
    if stats.num_pixel_texture_samples < 3:
        raise RuntimeError('Horse material did not compile all three PBR samples')
    save(mat)
    return mat


def fbx_options(skeleton=None):
    o=ue.FbxImportUI()
    o.automated_import_should_detect_type=False
    anim=skeleton is not None
    o.mesh_type_to_import=ue.FBXImportType.FBXIT_ANIMATION if anim else ue.FBXImportType.FBXIT_SKELETAL_MESH
    o.import_as_skeletal=True
    o.import_mesh=not anim
    o.import_animations=anim
    o.import_materials=False
    o.import_textures=False
    o.create_physics_asset=not anim
    data=o.anim_sequence_import_data if anim else o.skeletal_mesh_import_data
    data.convert_scene=True
    data.convert_scene_unit=True
    if anim:
        o.skeleton=skeleton
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',ue.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('preserve_local_transform',True)
    else:
        data.set_editor_property('use_t0_as_ref_pose',False)
        data.set_editor_property('normal_import_method',ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS)
    return o


def match_root_units(clip,mesh):
    # Legacy FBX animation-only import can omit the Armature's metres-to-cm transform.
    root='root'
    local=ue.AnimPoseSpaces.LOCAL
    opts=ue.AnimPoseEvaluationOptions()
    opts.optional_skeletal_mesh=mesh
    opts.set_editor_property('evaluation_type',ue.AnimDataEvalType.SOURCE)
    def root_at(time):
        pose=ue.AnimPoseExtensions.get_anim_pose_at_time(clip,time,opts)
        return ue.AnimPoseExtensions.get_bone_pose(pose,root,local)
    ref=ue.AnimPoseExtensions.get_bone_pose(mesh.skeleton.get_reference_pose(),root,local)
    factor=ref.scale3d/root_at(0.).scale3d
    if max(abs(k-1) for k in factor.to_tuple())<.001:
        return
    count=clip.get_editor_property('data_model_interface').get_number_of_keys()
    keys=[root_at(clip.get_play_length()*i/max(1,count-1)) for i in range(count)]
    controller=clip.get_editor_property('controller')
    controller.open_bracket('Match horse root to FBX bind units',False)
    try:
        if not controller.set_bone_track_keys(root,[k.translation*factor for k in keys],
                                               [k.rotation for k in keys],[k.scale3d*factor for k in keys],False):
            raise RuntimeError('Could not apply horse root units: '+clip.get_name())
    finally:
        controller.close_bracket(False)


def author():
    name='SK_StableWarhorse'
    mesh=import_file(ART/(name+'.fbx'),name,options=fbx_options())
    material=finish_material()
    slots=list(mesh.materials)
    if len(slots)!=1:
        raise RuntimeError('Expected the single Warhorse atlas')
    slots[0].material_interface=material
    mesh.materials=slots
    skeleton=mesh.skeleton
    save(mesh)
    save(skeleton)
    if not mesh.physics_asset:
        raise RuntimeError('Missing horse physics asset')
    save(mesh.physics_asset)
    clips=json.loads((ART/'clips.json').read_text('utf-8'))
    for name,meta in clips.items():
        if name == 'A_Warhorse_Canter' and LIB.does_asset_exist(DEST+'/Animations/'+name):
            existing = LIB.load_asset(DEST+'/Animations/'+name)
            if LIB.get_metadata_tag(existing, 'StableCanterFit') == 'CoastalGallopR14':
                continue
        clip=import_file(ART/(name+'.fbx'),name,DEST+'/Animations',fbx_options(skeleton))
        if not isinstance(clip,ue.AnimSequence) or clip.get_editor_property('skeleton')!=skeleton or clip.get_play_length()<=0:
            raise RuntimeError('Missing horse animation '+name)
        clip.set_preview_skeletal_mesh(mesh)
        match_root_units(clip,mesh)
        LIB.set_metadata_tag(clip,'StableHorseMotion',meta['source'])
        save(clip)
    save(skeleton)
    return dict(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=mesh.physics_asset.get_path_name(),
                material=material.get_path_name(),clips=list(clips))
