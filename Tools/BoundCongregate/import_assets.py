"""Background UE import: real packages, shared AI, garments and continuous corpse."""
from pathlib import Path
import json, sys, subprocess
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME');ROOT=PROJECT/'SourceAssets/BoundCongregateMeshy20261006'
DEST='/Game/Monsters/BoundCongregate';E=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
REPORT=ROOT/'Records/delivery.json';report=dict(complete=False,saved=[],tested=False,rendered=False)
def record():REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(a):
    if not a or not E.save_loaded_asset(a,False):raise RuntimeError('Could not save '+str(a))
    name=a.get_path_name()
    if name not in report['saved']:report['saved'].append(name)
    record()
def create(name,folder,cls,factory):return u.load_asset(folder+'/'+name) or AT.create_asset(name,folder,cls,factory)
def texture(file,name,normal=False,linear=False):
    path=DEST+'/Textures';a=u.load_asset(path+'/'+name)
    if not a:
        task=u.AssetImportTask();task.filename=str(ROOT/'Textures'/file);task.destination_path=path;task.destination_name=name
        task.automated=True;task.save=False;task.replace_existing=True;AT.import_asset_tasks([task]);a=u.load_asset(path+'/'+name)
    if not a:raise RuntimeError('Texture import '+file)
    a.set_editor_property('srgb',not (normal or linear))
    if normal:
        a.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP)
        a.set_editor_property('flip_green_channel',True)
    elif linear:a.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(a);return a
