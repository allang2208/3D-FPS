"""Save the selected Meshy guard and original PBR; publish only after saves."""
from pathlib import Path
import json,shutil,unreal as u
P=Path(__file__).resolve().parent;ROOT=P.parents[2]
D='/Game/Weapons/AzureRunesword20260913/StarfallGuard20261030/MeshyV2'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
REV='StarfallMeshyV2-20261031';TAG='StarfallSourceRevision'
receipt={'complete':False,'saved_assets':[],'temporal_materials':{},'material_recipes':{},'gameplay_tested':False,'editor_launched_by_task':False}
def record():(P/'asset-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def owned(path):
    obj=u.load_asset(path)
    if obj and E.get_metadata_tag(obj,TAG)!=REV:raise RuntimeError('Preserve existing unowned asset '+path)
    return obj
def saved(obj):
    E.set_metadata_tag(obj,TAG,REV)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())
    receipt['saved_assets'].append(obj.get_path_name());record();return obj
def existing(obj):
    receipt['saved_assets'].append(obj.get_path_name());record();return obj
def import_new(file,name,options=None):
    obj=owned(D+'/'+name)
    if obj:return obj
    t=u.AssetImportTask();t.filename=str(file);t.destination_path=D;t.destination_name=name;t.automated=True;t.replace_existing=False;t.save=False
    if options:t.options=options
    A.import_asset_tasks([t]);obj=u.load_asset(D+'/'+name)
    if not obj or not t.imported_object_paths:raise RuntimeError('Import failed '+name)
    return obj
textures={}
for kind in ['BaseColor','Normal','MetallicRoughness']:
    name='T_StarfallMeshy_'+kind;tex=owned(D+'/'+name)
    if tex:textures[kind]=existing(tex);continue
    tex=import_new(P/'Textures'/(name+'.png'),name)
    tex.set_editor_property('srgb',kind=='BaseColor');tex.set_editor_property('never_stream',False)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if kind=='Normal' else u.TextureCompressionSettings.TC_DEFAULT if kind=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_WORLD_NORMAL_MAP if kind=='Normal' else u.TextureGroup.TEXTUREGROUP_WORLD)
    if kind=='Normal':tex.set_editor_property('flip_green_channel',True)
    textures[kind]=saved(tex)
