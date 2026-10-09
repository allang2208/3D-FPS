"""Background import into an independent security namespace; no game/preview tests."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V01')
DEST='/Game/Monsters/FacelessSecurity'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
report=json.loads((ROOT/'ue_delivery.json').read_text(encoding='utf-8')) if (ROOT/'ue_delivery.json').exists() else {'stage':'importing','saved':[],'runtime_tested':False}
def record():
    (ROOT/'ue_delivery.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
def save(asset):
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record()
def copy_asset(source,name):
    path=DEST+'/'+name
    asset=u.load_asset(path) if LIB.does_asset_exist(path) else LIB.duplicate_asset(source,path)
    if not asset:raise RuntimeError('Copy source unavailable: '+source)
    return asset
def import_one(file,folder,name,options=None):
    path=folder+'/'+name
    if LIB.does_asset_exist(path):return u.load_asset(path)
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);asset=u.load_asset(path)
    if not asset:raise RuntimeError('Import failed '+path)
    return asset
def connect(source,output,dest,pin):
    names=MEL.get_material_expression_input_names(dest)
    normalize=lambda s:''.join(c.lower() for c in str(s) if c.isalnum())
    match=next((p for p in names if normalize(p)==normalize(pin)),None)
    if match is None:match=next((p for p in names if normalize(p).startswith(normalize(pin))),None)
    if match is None or not MEL.connect_material_expressions(source,output,dest,match):raise RuntimeError('Material pin '+pin+' in '+str(names))
skeleton=copy_asset('/Game/ZombieFemale/Asset/Meshes/SK_ZombieFemale','SKEL_FacelessSecurity')
physics=copy_asset('/Game/ZombieFemale/Asset/Meshes/PA_ZombieFemale','PA_FacelessSecurity')
save(skeleton);save(physics)
textures={}
for file in sorted((ROOT/'Textures').glob('*.png')):
    name='T_FS1_'+file.stem;tex=import_one(file,DEST+'/Textures',name)
    is_normal='_Normal' in file.stem or file.stem=='Source_normal'
    is_data=is_normal or '_ORM' in file.stem or 'metallic_roughness' in file.stem
    tex.set_editor_property('srgb',not is_data);tex.set_editor_property('never_stream',False)
    if is_normal:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif is_data:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);textures[file.stem]=tex
materials={}
for family in ['Skin','Uniform','Trousers','Trim','Hardware','Insignia','Leather']:
    name='M_FS1_'+family;path=DEST+'/Materials/'+name
    if LIB.does_asset_exist(path):mat=u.load_asset(path)
    else:
        mat=AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        cloth=family in ['Uniform','Trousers','Trim','Insignia']
        slab=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF if cloth else u.MaterialExpressionSubstrateShadingModels,450,0)
        keys=['Source_texture_0','Source_normal','Source_texture_0_metallic_roughness'] if family=='Skin' else ['Security_'+family+'_'+s for s in ['BaseColor','Normal','ORM']]
        for i,(key,pin,channel,sampler) in enumerate([
            (keys[0],'DiffuseAlbedo' if cloth else 'BaseColor','RGB',u.MaterialSamplerType.SAMPLERTYPE_COLOR),
            (keys[1],'Normal','RGB',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
            (keys[2],'Roughness','G',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
            node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSample,0,i*180)
            node.texture=textures[key];node.sampler_type=sampler;connect(node,channel,slab,pin)
            if i==0 and cloth:connect(node,'RGB',slab,'FuzzColor')
            if i==2 and not cloth:connect(node,'B',slab,'Metallic')
        if cloth:
            for pin,value in [('F0',.022),('FuzzAmount',.14 if family=='Uniform' else .10),('FuzzRoughness',.84)]:
                node=MEL.create_material_expression(mat,u.MaterialExpressionConstant,220,0);node.r=value;connect(node,'',slab,pin)
        if not MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output failed')
    mat.set_editor_property('two_sided',False);MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    errors=MEL.recompile_material(mat)
    if errors:raise RuntimeError('Material compile error '+str(errors))
    save(mat);materials['Security_'+family]=mat
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
meshes={}
for role,name in [('outfit','SK_FacelessSecurity_V01'),('clothing','SK_FacelessSecurity_Clothing_V01'),('body','SK_FacelessSecurity_Body_V01')]:
    mesh=import_one(ROOT/'Delivery'/(name+'.fbx'),DEST,name,options)
    slots=list(mesh.materials)
    for slot in slots:
        imported=str(slot.get_editor_property('imported_material_slot_name'))
        chosen=next((mat for key,mat in materials.items() if imported.startswith(key)),None)
        if not chosen:raise RuntimeError('Unknown material slot '+imported)
        slot.material_interface=chosen
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'Source','User Meshy athletic male GLB; independent local security uniform; native humanoid rig')
    LIB.set_metadata_tag(mesh,'Status','Saved V01 candidate; not rendered or gameplay tested')
    save(mesh);meshes[role]=mesh
clips={}
for role in ['idle','walk','attack']:
    clip=copy_asset('/Game/Monsters/NurseZombie/A_Nurse_'+role,'Animations/A_Security_'+role)
    if not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):raise RuntimeError('Native animation rebind failed')
    clip.set_preview_skeletal_mesh(meshes['outfit']);save(clip);clips[role]=clip
save(skeleton)
bp=copy_asset('/Game/Monsters/NurseZombie/BP_NurseZombie','BP_FacelessSecurity')
u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',meshes['outfit']);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(meshes['outfit'])
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
tags=[t for t in cdo.get_editor_property('tags') if str(t) not in ['NurseZombie','FacelessReceptionist','FacelessSecurity']]
tags.append(u.Name('FacelessSecurity'));cdo.set_editor_property('tags',tags)
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),meshes={k:v.get_path_name() for k,v in meshes.items()},
    animations={k:v.get_path_name() for k,v in clips.items()},skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),
    navigation='Inherited existing Nurse humanoid capsule and supported navigation agent; no level edits',
    combat='Inherited Nurse gameplay and timing; no new combat abilities or numbers',clothing='Skinned independent source garments; consolidated runtime render mesh; no Chaos simulation')
record();print('SECURITY_UE_SAVED '+json.dumps({'saved_count':len(report['saved']),'blueprint':report['blueprint']}),flush=True)
