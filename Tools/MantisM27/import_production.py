"""Save the M27 production candidate and its existing AI/F6 integration.

Run through the shared UE bridge when an editor already exists, otherwise with
UnrealEditor-Cmd -run=pythonscript. Never starts PIE or opens a preview viewport.
"""
from pathlib import Path
import json
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/MantisM27/ProductionV1'
SOURCE=ROOT/'Delivery'
SOURCE_TEXTURES=ROOT.parent/'MeshyImport20261005V1/Source'
OWNER='/Game/Monsters/MantisM27'
DEST=OWNER+'/ProductionV1'
LIB=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
REPORT=ROOT/'ue_production_receipt.json'
manifest=json.loads((SOURCE/'motion_manifest.json').read_text(encoding='utf-8'))
report={'name':'螳螂-M27','revision':'ProductionV1','saved':False,'assets':[],
        'tested':False,'runtime_tested':False,'visual_tested':False,'user_review_pending':True}

def receipt(): REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not asset or not asset.get_path_name().startswith(OWNER+'/'):
        raise RuntimeError('M27 save target is absent or outside its owned folder.')
    if not LIB.save_loaded_asset(asset,False): raise RuntimeError('Could not save '+asset.get_path_name())
    if asset.get_path_name() not in report['assets']: report['assets'].append(asset.get_path_name())
    receipt()
def make(name,folder,cls,factory):
    return u.load_asset(folder+'/'+name) or TOOLS.create_asset(name,folder,cls,factory)
def import_file(filename,name,folder,options=None,factory=None):
    task=u.AssetImportTask(); task.filename=str(filename); task.destination_name=name; task.destination_path=folder
    task.automated=True; task.save=False; task.replace_existing=True; task.replace_existing_settings=True
    if options: task.options=options
    if factory: task.factory=factory
    TOOLS.import_asset_tasks([task])
    asset=u.load_asset(folder+'/'+name)
    if not asset or not task.imported_object_paths: raise RuntimeError('Import did not produce '+folder+'/'+name)
    return asset

def options(skeleton=None,animation=False):
    opt=u.FbxImportUI(); opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION if animation else u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True; opt.import_mesh=not animation; opt.import_animations=animation
    opt.import_materials=False; opt.import_textures=False; opt.create_physics_asset=not animation; opt.skeleton=skeleton
    data=opt.skeletal_mesh_import_data
    data.convert_scene=True; data.convert_scene_unit=True; data.import_uniform_scale=1.
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.set_editor_property('use_t0_as_ref_pose',False)
    data.set_editor_property('update_skeleton_reference_pose',False)
    if animation:
        data=opt.anim_sequence_import_data
        data.convert_scene=True; data.convert_scene_unit=True; data.import_uniform_scale=1.
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',30)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        data.set_editor_property('preserve_local_transform',True)
    return opt

def material():
    textures={}
    for name,filename in [('BaseColor','texture_0.png'),('Normal','normal.png'),('MetallicRoughness','texture_0_metallic_roughness.png')]:
        tex=import_file(SOURCE_TEXTURES/filename,'T_M27_'+name,DEST+'/Textures',factory=u.TextureFactory())
        tex.set_editor_property('srgb',name=='BaseColor')
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if name=='Normal' else
            u.TextureCompressionSettings.TC_DEFAULT if name=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
        if name=='Normal': tex.set_editor_property('flip_green_channel',True)
        save(tex); textures[name]=tex
    mat=make('M_M27_OriginalPBR',DEST+'/Materials',u.Material,u.MaterialFactoryNew())
    mel=u.MaterialEditingLibrary; mel.delete_all_material_expressions(mat)
    mat.set_editor_property('two_sided',True); mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    slab=mel.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels)
    for name,output,pin,prop in [('BaseColor','RGB','BaseColor',u.MaterialProperty.MP_BASE_COLOR),
                              ('Normal','RGB','Normal',u.MaterialProperty.MP_NORMAL),
                              ('MetallicRoughness','G','Roughness',u.MaterialProperty.MP_ROUGHNESS),
                              ('MetallicRoughness','B','Metallic',u.MaterialProperty.MP_METALLIC)]:
        node=mel.create_material_expression(mat,u.MaterialExpressionTextureSample)
        node.set_editor_property('texture',textures[name])
        node.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL if name=='Normal' else
            u.MaterialSamplerType.SAMPLERTYPE_COLOR if name=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        mel.connect_material_property(node,output,prop); mel.connect_material_expressions(node,output,slab,pin)
    mel.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL)
    mel.set_base_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH,True)
    mel.recompile_material(mat)
    LIB.set_metadata_tag(mat,'Source','Original Meshy UV and embedded PBR; G roughness, B metallic; normal green inverted for UE')
    save(mat); return mat

