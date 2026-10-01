"""Background import/save of the authored HK416 mesh, fittings and animations."""
import unreal as u,ast,copy,hashlib,json,re
from pathlib import Path
from runpy import run_path
O=Path(__file__).parent;P=O.parents[1];ROOT='/Game/Weapons/HK416/Reworked20260930'
apply_current_bindings=run_path(str(P/'SourceAssets/WeaponSurface20260930/HK416/current_bindings.py'))['apply_current_bindings']
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
auth=json.loads((O/'authoring.json').read_text());report={'saved':[],'materials':{},'static':{},'animations':{},'runtime_tested':False}
def record():(O/'import_receipt.json').write_text(json.dumps(report,indent=2))
def load(path):
    asset=u.load_asset(path)
    if not asset:raise RuntimeError('Missing HK416 dependency '+path)
    return asset
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('HK416 save failed '+asset.get_path_name())
    if asset.get_path_name() not in report['saved']:report['saved'].append(asset.get_path_name())
    record();return asset
def create(name,folder,cls,factory):
    return load(folder+'/'+name) if E.does_asset_exist(folder+'/'+name) else A.create_asset(name,folder,cls,factory)
def imported(file,folder,name,options=None):
    path=folder+'/'+name;digest=hashlib.sha256(Path(file).read_bytes()).hexdigest()
    if E.does_asset_exist(path):
        previous=load(path)
        if E.get_metadata_tag(previous,'HK416SourceSHA256')==digest:return previous
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    if options:task.options=options;task.factory=u.FbxFactory()
    A.import_asset_tasks([task]);asset=load(path);E.set_metadata_tag(asset,'HK416SourceSHA256',digest);return save(asset)

tree=ast.parse((P/'Tools/Weather/build_natural_weather.py').read_text(encoding='utf8'))
helpers={'unreal':u,'LIB':L};wanted={'node','wire','prop','scalar','constant','vector','custom'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in wanted],type_ignores=[]),'HK416 material helpers','exec'),helpers)
node,custom,prop,scalar,constant,vector=[helpers[k] for k in ('node','custom','prop','scalar','constant','vector')]
textures={}
for file in sorted((O/'Original/textures').iterdir()):
    tex=imported(file,ROOT+'/Textures','T_HK416_'+file.stem);normal=file.stem.endswith('_normal')
    color=file.stem.endswith(('_albedo','_emissive'))
    tex.srgb=color;tex.compression_settings=u.TextureCompressionSettings.TC_NORMALMAP if normal else u.TextureCompressionSettings.TC_DEFAULT if color else u.TextureCompressionSettings.TC_MASKS
    tex.lod_group=u.TextureGroup.TEXTUREGROUP_WEAPON_NORMAL_MAP if normal else u.TextureGroup.TEXTUREGROUP_WEAPON
    if normal:tex.flip_green_channel=True
    save(tex);textures[file.stem]=tex

