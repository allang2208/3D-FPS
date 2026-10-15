"""Create two independent guard-derived station monsters, without running the game."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/CargoStationStaff20261014/V01')
SHARED='/Game/Monsters/CargoStationStaff'
SOURCE='/Game/Monsters/FacelessSecurity'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; no import performed')
manifest=json.loads((ROOT/'authoring_receipt.json').read_text(encoding='utf-8'))
receipt=ROOT/'ue_delivery.json'
report=json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else dict(stage='importing',saved=[],variants={},runtime_tested=False,rendered=False)

def record():receipt.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
    path=asset.get_path_name()
    if path not in report['saved']:report['saved'].append(path)
    record()
def import_one(file,folder,name,options=None):
    path=folder+'/'+name
    asset=u.load_asset(path) if LIB.does_asset_exist(path) else None
    if asset:return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=False
    if options:task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);asset=u.load_asset(path)
    if not asset or not task.imported_object_paths:raise RuntimeError('Import failed '+path)
    return asset
def connect(source,output,dest,pin):
    normalize=lambda s:''.join(c.lower() for c in str(s) if c.isalnum())
    names=MEL.get_material_expression_input_names(dest)
    match=next((p for p in names if normalize(p)==normalize(pin)),None)
    if match is None:match=next((p for p in names if normalize(p).startswith(normalize(pin))),None)
    if match is None or not MEL.connect_material_expressions(source,output,dest,match):raise RuntimeError('Cannot connect '+pin)

source_bp=u.load_asset(SOURCE+'/BP_FacelessSecurity')
source_cdo=u.get_default_object(source_bp.generated_class())
source_mesh=source_cdo.get_editor_property('visual_mesh')
skeleton=source_mesh.get_editor_property('skeleton');physics=source_mesh.get_editor_property('physics_asset')
report['source_blueprint']=source_bp.get_path_name();report['source_mesh']=source_mesh.get_path_name()
report['shared_skeleton']=skeleton.get_path_name();report['shared_physics']=physics.get_path_name();record()
textures={}
for file in sorted((ROOT/'Textures').glob('*.png')):
    tex=import_one(file,SHARED+'/Textures','T_'+file.stem)
    normal=file.stem.endswith('_Normal');data=normal or file.stem.endswith('_ORM')
    tex.set_editor_property('srgb',not data);tex.set_editor_property('never_stream',False)
    if normal:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif data:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);textures[file.stem]=tex
materials={}
for role in manifest['variants']:
    families=[role+'_Workwear',role+('_Vest' if role=='CargoPorter' else '_Reinforcement'),role+'_Reflective',role+'_Helmet']
    for family in families:
        path=SHARED+'/Materials/M_'+family
        mat=u.load_asset(path) if LIB.does_asset_exist(path) else None
        if not mat:
            mat=AT.create_asset('M_'+family,SHARED+'/Materials',u.Material,u.MaterialFactoryNew())
            cloth=family.endswith(('_Workwear','_Vest','_Reinforcement'))
            slab=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF if cloth else u.MaterialExpressionSubstrateShadingModels,450,0)
            for i,(suffix,pin,channel,sampler) in enumerate([
                ('BaseColor','DiffuseAlbedo' if cloth else 'BaseColor','RGB',u.MaterialSamplerType.SAMPLERTYPE_COLOR),
                ('Normal','Normal','RGB',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
                ('ORM','Roughness','G',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
                node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSample,0,i*180)
                node.texture=textures[family+'_'+suffix];node.sampler_type=sampler;connect(node,channel,slab,pin)
                if i==0 and cloth:connect(node,'RGB',slab,'FuzzColor')
                if i==2 and not cloth:connect(node,'B',slab,'Metallic')
            if cloth:
                for pin,value in [('F0',.022),('FuzzAmount',.12),('FuzzRoughness',.84)]:
                    node=MEL.create_material_expression(mat,u.MaterialExpressionConstant,200,0);node.r=value;connect(node,'',slab,pin)
            if not MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output failed')
        mat.set_editor_property('two_sided',False)
        if not family.endswith('_Helmet'):MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
        errors=MEL.recompile_material(mat)
        if errors:raise RuntimeError('Material compilation '+str(errors))
        save(mat);materials[family]=mat

def assign_materials(mesh,static=False):
    prop='static_materials' if static else 'materials';slots=list(mesh.get_editor_property(prop))
    for slot in slots:
        family=str(slot.get_editor_property('imported_material_slot_name')).split('.')[0]
        mat=materials.get(family)
        if mat is None and family.startswith('Security_'):mat=u.load_asset(SOURCE+'/Materials/M_FS1_'+family.removeprefix('Security_'))
        if mat is None:raise RuntimeError('Missing material '+family)
        slot.material_interface=mat
    mesh.set_editor_property(prop,slots)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for role,entry in manifest['variants'].items():
    dest='/Game/Monsters/'+role
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
    data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    meshes={}
    for kind in ['outfit','clothing']:
        filename=entry[kind]['file'];mesh=import_one(ROOT/'Delivery'/filename,dest,Path(filename).stem,options)
        assign_materials(mesh);mesh.set_editor_property('physics_asset',physics)
        LIB.set_metadata_tag(mesh,'ProductionSource','CargoStationStaff20261014 V01; FacelessSecurity V13 native skin and rig')
        save(mesh);meshes[kind]=mesh
    hatname=entry['helmet']['name'];options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;options.import_as_skeletal=False;options.import_mesh=True
    options.import_animations=False;options.import_materials=False;options.import_textures=False
    data=options.static_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.combine_meshes=True;data.auto_generate_collision=False;data.one_convex_hull_per_ucx=True
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    hat=import_one(ROOT/'Delivery'/(hatname+'.fbx'),dest+'/Accessories',hatname,options)
    assign_materials(hat,True);save(hat)
    bppath=dest+'/BP_'+role
    bp=u.load_asset(bppath) if LIB.does_asset_exist(bppath) else LIB.duplicate_asset(source_bp.get_path_name(),bppath)
    if not bp:raise RuntimeError('Blueprint duplication failed '+role)
    u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
    cdo.set_editor_property('visual_mesh',meshes['outfit']);component=cdo.get_editor_property('mesh')
    component.set_skeletal_mesh_asset(meshes['outfit']);component.set_editor_property('override_materials',[])
    tags=[t for t in cdo.get_editor_property('tags') if str(t) not in ['FacelessSecurity','CargoPorter','CargoTechnician']]
    for tag in [role,'CargoStation']:
        if not any(str(t)==tag for t in tags):tags.append(u.Name(tag))
    cdo.set_editor_property('tags',tags)
    subsystem=u.get_engine_subsystem(u.SubobjectDataSubsystem);library=u.SubobjectDataBlueprintFunctionLibrary
    cap=None
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        obj=library.get_object_for_blueprint(library.get_data(handle),bp)
        if isinstance(obj,u.SecurityHatComponent):cap=obj;break
    if cap is None:raise RuntimeError('Duplicated guard has no hat component')
    cap.set_static_mesh(hat);cap.set_editor_property('override_materials',[])
    cap.set_editor_property('head_bone','head')
    cap.set_editor_property('head_attachment_transform',u.Transform(location=u.Vector(*entry['helmet']['relative_location_cm']),rotation=u.Rotator(0,0,0),scale=u.Vector(1,1,1)))
    cap.set_collision_enabled(u.CollisionEnabled.NO_COLLISION)
    LIB.set_metadata_tag(bp,'MSeriesNumber',entry['number'])
    LIB.set_metadata_tag(bp,'IntendedRegion','Freight station / cargo area')
    LIB.set_metadata_tag(bp,'OutfitRevision','V01 workwear and safety helmet; all guard animation and gameplay defaults inherited')
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    cdo=u.get_default_object(bp.generated_class())
    clips={p:cdo.get_editor_property(p+'_clip').get_path_name() for p in ['idle','walk','attack']}
    for group,names in [('combat',['hit_clip','dizzy_clip']),('knockdown',['fall_clip','get_up_clip','prone_get_up_clip'])]:
        obj=cdo.get_editor_property(group)
        for name in names:
            clip=obj.get_editor_property(name);clips[group+'.'+name]=clip.get_path_name() if clip else None
    report['variants'][role]=dict(number=entry['number'],blueprint=bp.get_path_name(),meshes={k:v.get_path_name() for k,v in meshes.items()},
        helmet=hat.get_path_name(),shared_animations=clips,navigation='Exact guard capsule and NavAgent inherited; F6 footprint 44 cm',
        combat='Guard AI, damage timing, hit, knockdown, stun, ragdoll and rewards retained')
    record();print('CARGO_SAVED '+role,flush=True)
# Constructor defaults are not rebuilt by Live Coding. Install the same
# catalogue entries on this editor session's native templates for the next PIE.
templates=[u.get_default_object(u.DevelopmentSpawnComponent)]
controller=u.get_default_object(u.FPSGAMEPlayerController)
spawner=controller.get_editor_property('development_spawner')
if spawner:templates.append(spawner)
for template in templates:
    entries=list(template.get_editor_property('monsters'))
    for entry in entries:
        if str(entry.get_editor_property('id'))=='M10Mawcrawler':entry.set_editor_property('name',u.Text('沉匣 M-20'))
    for role,label in [('CargoPorter','搬运工 M-10'),('CargoTechnician','技术员 M-11')]:
        entry=next((e for e in entries if str(e.get_editor_property('id'))==role),None)
        if entry is None:entry=u.DevelopmentMonsterEntry();entries.append(entry)
        entry.set_editor_property('id',u.Name(role));entry.set_editor_property('name',u.Text(label))
        entry.set_editor_property('character_class',u.load_class(None,'/Game/Monsters/'+role+'/BP_'+role+'.BP_'+role+'_C'))
        entry.set_editor_property('footprint_radius',44.)
    template.set_editor_property('monsters',entries)
report['editor_catalogue_templates']=[o.get_path_name() for o in templates]
report['stage']='saved';record()
print('CARGO_STAFF_ASSETS_SAVED '+str(len(report['saved'])),flush=True)
