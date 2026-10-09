"""Background import into an independent security namespace; no game/preview tests."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessResearcher20261009/V01')
DEST='/Game/Monsters/FacelessResearcher'
LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools();MEL=u.MaterialEditingLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE is active; researcher import not started')

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
skeleton=copy_asset('/Game/ZombieFemale/Asset/Meshes/SK_ZombieFemale','SKEL_FacelessResearcher')
physics=copy_asset('/Game/ZombieFemale/Asset/Meshes/PA_ZombieFemale','PA_FacelessResearcher')
save(skeleton);save(physics)
textures={}
for file in sorted((ROOT/'Textures').glob('*.png')):
    name='T_FRS1_'+file.stem;tex=import_one(file,DEST+'/Textures',name)
    is_normal='_Normal' in file.stem or file.stem=='Source_normal'
    is_data=is_normal or '_ORM' in file.stem or 'metallic_roughness' in file.stem
    tex.set_editor_property('srgb',not is_data);tex.set_editor_property('never_stream',False)
    if is_normal:
        tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP);tex.set_editor_property('flip_green_channel',True)
    elif is_data:tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_MASKS)
    save(tex);textures[file.stem]=tex
materials={}
for family in ['Skin','Coat','Trousers','Trim','Hardware','Leather']:
    name='M_FRS1_'+family;path=DEST+'/Materials/'+name
    if LIB.does_asset_exist(path):mat=u.load_asset(path)
    else:
        mat=AT.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew())
        cloth=family in ['Coat','Trousers','Trim','Insignia']
        slab=MEL.create_material_expression(mat,u.MaterialExpressionSubstrateSlabBSDF if cloth else u.MaterialExpressionSubstrateShadingModels,450,0)
        keys=['Source_texture_0','Source_normal','Source_texture_0_metallic_roughness'] if family=='Skin' else ['Researcher_'+family+'_'+s for s in ['BaseColor','Normal','ORM']]
        for i,(key,pin,channel,sampler) in enumerate([
            (keys[0],'DiffuseAlbedo' if cloth else 'BaseColor','RGB',u.MaterialSamplerType.SAMPLERTYPE_COLOR),
            (keys[1],'Normal','RGB',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),
            (keys[2],'Roughness','G',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]):
            node=MEL.create_material_expression(mat,u.MaterialExpressionTextureSample,0,i*180)
            node.texture=textures[key];node.sampler_type=sampler;connect(node,channel,slab,pin)
            if i==0 and cloth:connect(node,'RGB',slab,'FuzzColor')
            if i==2 and not cloth:connect(node,'B',slab,'Metallic')
        if cloth:
            for pin,value in [('F0',.022),('FuzzAmount',.14 if family=='Coat' else .10),('FuzzRoughness',.84)]:
                node=MEL.create_material_expression(mat,u.MaterialExpressionConstant,220,0);node.r=value;connect(node,'',slab,pin)
        if not MEL.connect_material_property(slab,'',u.MaterialProperty.MP_FRONT_MATERIAL):raise RuntimeError('Substrate output failed')
    mat.set_editor_property('two_sided',False);MEL.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH);mat.set_editor_property('used_with_morph_targets',True)
    errors=MEL.recompile_material(mat)
    if errors:raise RuntimeError('Material compile error '+str(errors))
    save(mat);materials['Researcher_'+family]=mat
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1
data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
data.set_editor_property('import_morph_targets',True)
meshes={}
for role,name in [('outfit','SK_FacelessResearcher_V01'),('clothing','SK_FacelessResearcher_Clothing_V01'),('body','SK_FacelessResearcher_Body_V01')]:
    mesh=import_one(ROOT/'Delivery'/(name+'.fbx'),DEST,name,options)
    slots=list(mesh.materials)
    for slot in slots:
        imported=str(slot.get_editor_property('imported_material_slot_name'))
        chosen=next((mat for key,mat in materials.items() if imported.startswith(key)),None)
        if not chosen:raise RuntimeError('Unknown material slot '+imported)
        slot.material_interface=chosen
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'Source','User reduced Meshy female GLB; independent fitted lab coat and trousers; original Nurse skeleton')
    LIB.set_metadata_tag(mesh,'Status','Saved V01 candidate; not rendered or gameplay tested')
    save(mesh);meshes[role]=mesh

# Appended to the material/mesh importer; executed in the existing UE mutex.
source=json.loads((ROOT/'nurse_source.json').read_text(encoding='utf-8'))
fit=json.loads((ROOT/'placement_manifest.json').read_text(encoding='utf-8'))
curves=json.loads((ROOT/'corrective_curves.json').read_text(encoding='utf-8'))
curve_manifest=json.loads((ROOT/'corrective_manifest.json').read_text(encoding='utf-8'))
requested=json.loads((ROOT/'export_receipt.json').read_text(encoding='utf-8'))['morph_names']
actual=[m.get_name() for m in meshes['outfit'].get_editor_property('morph_targets')];mapping={}
for name in requested:
    matches=[n for n in actual if n==name or n.endswith('_'+name)]
    if len(matches)!=1:raise RuntimeError('Morph import did not produce '+name)
    mapping[name]=matches[0]
clips={}
for role in ['idle','walk','attack']:
    clip=copy_asset(source['clips'][role]['source'],'Animations/A_Researcher_'+role)
    if not u.WeaponAnimationAuthoring.rebind_native_animation(clip,skeleton):raise RuntimeError('Cannot attach Nurse tracks to independent researcher skeleton')
    clip.set_preview_skeletal_mesh(meshes['outfit'])
    if role=='walk':clip.set_editor_property('rate_scale',source['clips'][role]['rate_scale']/fit['component_scale'])
    frames=curve_manifest[role]['frames'];duration=clip.get_play_length()
    for name,values in curves[role].items():
        target=mapping[name]
        if u.AnimationLibrary.does_curve_exist(clip,target,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,target)
        u.AnimationLibrary.add_curve(clip,target)
        times=[i*duration/(frames-1) for i in range(frames)]
        u.AnimationLibrary.add_float_curve_keys(clip,target,times,values)
        u.AnimationLibrary.set_curve_meta_data_morph_target(skeleton,target,True)
    LIB.set_metadata_tag(clip,'ResearcherSourceMotion',source['clips'][role]['source'])
    LIB.set_metadata_tag(clip,'ResearcherTailoring','Original Nurse bone tracks; independent motion-driven coat clearance curves')
    save(clip);clips[role]=clip
save(skeleton)
bp=copy_asset('/Game/Monsters/NurseZombie/BP_NurseZombie','BP_FacelessResearcher')
u.BlueprintEditorLibrary.compile_blueprint(bp);cdo=u.get_default_object(bp.generated_class())
cdo.set_editor_property('visual_mesh',meshes['outfit']);component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(meshes['outfit'])
for role,clip in clips.items():cdo.set_editor_property(role+'_clip',clip)
for key,value in source['properties'].items():cdo.set_editor_property(key,value)
# Native body bindings share Nurse proportions and animations. A small uniform
# component scale gives the designed researcher height without nonuniform bones.
scale=fit['component_scale'];component.set_relative_scale3d(u.Vector(scale,scale,scale))
cdo.get_editor_property('capsule_component').set_capsule_half_height(fit['capsule_half_height_cm'],False)
component.set_relative_location(u.Vector(0,0,fit['mesh_relative_z_cm']),False,False)
tags=[t for t in cdo.get_editor_property('tags') if str(t) not in ['NurseZombie','FacelessReceptionist','FacelessSecurity','FacelessResearcher']]
tags.append(u.Name('FacelessResearcher'));cdo.set_editor_property('tags',tags)
LIB.set_metadata_tag(bp,'ResearcherRevision','V01 high slender faceless researcher; continuous lab coat, paired walls, closed shoes and Nurse motions')
LIB.set_metadata_tag(bp,'SourceGLB','Meshy_AI_Gray_Full_Body_Manneq_1009014620_texture.glb')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
report.update(stage='saved',blueprint=bp.get_path_name(),meshes={k:v.get_path_name() for k,v in meshes.items()},
    animations={k:v.get_path_name() for k,v in clips.items()},skeleton=skeleton.get_path_name(),physics=physics.get_path_name(),
    source_motion=source,placement=fit,morph_names=mapping,
    clothing='Independent continuous coat, trouser and shoe source meshes; consolidated runtime skin; offline corrective shapes; no runtime cloth solver',
    complete_body_preserved=True,runtime_tested=False,rendered=False)
record();print('RESEARCHER_UE_SAVED '+json.dumps({'saved_count':len(report['saved']),'blueprint':report['blueprint']}),flush=True)