def material(kind,temporal=False):
    name='M_StarfallMeshy_'+kind+('_Whirlwind' if temporal else '')
    mat=owned(D+'/'+name)
    if mat:return existing(mat)
    mat=A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_skeletal_mesh',False);mat.set_editor_property('automatically_set_usage_in_editor',False)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    mat.set_editor_property('two_sided',False);mat.set_editor_property('tangent_space_normal',True)
    def node(cls,**props):
        n=L.create_material_expression(mat,cls)
        for key,value in props.items():n.set_editor_property(key,value)
        return n
    def wire(src,dst,pin,channel=''):
        names=[str(n) for n in L.get_material_expression_input_names(dst)];norm=lambda s:s.replace(' ','').replace('_','').lower()
        actual=next((n for n in names if norm(n)==norm(pin)),None)
        if actual is None and pin=='Input' and len(names)==1:actual=names[0]
        if actual is None or not L.connect_material_expressions(src,channel,dst,actual):raise RuntimeError('Material pin '+pin+' '+str(names))
    def out(n,key,channel=''):
        if not L.connect_material_property(n,channel,getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError('Output '+key)
    def const(value):return node(u.MaterialExpressionConstant,r=float(value))
    def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=float(value))
    def vector(name,value):return node(u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1))
    def custom(label,code,inputs,width=1):
        n=node(u.MaterialExpressionCustom,description=label,code=code,output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
        pins=[]
        for name in inputs:
            p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
        n.set_editor_property('inputs',pins)
        for name,s in inputs.items():wire(s,n,name)
        return n
    uv=node(u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    def sample(kind,coords=uv):
        st=u.MaterialSamplerType.SAMPLERTYPE_NORMAL if kind=='Normal' else u.MaterialSamplerType.SAMPLERTYPE_COLOR if kind=='BaseColor' else u.MaterialSamplerType.SAMPLERTYPE_MASKS
        n=node(u.MaterialExpressionTextureSample,texture=textures[kind],sampler_type=st);wire(coords,n,'UVs');return n
    if kind=='Join':
        out(vector('BaseColor',(.12,.14,.17)),'BASE_COLOR','RGB');out(const(.9),'METALLIC');out(const(.3),'ROUGHNESS')
        # A true flat vector, never Engine/DefaultNormal (which contains texture detail).
        out(vector('FlatNormal',(0,0,1)),'NORMAL','RGB')
        recipe={'surface':'Small new interface caps; flat tangent-space normal'}
    else:
        base=sample('BaseColor');mr=sample('MetallicRoughness');raw_normal=sample('Normal')
        normal=custom('Preserve Meshy normal; polished gemstone strength', 'return normalize(float3(N.xy*Strength,max(N.z,0.02)));',{'N':raw_normal,'Strength':scalar('NormalStrength',.35 if kind=='Sapphire' else 1.)},3)
        mask=custom('Blue crystal and star-line mask from the original atlas','return saturate((C.b-max(C.r,C.g)*1.10)*12)*smoothstep(0.025,0.16,C.b);',{'C':base})
        pulse=custom('Gentle 3.5 second pulse','return .86+.14*sin(T*1.795195802);',{'T':node(u.MaterialExpressionTime)})
        emission=custom('Local crystal glow; preserve baked star contrast','return C.rgb*Mask*Pulse*Gain;',{'C':base,'Mask':mask,'Pulse':pulse,'Gain':scalar('GlowStrength',.95 if kind=='Sapphire' else .24)},3)
        if kind=='Body':
            metallic=custom('Original glTF blue metallic channel, dielectric blue crystal','return saturate(M.b)*(1-Mask);',{'M':mr,'Mask':mask})
            rough=custom('Original glTF green roughness channel','return clamp(M.g,.16,.78);',{'M':mr})
            out(base,'BASE_COLOR','RGB');out(metallic,'METALLIC');out(rough,'ROUGHNESS');out(normal,'NORMAL');out(emission,'EMISSIVE_COLOR')
            recipe={'base':'Original 4K BaseColor','normal':'Original 4K Normal, +Y converted for UE','metallic':'Original packed B; crystal mask dielectric','roughness':'Original packed G, .16-.78','glow':'Only blue inlays/crystal pixels, weak 3.5 s pulse'}
        else:
            view=node(u.MaterialExpressionTransform,transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_TANGENT)
            wire(node(u.MaterialExpressionCameraVectorWS),view,'Input')
            interior_uv=custom('Atlas-safe optical depth','float3 r=refract(-normalize(V),normalize(N),1.0/1.76);return UV+r.xy/max(abs(r.z),.4)*.00025;',{'V':view,'N':normal,'UV':uv},2)
            interior=sample('BaseColor',interior_uv)
            crystal=custom('Retain Meshy star artwork, shallow optical layer','return lerp(C.rgb,C.rgb*.82+I.rgb*.18,Mask);',{'C':base,'I':interior,'Mask':mask},3)
            slab=node(u.MaterialExpressionSubstrateSlabBSDF)
            wire(crystal,slab,'Diffuse Albedo');wire(const(.0758),slab,'F0');wire(const(1),slab,'F90');wire(const(.12),slab,'Roughness');wire(normal,slab,'Normal');wire(emission,slab,'Emissive Color')
            coat=node(u.MaterialExpressionSubstrateSlabBSDF)
            wire(vector('CoatDiffuse',(0,0,0)),coat,'Diffuse Albedo');wire(const(.04),coat,'F0');wire(const(1),coat,'F90');wire(const(.055),coat,'Roughness');wire(normal,coat,'Normal')
            mfp=node(u.MaterialExpressionSubstrateTransmittanceToMFP);thick=const(.003)
            wire(vector('CoatTransmittance',(.995,.998,1)),mfp,'TransmittanceColor');wire(thick,mfp,'Thickness');wire(mfp,coat,'SSS MFP','MFP')
            layer=node(u.MaterialExpressionSubstrateVerticalLayering,use_parameter_blending=False);wire(coat,layer,'Top');wire(slab,layer,'Bottom');wire(thick,layer,'Top Thickness');out(layer,'FRONT_MATERIAL')
            recipe={'base':'Original blue star artwork retained','normal':'Original normal x .35','metallic':0,'coat':'Explicit Substrate clear top layer','optics':'Atlas-safe subtle internal shift, opaque backing; no scene transparency','glow':'Masked 3.5 s blue pulse'}
    if temporal:wire(const(1),node(u.MaterialExpressionTemporalResponsivenessOutput),'Input')
    errors=L.recompile_material(mat)
    if errors:raise RuntimeError('Shader compilation failed '+name+': '+str(errors))
    receipt['material_recipes'][mat.get_path_name()]=recipe;saved(mat);return mat
materials={}
for kind in ['Body','Sapphire','Join']:
    main=material(kind);temp=material(kind,True);materials['M_StarfallMeshy_'+kind]=main
    receipt['temporal_materials'][main.get_path_name()]=temp.get_path_name();record()
mesh_name='SM_RuneSword_Guard_Starfall_MeshyV2';mesh=owned(D+'/'+mesh_name)
if mesh:existing(mesh)
else:
    world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    if world:u.SystemLibrary.execute_console_command(world,'Interchange.FeatureFlags.Import.FBX 0')
    cfg=u.FbxImportUI();cfg.automated_import_should_detect_type=False;cfg.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    cfg.import_mesh=True;cfg.import_as_skeletal=False;cfg.import_materials=False;cfg.import_textures=False;cfg.import_animations=False
    data=cfg.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False;data.generate_lightmap_u_vs=False;data.build_nanite=False
    data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.0
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    mesh=import_new(P/'SM_RuneSword_Guard_Starfall_MeshyV2.fbx',mesh_name,cfg)
    native=u.load_asset('/Game/Weapons/AzureRunesword20260913/M_AzureRunesword')
    for i,slot in enumerate(mesh.static_materials):
        key=str(slot.material_slot_name);mat=native if key=='M_AzureRunesword' else materials[key];mesh.set_material(i,mat)
    subsystem=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    settings=subsystem.get_lod_build_settings(mesh,0);settings.recompute_normals=False;settings.recompute_tangents=False;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    subsystem.set_lod_build_settings(mesh,0,settings);saved(mesh)
receipt['mesh']=mesh.get_path_name()
bounds=mesh.get_bounds()
receipt['mesh_dimensions_cm']=[bounds.box_extent.x*2,bounds.box_extent.y*2,bounds.box_extent.z*2]
receipt['mesh_triangles']=mesh.get_num_triangles(0)
receipt['mesh_slots']=[str(slot.material_slot_name) for slot in mesh.static_materials]
record()

# Icon has a stable runtime key: back up that exact asset before the authorized update.
key='guard_starfall_nexus_guard';icon_dir=ROOT/'Content/ColdSteelData/AttachmentIcons20260913';before=P/'Before';before.mkdir(exist_ok=True)
for ext in ['.png','.uasset']:
    old=icon_dir/(key+ext)
    if old.exists() and not (before/(key+ext)).exists():shutil.copy2(old,before/(key+ext))
shutil.copy2(P/(key+'.png'),icon_dir/(key+'.png'))
t=u.AssetImportTask();t.filename=str(icon_dir/(key+'.png'));t.destination_path='/Game/ColdSteelData/AttachmentIcons20260913';t.destination_name=key;t.automated=True;t.replace_existing=True;t.save=False
A.import_asset_tasks([t]);icon=u.load_asset(t.destination_path+'/'+key)
if not icon or not t.imported_object_paths:raise RuntimeError('Icon import failed')
icon.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_UI);icon.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_EDITOR_ICON);icon.set_editor_property('srgb',True);icon.set_editor_property('never_stream',True);icon.set_editor_property('mip_gen_settings',u.TextureMipGenSettings.TMGS_NO_MIPMAPS);saved(icon)
receipt['icon']=icon.get_path_name();record()
def update_json(relative,fn):
    path=ROOT/relative;old=path.read_text(encoding='utf-8-sig');backup=before/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(path,backup)
    data=json.loads(old);fn(data)
    if path.read_text(encoding='utf-8-sig')!=old:raise RuntimeError('Concurrent catalog update: '+relative)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def switch(data):
    spec=data['slots']['guard']['starfall_nexus_guard'];spec['mesh']=mesh.get_path_name();spec['appearance']='Meshy 星陨天枢 · 银翼金纹与长菱星晶'
update_json('Content/ColdSteelData/rune-sword-modules.json',switch)
update_json('Content/ColdSteelData/whirlwind-temporal-materials.json',lambda data:data.update(receipt['temporal_materials']))
receipt['complete']=True;record();print('STARFALL_MESHY_V2_SAVED',len(receipt['saved_assets']))
