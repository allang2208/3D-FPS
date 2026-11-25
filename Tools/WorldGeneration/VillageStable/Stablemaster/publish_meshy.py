"""Import the two finished Meshy pieces on one skeleton and save the village resident."""
import json,os,subprocess
from pathlib import Path
import unreal as u
P=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
SRC=P/'SourceAssets/HillsVillageStable/StablemasterMeshyR3'
A=SRC/'Authoring'
DEST='/Game/WorldGeneration/TemperateHills/VillageStable/StablemasterMeshyR3'
E=u.EditorAssetLibrary;T=u.AssetToolsHelpers.get_asset_tools();M=u.MaterialEditingLibrary
def save(obj):
    if not obj or not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+str(obj))
    return obj
def existing(path):
    return E.load_asset(path) if E.does_asset_exist(path) else None
def make(name,folder,cls,factory):
    return existing(DEST+folder+'/'+name) or T.create_asset(name,DEST+folder,cls,factory)
def import_file(path,folder,factory,options=None):
    name=path.stem;uri=DEST+folder+'/'+name
    task=u.AssetImportTask();task.filename=str(path);task.destination_path=DEST+folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.save=False;task.factory=factory
    if options:task.options=options
    T.import_asset_tasks([task]);asset=existing(uri)
    if not asset:raise ValueError('Importer produced no '+uri)
    return asset