try:
    if not hasattr(u,'MantisM27Monster'): raise RuntimeError('The running UE module does not contain MantisM27Monster; the current native build must be loaded first.')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor(): raise RuntimeError('Cannot author M27 while PIE is running.')
    ai=u.load_class(None,'/Game/Monsters/AI/BP_MonsterAIController.BP_MonsterAIController_C')
    if not ai: raise RuntimeError('The existing shared monster Behavior Tree controller is required.')
    body_material=material()
    mesh=import_file(SOURCE/'SK_MantisM27.fbx','SK_MantisM27',DEST,options(),u.FbxFactory())
    skeleton=mesh.skeleton
    slots=list(mesh.materials)
    for slot in slots: slot.material_interface=body_material
    mesh.set_editor_property('materials',slots); mesh.set_editor_property('enable_per_poly_collision',False)
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    settings=editor.get_lod_build_settings(mesh,0)
    settings.recompute_normals=False; settings.recompute_tangents=True; settings.use_mikk_t_space=True; settings.use_full_precision_u_vs=True
    editor.set_lod_build_settings(mesh,0,settings)
    factory=u.DataAssetFactory(); factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings.static_class())
    policy=make('LOD_MantisM27',DEST,u.SkeletalMeshLODSettings,factory)
    lods=[]
    for percentage,screen in [(1.,1.),(.5,.45),(.20,.20),(.08,.09)]:
        row=u.SkeletalMeshLODGroupSettings(); reduction=row.get_editor_property('reduction_settings')
        reduction.set_editor_property('num_of_triangles_percentage',percentage)
        reduction.set_editor_property('base_lod',0)
        reduction.set_editor_property('max_bones_per_vertex',4)
        reduction.set_editor_property('enforce_bone_boundaries',True)
        row.set_editor_property('reduction_settings',reduction)
        row.set_editor_property('screen_size',u.PerPlatformFloat(default=screen)); lods.append(row)
    policy.set_editor_property('lod_groups',lods); save(policy); mesh.set_editor_property('lod_settings',policy)
    if not editor.regenerate_lod(mesh,4,False,False): raise RuntimeError('M27 distance LOD generation did not complete.')
    # Assigning a policy alone does not apply its values to UE 5.8 source models.
    import sys
    sys.path.insert(0,str(PROJECT/'Tools/MantisM27'))
    from finish_lods import configure
    configure(mesh,policy)
    from finish_contacts import configure_contacts
    configure_contacts(mesh)
    LIB.set_metadata_tag(mesh,'Source','Meshy_AI_M_27_Mawbound_Horror_1005150638_texture.glb; original 197761-triangle close-up surface; custom M27 rig')
    LIB.set_metadata_tag(mesh,'ReviewStatus','ProductionV1 saved; no visual or runtime acceptance performed')
    save(mesh.physics_asset); save(skeleton); save(mesh)
    report.update(mesh=mesh.get_path_name(),skeleton=skeleton.get_path_name(),physics=mesh.physics_asset.get_path_name(),lod_count=4,physics_body_count=15,
                  lod_triangle_ratios=[1,.5,.2,.08],lod_screen_sizes=[1,.45,.20,.09],lod_policy_applied_to_source_models=True,
                  blade_sockets_force_animation=True)
    receipt()
    clips={}
    for role,info in manifest['clips'].items():
        clip=import_file(SOURCE/info['file'],'A_M27_'+role,DEST+'/Animations',options(skeleton,True),u.FbxFactory())
        clip.set_preview_skeletal_mesh(mesh)
        clip.set_editor_property('enable_root_motion',False)
        LIB.set_metadata_tag(clip,'SourceRevision','M27 ProductionV1, custom anatomy, in-place, user review pending')
        save(clip); clips[role]=clip
    save(skeleton)
    factory=u.BlueprintFactory(); factory.set_editor_property('parent_class',u.MantisM27Monster.static_class())
    bp=make('BP_MantisM27',OWNER,u.Blueprint,factory)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class())
    defaults.set_editor_property('visual_mesh',mesh)
    defaults.set_editor_property('monster_display_name','螳螂 M27')
    defaults.set_editor_property('ai_controller_class',ai)
    defaults.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    for prop,role in [('idle_clip','Idle'),('walk_clip','Walk'),('attack_clip','LeftSlash'),('left_slash_clip','LeftSlash'),('right_slash_clip','RightSlash'),('death_clip','Death')]:
        defaults.set_editor_property(prop,clips[role])
    speed=manifest['clips']['Walk']['expected_speed_cm_s']
    defaults.set_editor_property('source_move_speed',speed)
    defaults.set_editor_property('walk_speed',speed)
    defaults.set_editor_property('contact_time',.48); defaults.set_editor_property('contact_end',.68)
    component=defaults.get_editor_property('mesh'); component.set_skeletal_mesh_asset(mesh)
    component.set_editor_property('override_materials',[]); component.set_anim_instance_class(u.FatZombieAnimInstance)
    defaults.get_editor_property('character_movement').set_editor_property('max_walk_speed',speed)
    combat=defaults.get_editor_property('combat'); combat.set_editor_property('hit_clip',clips['Hit']); combat.set_editor_property('dizzy_clip',clips['Dizzy'])
    knockdown=defaults.get_editor_property('knockdown')
    for prop,role in [('fall_clip','Fall'),('get_up_clip','GetUp'),('prone_get_up_clip','ProneGetUp')]: knockdown.set_editor_property(prop,clips[role])
    LIB.set_metadata_tag(bp,'MonsterIdentity','螳螂 M27 / MantisM27')
    LIB.set_metadata_tag(bp,'ProductionRevision','ProductionV1; F6 entry MantisM27; user review pending')
    save(bp)
    report.update(saved=True,blueprint=bp.get_path_name(),ai_controller=ai.get_path_name(),f6_entry='MantisM27',
                  movement_speed_cm_s=speed,contact_window_seconds=[.48,.68],
                  clips={role:{'asset':clip.get_path_name(),'duration_seconds':clip.get_play_length()} for role,clip in clips.items()},
                  stage='Custom skinned model, original PBR, four LODs, ten animations, 15-body ragdoll, shared AI and F6 blueprint saved')
    receipt()
    print('M27_PRODUCTION_SAVED '+str(REPORT),flush=True)
except Exception as error:
    report['error']=str(error); receipt(); raise