materials={};wetmap={}
for name,group in auth['material_groups'].items():
    mat=create(name,ROOT+'/Materials',u.Material,u.MaterialFactoryNew())
    # Delete from a snapshot: UE 5.8's bulk helper removes entries while iterating
    # its live array and can leave old texture nodes behind during a rebuild.
    for old_expression in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat,old_expression)
    samples={}
    for suffix in ('albedo','metallic','roughness','normal','AO','emissive','opacity'):
        if group+'_'+suffix not in textures:continue
        tex=node(mat,u.MaterialExpressionTextureSample);tex.texture=textures[group+'_'+suffix]
        tex.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if suffix=='normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if suffix in ('albedo','emissive') else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        samples[suffix]=tex
    glass='Glass' in name;reticle='Reticle' in name
    skeletal=group in ('Upper_Body','Lower_Body','Stock','Muzzle') or name.endswith('_Magazine')
    mat.set_editor_property('used_with_skeletal_mesh',skeletal)
    if skeletal:L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    if reticle:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_ADDITIVE);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT);mat.set_editor_property('two_sided',True)
        prop(custom(mat,'return Emission*6;',dict(Emission=samples['emissive']),3,'Original HK416 reticle'),'EMISSIVE_COLOR')
    elif glass:
        mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT);mat.set_editor_property('two_sided',True)
        prop(samples['albedo'],'BASE_COLOR');prop(samples['normal'],'NORMAL')
        L.connect_material_property(samples['roughness'],'R',u.MaterialProperty.MP_ROUGHNESS)
        prop(custom(mat,'return .08+Mask.r*.2;',dict(Mask=samples['opacity']),1,'Lens transmission'),'OPACITY')
    else:
        wet=scalar(mat,'WeaponWetness',0);uv=node(mat,u.MaterialExpressionTextureCoordinate)
        beads=custom(mat,(P/'SourceAssets/WeatherNatural20260912/WeaponBeads.hlsl').read_text(),dict(UV=uv,Wet=wet),4,'HK416 rain beads')
        prop(custom(mat,'return Base*(1-Data.a*.07);',dict(Base=samples['albedo'],Data=beads),3),'BASE_COLOR')
        prop(custom(mat,'return lerp(lerp(Base.r,max(.085,Base.r*.70),Data.a),.065,Data.b*.8);',dict(Base=samples['roughness'],Data=beads),1),'ROUGHNESS')
        prop(custom(mat,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=samples['normal'],Data=beads),3),'NORMAL')
        L.connect_material_property(samples['metallic'],'R',u.MaterialProperty.MP_METALLIC)
        if 'AO' in samples:L.connect_material_property(samples['AO'],'R',u.MaterialProperty.MP_AMBIENT_OCCLUSION)
        if 'emissive' in samples:prop(custom(mat,'return Source*.2;',dict(Source=samples['emissive']),3),'EMISSIVE_COLOR')
        wetmap[mat.get_path_name()]=mat
    E.set_metadata_tag(mat,'Attribution','HK416 Full ReWorked by MojoLeeDa / Sketchfab 669a9ee17dc44580b53425a08c2f83d0 / CC BY 4.0; modified for FPSGAME')
    L.recompile_material(mat);save(mat);materials[name]=mat;report['materials'][name]=mat.get_path_name()

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag);u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
    mesh=imported(auth['mesh'],ROOT,'SK_HK416_Manny',opt)
    profiles=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))['profiles']
    profile=copy.deepcopy(next(v for v in profiles.values() if v.get('rig_profile')=='M4'))
    skin=load(profile['base']);skin_mats=dict(zip(('UpperArm','Forearm','Hand'),[x.material_interface for x in skin.materials]))
    slots=list(mesh.materials);arm_ids=[]
    for i,slot in enumerate(slots):
        name=re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))
        if 'Manny' in name:
            arm_ids.append(i);key=next((k for k in skin_mats if k.lower() in name.lower()),'Hand');slot.material_interface=skin_mats[key]
        else:slot.material_interface=materials[name]
        slots[i]=slot
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
    system=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    for lod in range(system.get_lod_count(mesh)):
        settings=system.get_lod_build_settings(mesh,lod);settings.use_full_precision_u_vs=True;system.set_lod_build_settings(mesh,lod,settings)
    apply_current_bindings(mesh)
    save(mesh);save(mesh.skeleton);report['mesh']=mesh.get_path_name();report['arm_materials']=arm_ids;record()
    for key,clip in auth['clips'].items():
        family,kind=key.split('/');file=Path(clip['fbx']);opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        anim=imported(file,ROOT+'/Animations/'+family,file.stem,opt)
        anim.set_editor_property('bone_compression_settings',load('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel'));save(anim)
        report['animations'][key]={'asset':anim.get_path_name(),'duration':anim.get_play_length()};record()
    for key,entry in auth['static'].items():
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.override_full_name=True
        opt.static_mesh_import_data.combine_meshes=True;opt.static_mesh_import_data.auto_generate_collision=False;opt.static_mesh_import_data.generate_lightmap_u_vs=False
        opt.static_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        part=imported(entry['fbx'],ROOT+'/Attachments','SM_HK416_'+key,opt);slots=list(part.static_materials)
        for i,slot in enumerate(slots):slot.material_interface=materials[re.sub(r'[._]\d{3}$','',str(slot.material_slot_name))];slots[i]=slot
        part.set_editor_property('static_materials',slots);apply_current_bindings(part);save(part);report['static'][key]=part.get_path_name();record()
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

file=O/'finish_publication.py'
exec(compile(file.read_text(encoding='utf-8'),str(file),'exec'),{'__file__':str(file),'__name__':'__main__'})