def mat_for(d):
    mat=make(d['name'],'/Materials',u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(mat);M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    mat.set_editor_property('two_sided',d['two_sided'])
    slab=M.create_material_expression(mat,u.MaterialExpressionSubstrateShadingModels,150,0)
    samples={}
    for i,(role,filename) in enumerate(d['files'].items()):
        tx=import_file(A/filename,'/Textures',u.TextureFactory())
        tx.set_editor_property('srgb',role=='Color')
        tx.set_editor_property('compression_settings',{'Color':u.TextureCompressionSettings.TC_DEFAULT,'Normal':u.TextureCompressionSettings.TC_NORMALMAP,'ORM':u.TextureCompressionSettings.TC_MASKS}[role])
        if role=='Normal':tx.set_editor_property('flip_green_channel',True)
        tx.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if role=='Normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER)
        save(tx)
        node=M.create_material_expression(mat,u.MaterialExpressionTextureSample,-650,240*i);node.texture=tx
        node.sampler_type={'Color':u.MaterialSamplerType.SAMPLERTYPE_COLOR,'Normal':u.MaterialSamplerType.SAMPLERTYPE_NORMAL,'ORM':u.MaterialSamplerType.SAMPLERTYPE_MASKS}[role]
        samples[role]=node
    def connect(node,out,other,pin):
        if not M.connect_material_expressions(node,out,other,pin):raise ValueError('Material connection: '+pin)
    for i,(role,ch,pin,factor) in enumerate([('Color','RGB','BaseColor',d['color'][:3]),('ORM','G','Roughness',d['rough']),('ORM','B','Metallic',d['metal'])]):
        node=samples.get(role);vec=isinstance(factor,list)
        if not node or (factor!=[1,1,1] if vec else factor!=1.):
            constant=M.create_material_expression(mat,u.MaterialExpressionConstant3Vector if vec else u.MaterialExpressionConstant,-600,840+i*120)
            if vec:constant.constant=u.LinearColor(*factor,1)
            else:constant.r=factor
            if node:
                mul=M.create_material_expression(mat,u.MaterialExpressionMultiply,-230,i*180)
                connect(node,ch,mul,'A');connect(constant,'',mul,'B');node=mul
            else:node=constant
            ch=''
        connect(node,ch,slab,pin)
    if 'Normal' in samples:connect(samples['Normal'],'RGB',slab,'Normal')
    if d['occlusion'] and 'ORM' in samples:M.connect_material_property(samples['ORM'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
    if d['alpha']=='MASK':
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED);mat.opacity_mask_clip_value=d['cutoff']
        M.connect_material_property(samples['Color'],'A',u.MaterialProperty.MP_OPACITY_MASK)
    if not M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise ValueError('Surface output')
    M.recompile_material(mat);return save(mat)
def neck_material():
    mat=make('M_Stablemaster_Neck','/Materials',u.Material,u.MaterialFactoryNew())
    M.delete_all_material_expressions(mat);M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    def node(cls,x,y):return M.create_material_expression(mat,cls,x,y)
    def wire(src,out,dst,pin):
        if not M.connect_material_expressions(src,out,dst,pin):raise RuntimeError('Neck material connection '+pin)
    slab=node(u.MaterialExpressionSubstrateShadingModels,450,0)
    samples={}
    for slot,(role,index) in enumerate([('Body',1),('Head',0)]):
        uv=node(u.MaterialExpressionTextureCoordinate,-950,slot*700);uv.coordinate_index=index
        for row,(channel,typ) in enumerate([('Color','COLOR'),('Normal','NORMAL'),('ORM','MASKS')]):
            tex=node(u.MaterialExpressionTextureSample,-650,slot*700+210*row)
            tex.texture=existing(DEST+'/Textures/T_Stablemaster_'+role+'_0_'+channel)
            tex.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+typ)
            wire(uv,'',tex,'UVs');samples[role,channel]=tex
    uv=node(u.MaterialExpressionTextureCoordinate,-650,-320);uv.coordinate_index=2
    mask=node(u.MaterialExpressionComponentMask,-400,-320)
    for c in 'rgba':mask.set_editor_property(c,c=='r')
    wire(uv,'',mask,'')
    for row,(channel,out,pin) in enumerate([('Color','RGB','BaseColor'),('Normal','RGB','Normal'),('ORM','G','Roughness'),('ORM','B','Metallic')]):
        mix=node(u.MaterialExpressionLinearInterpolate,0,row*210)
        wire(samples['Body',channel],out,mix,'A');wire(samples['Head',channel],out,mix,'B')
        wire(mask,'',mix,'Alpha');wire(mix,'',slab,pin)
    if not M.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Neck surface output')
    M.recompile_material(mat);return save(mat)
def mesh(role,materials,skeleton=None):
    ui=u.FbxImportUI();ui.automated_import_should_detect_type=False;ui.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    ui.import_as_skeletal=True;ui.import_mesh=True;ui.import_materials=False;ui.import_textures=False;ui.import_animations=False;ui.create_physics_asset=False
    if skeleton:ui.skeleton=skeleton
    opt=ui.skeletal_mesh_import_data;opt.convert_scene=True;opt.convert_scene_unit=True;opt.force_front_x_axis=False
    opt.set_editor_property('bUseT0AsRefPose',False);opt.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    sk=import_file(A/('SK_Stablemaster_'+role+'.fbx'),'/Meshes',u.FbxFactory(),ui)
    slots=list(sk.materials)
    for slot in slots:slot.material_interface=materials[str(slot.material_slot_name)]
    sk.set_editor_property('materials',slots);save(sk.skeleton);return save(sk)
def idle(body):
    names=list(map(str,u.AnimPoseExtensions.get_bone_names(body.skeleton.get_reference_pose())))
    comp=u.new_object(u.SkeletalMeshComponent);comp.set_skeletal_mesh_asset(body);ref=body.skeleton.get_reference_pose()
    frames=[]
    for n in names:
        v=u.AnimPoseExtensions.get_bone_pose(ref,n,u.AnimPoseSpaces.LOCAL)
        p,q,s=v.translation,v.rotation,v.scale3d;frames.append([p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z])
    idx={n:i for i,n in enumerate(names)}
    (A/'idle_reference.json').write_text(json.dumps(dict(names=names,parents=[idx.get(str(comp.get_parent_bone(n)),-1) for n in names],reference=frames)))
    env={k:v for k,v in os.environ.items() if k not in ('PYTHONHOME','PYTHONPATH')}
    subprocess.run([env['STABLEMASTER_PYTHON'],'-I',str(Path(__file__).resolve().with_name('fit_meshy_idle.py')),str(A/'idle_reference.json'),str(A/'idle_motion.json')],env=env,check=True)
    data=json.loads((A/'idle_motion.json').read_bytes());f=u.AnimSequenceFactory();f.target_skeleton=body.skeleton;f.preview_skeletal_mesh=body
    seq=make('A_Stablemaster_Stand','/Animations',u.AnimSequence,f)
    ctl=seq.get_editor_property('controller');ctl.open_bracket('Fit relaxed standing pose to stablemaster',False)
    try:
        ctl.set_frame_rate(u.FrameRate(data['rate'],1),False);ctl.set_number_of_frames(u.FrameNumber(data['frame_count']),False)
        known=set(map(str,u.AnimationLibrary.get_animation_track_names(seq)))
        for i,n in enumerate(names):
            keys=data['tracks'].get(n,[frames[i]])
            if n not in known:ctl.add_bone_curve(n,False)
            if not ctl.set_bone_track_keys(n,[u.Vector(*v[:3]) for v in keys],[u.Quat(*v[3:7]) for v in keys],[u.Vector(*v[7:]) for v in keys],False):raise RuntimeError(n)
    finally:ctl.close_bracket(False)
    seq.set_editor_property('loop',True);seq.set_editor_property('force_root_lock',True);return save(seq)
def resident(body,head,clip):
    factory=u.BlueprintFactory();factory.set_editor_property('parent_class',u.Character)
    bp=make('BP_Stablemaster','',u.Blueprint,factory);sub=u.get_engine_subsystem(u.SubobjectDataSubsystem);lib=u.SubobjectDataBlueprintFunctionLibrary
    handles=sub.k2_gather_subobject_data_for_blueprint(bp)
    def tmpl(h):return lib.get_object_for_blueprint(lib.get_data(h),bp)
    parent=next(h for h in handles if isinstance(tmpl(h),u.SkeletalMeshComponent))
    part=next((tmpl(h) for h in handles if isinstance(tmpl(h),u.SkeletalMeshComponent) and 'StablemasterHead' in tmpl(h).get_name()),None)
    if not part:
        handle,reason=sub.add_new_subobject(u.AddNewSubobjectParams(parent_handle=parent,new_class=u.SkeletalMeshComponent,blueprint_context=bp))
        sub.rename_subobject(handle,u.Text('StablemasterHead'));part=tmpl(handle)
    part.set_skeletal_mesh_asset(head);part.set_anim_instance_class(u.load_class(None,'/Script/FPSGAME.FPSPlayerHeadAnimInstance'))
    part.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    u.BlueprintEditorLibrary.compile_blueprint(bp)
    cdo=u.get_default_object(bp.generated_class());cdo.modify()
    cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.DISABLED);cdo.set_editor_property('tags',['NPC','Friendly','VillageStablemaster'])
    cdo.set_editor_property('replicates',True)
    cap=cdo.get_editor_property('capsule_component');cap.modify();cap.set_capsule_size(28.,84.,False)
    cap.set_collision_response_to_channel(u.CollisionChannel.ECC_VISIBILITY,u.CollisionResponseType.ECR_OVERLAP)
    main=cdo.get_editor_property('mesh');main.modify();main.set_skeletal_mesh_asset(body)
    main.set_relative_location(u.Vector(0,0,-84.),False,False)
    main.set_relative_rotation(u.Rotator(yaw=-90.),False,False)
    main.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE);play=main.get_editor_property('animation_data')
    play.anim_to_play=clip;play.saved_looping=True;play.saved_playing=True;main.set_editor_property('animation_data',play)
    cdo.character_movement.set_editor_property('default_land_movement_mode',u.MovementMode.MOVE_NONE)
    return save(bp)
if __name__=='__main__':
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    mats={d['name']:mat_for(d) for d in json.loads((A/'surfaces.json').read_bytes())}
    mats['M_Stablemaster_Neck']=neck_material()
    body=mesh('Body',mats);head=mesh('Head',mats,body.skeleton)
    if body.skeleton!=head.skeleton:raise RuntimeError('The two pieces must share the Meshy rig')
    clip=idle(body);bp=resident(body,head,clip)
    (SRC/'imported.json').write_text(json.dumps(dict(body=body.get_path_name(),head=head.get_path_name(),skeleton=body.skeleton.get_path_name(),idle=clip.get_path_name(),blueprint=bp.get_path_name(),materials={k:v.get_path_name() for k,v in mats.items()},gameplay_test=False),indent=2))