def material(name,color=None,base=None,normal=None,rough=None,packed=False,metal=0,tint=None):
    m=create(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(m)
    m.set_editor_property('two_sided',True)
    # Commandlets do not infer usage from a placed mesh; compile these before
    # saving so PIE and packaged skeletal/cloth draws keep the authored maps.
    m.set_editor_property('used_with_skeletal_mesh',True)
    m.set_editor_property('used_with_clothing',True)
    slab=L.create_material_expression(m,u.MaterialExpressionSubstrateShadingModels)
    def connect(node,out,prop,pin):L.connect_material_property(node,out,prop);L.connect_material_expressions(node,out,slab,pin)
    def constant(value):
        n=L.create_material_expression(m,u.MaterialExpressionConstant3Vector if isinstance(value,tuple) else u.MaterialExpressionConstant)
        n.set_editor_property('constant' if isinstance(value,tuple) else 'r',u.LinearColor(*value,1) if isinstance(value,tuple) else value);return n
    def sample(t):
        n=L.create_material_expression(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',t)
        if t.get_editor_property('compression_settings')==u.TextureCompressionSettings.TC_NORMALMAP:n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
        elif not t.get_editor_property('srgb'):n.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
        return n
    b=sample(base) if base else constant(color)
    if tint:
        mult=L.create_material_expression(m,u.MaterialExpressionMultiply)
        L.connect_material_expressions(b,'RGB',mult,'A');L.connect_material_expressions(constant(tint),'',mult,'B');b=mult
    connect(b,'RGB' if base and not tint else '',u.MaterialProperty.MP_BASE_COLOR,'BaseColor')
    r=sample(rough) if rough else constant(.75)
    connect(r,'G' if packed else 'R' if rough else '',u.MaterialProperty.MP_ROUGHNESS,'Roughness')
    connect(r,'B',u.MaterialProperty.MP_METALLIC,'Metallic') if packed else connect(constant(metal),'',u.MaterialProperty.MP_METALLIC,'Metallic')
    if normal:connect(sample(normal),'RGB',u.MaterialProperty.MP_NORMAL,'Normal')
    connect(constant(.35),'',u.MaterialProperty.MP_SPECULAR,'Specular')
    L.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL);L.recompile_material(m);save(m);return m
def options(kind,skeleton=None):
    o=u.FbxImportUI();o.automated_import_should_detect_type=False;o.mesh_type_to_import=kind
    o.import_materials=False;o.import_textures=False;o.import_as_skeletal=True
    o.import_animations=kind==u.FBXImportType.FBXIT_ANIMATION;o.import_mesh=not o.import_animations;o.create_physics_asset=False
    if skeleton:o.skeleton=skeleton
    d=o.anim_sequence_import_data if o.import_animations else o.skeletal_mesh_import_data
    d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=False;d.import_uniform_scale=1
    if not o.import_animations:
        d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        d.set_editor_property('vertex_color_import_option',u.VertexColorImportOption.REPLACE)
    else:
        d.set_editor_property('use_default_sample_rate',False)
        d.set_editor_property('custom_sample_rate',30)
        d.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    return o
def fbx(name,folder,opts):
    task=u.AssetImportTask();task.filename=str(ROOT/'Exports'/(name+'.fbx'));task.destination_path=folder;task.destination_name=name
    task.factory=u.FbxFactory();task.options=opts;task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True
    AT.import_asset_tasks([task]);a=u.load_asset(folder+'/'+name)
    if not a:raise RuntimeError('FBX import '+name)
    return a

def main():
    # A normal native build must exist before this new class is written to a BP.
    if not hasattr(u,'BoundCongregate'):raise RuntimeError('Build the baseline FPSGAMEEditor DLL before importing this new class')
    u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
    u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilation 0')
    skincolor=texture('texture_0.png','T_BC_Flesh_BaseColor')
    skinnormal=texture('normal.png','T_BC_Flesh_Normal',normal=True)
    skinpacked=texture('texture_0_metallic_roughness.png','T_BC_Flesh_MR',linear=True)
    clothcolor=texture('BC_Fabric_BaseColor.png','T_BC_Fabric_BaseColor')
    clothnormal=texture('BC_Fabric_Normal.png','T_BC_Fabric_Normal',normal=True)
    clothrough=texture('BC_Fabric_Roughness.png','T_BC_Fabric_Roughness',linear=True)
    mats={
        'BC_Flesh':material('M_BC_Flesh',base=skincolor,normal=skinnormal,rough=skinpacked,packed=True),
        'BC_RagFabric':material('M_BC_RagFabric',base=clothcolor,normal=clothnormal,rough=clothrough),
        'BC_Lining':material('M_BC_Lining',base=clothcolor,normal=clothnormal,rough=clothrough,tint=(1.30,1.15,.91)),
        'BC_Binding':material('M_BC_Binding',color=(.035,.030,.023),normal=clothnormal,rough=clothrough),
        'BC_Hardware':material('M_BC_Hardware',color=(.19,.17,.125),metal=.65)
    }
    mesh=fbx('SK_BoundCongregate',DEST,options(u.FBXImportType.FBXIT_SKELETAL_MESH))
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        key=str(slot.get_editor_property('imported_material_slot_name')).split('_Proxy')[0]
        slot.set_editor_property('material_interface',mats[key])
    mesh.set_editor_property('materials',slots)
    physics=u.load_asset(DEST+'/PA_BoundCongregate')
    if not physics:
        # PhysicsAssetFactory opens a modal body-generation dialog even when a
        # target is supplied. Duplicate a package, then replace every shape and
        # constraint below; this stays fully unattended.
        source_class=E.load_blueprint_class('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler')
        source_physics=u.get_default_object(source_class).get_editor_property('visual_mesh').get_editor_property('physics_asset')
        physics=E.duplicate_asset(source_physics.get_path_name(),DEST+'/PA_BoundCongregate')
    if not u.BoundCongregate.build_surface_physics(mesh,physics):raise RuntimeError('Could not author hit surfaces')
    if not u.BoundCongregate.build_garment_simulation(mesh):raise RuntimeError('Could not author cloth simulation')
    E.set_metadata_tag(mesh,'Source','User Meshy GLB 25028b9b2c002e0a0bb08023f50fd5aad3904a4c898be7e345ec5b9aa31dfeda')
    E.set_metadata_tag(mesh,'Production','Ten donor limbs; separate solid fabric render shells and hidden continuous cloth proxies; no additional reduction')
    save(mesh);save(mesh.skeleton);save(physics)
    clips={}
    for role,data in json.loads((ROOT/'Authoring/motion_manifest.json').read_text()).items():
        clip=fbx('A_BoundCongregate_'+role,DEST+'/Animations',options(u.FBXImportType.FBXIT_ANIMATION,mesh.skeleton))
        clip.set_editor_property('loop',data['loop']);clip.set_editor_property('enable_root_motion',False);clip.set_editor_property('force_root_lock',True)
        clip.set_preview_skeletal_mesh(mesh);save(clip);clips[role]=clip
    save(mesh.skeleton)
    print('BOUND_CONGREGATE_LIVING_SAVED',flush=True)
    corpse_path=DEST+'/Corpse/SK_BoundCongregate_Corpse'
    corpse=u.load_asset(corpse_path) or E.duplicate_asset(mesh.get_path_name(),corpse_path)
    corpse_root=ROOT/'SoftCorpse/BoundCongregate';corpse_root.mkdir(parents=True,exist_ok=True)
    skelpath=DEST+'/Corpse/SKEL_BoundCongregate_Corpse'
    corpseskeleton=u.load_asset(skelpath) or E.duplicate_asset(mesh.skeleton.get_path_name(),skelpath)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.M14SoftBodyData)
    data=create('DA_BoundCongregate_Corpse',DEST+'/Corpse',u.M14SoftBodyData,factory)
    if data.get_editor_property('corpse_mesh')!=corpse:
        # Rebinding an already-authored corpse would treat soft bones as the
        # living rig. Resume saved stages without changing that source contract.
        u.SystemLibrary.execute_console_command(None,'Editor.AsyncSkinnedAssetCompilationFinishAll')
        u.BoundCongregate.prepare_corpse_mesh(corpse)
        if not u.M14SoftBodyData.export_surface(corpse,str(corpse_root/'surface.bin'),[]):raise RuntimeError('Corpse source export failed')
        subprocess.run(['C:/Users/allan/AppData/Local/Programs/Python/Python311/python.exe',str(PROJECT/'Tools/BoundCongregate/author_soft_corpse.py')],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
        if not u.M14SoftBodyData.build_corpse(corpse,corpseskeleton,data,str(corpse_root/'cage.json'),str(corpse_root/'embedding.bin')):raise RuntimeError('Corpse binding failed')
    sys.path.insert(0,str(PROJECT/'Tools/MonsterSoftCorpse'));import corpse_materials
    # The algorithm is shared; this monster owns the output material packages.
    corpse_materials.DEST=DEST+'/Corpse/Materials';saved=set();slots=list(mesh.get_editor_property('materials'))
    for slot in slots:slot.set_editor_property('material_interface',corpse_materials.make(slot.get_editor_property('material_interface'),saved))
    corpse.set_editor_property('materials',slots);u.M14SoftBodyData.bind_to_living_mesh(mesh,data)
    for a in [corpse,corpseskeleton,data,mesh]:save(a)
    report['saved'].extend(sorted(saved))
    bp_factory=u.BlueprintFactory();bp_factory.set_editor_property('parent_class',u.BoundCongregate)
    bp=create('BP_BoundCongregate',DEST,u.Blueprint,bp_factory)
    cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('visual_mesh',mesh);cdo.set_editor_property('mesh_yaw',u.BoundCongregate.reference_facing_yaw(mesh))
    controller=E.load_blueprint_class('/Game/Monsters/AI/BP_MonsterAIController')
    if not controller:raise RuntimeError('Shared monster controller missing')
    cdo.set_editor_property('ai_controller_class',controller)
    cdo.set_editor_property('auto_possess_ai',u.AutoPossessAI.PLACED_IN_WORLD_OR_SPAWNED)
    cdo.set_editor_property('animation_walk_speed',38.095)
    for prop,role in [('idle_clip','Idle'),('move_clip','Walk'),('turn_left_clip','TurnLeft'),('turn_right_clip','TurnRight'),('bite_clip','Bite'),('hit_clip','Hit'),('death_clip','Death')]:cdo.set_editor_property(prop,clips[role])
    shared=E.load_blueprint_class('/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler')
    if shared:
        old=u.get_default_object(shared)
        for prop,source in [('breath_sound','idle_sound'),('bite_sound','bite_sound'),('death_sound','death_sound')]:
            sound=old.get_editor_property(source)
            if sound:cdo.set_editor_property(prop,sound)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    if (ROOT/'RigRepairV3/motion_manifest.json').exists():
        import runpy
        runpy.run_path(str(PROJECT/'Tools/BoundCongregate/import_rig_v3.py'),run_name='__main__')
    elif (ROOT/'LocomotionV2/motion_manifest.json').exists():
        import runpy
        runpy.run_path(str(PROJECT/'Tools/BoundCongregate/import_locomotion_v2.py'),run_name='__main__')
    report.update(complete=True,blueprint=bp.get_path_name(),mesh=cdo.get_editor_property('visual_mesh').get_path_name(),mesh_yaw=cdo.get_editor_property('mesh_yaw'),
        ground_limbs=10,bones=56,ai='Shared Monster BT',death='M14 V19 continuous soft corpse',
        spawn_entry='F6 -> 缚群',scope='Registered selectable monster; random encounter pools unchanged',
        user_testing_pending=True)
    record();print('BOUND_CONGREGATE_DELIVERED '+str(REPORT),flush=True)
try:main()
except Exception as error:report['error']=str(error);record();raise
