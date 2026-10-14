"""Build isolated candidate packages. Never save the production map or shared materials."""
import unreal as u,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Authored';DEST='/Game/Props/GodSpaceCoreStarfield20261005';A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
assert not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
receipt={'saved':[],'compile_results':{}}
def save(o):
    o.modify();assert E.save_loaded_asset(o,False),o.get_path_name();receipt['saved'].append(o.get_path_name())
def tex(name,compression,srgb):
    path=DEST+'/Textures/'+name
    t=u.load_asset(path)
    signature=hashlib.sha256((OUT/'Textures'/(name+'.png')).read_bytes()).hexdigest()
    if not t or E.get_metadata_tag(t,'CoreStarfieldSource')!=signature:
        task=u.AssetImportTask();task.filename=str(OUT/'Textures'/(name+'.png'));task.destination_name=name;task.destination_path=DEST+'/Textures';task.factory=u.TextureFactory();task.automated=True;task.replace_existing=True;task.save=False
        A.import_asset_tasks([task]);t=u.load_asset(path);assert t,path
        t.set_editor_property('srgb',srgb);t.set_editor_property('compression_settings',compression);t.set_editor_property('virtual_texture_streaming',False)
        E.set_metadata_tag(t,'CoreStarfieldSource',signature);save(t)
    return t
textures={
 'star':tex('T_CoreStarfield_BaseColor',u.TextureCompressionSettings.TC_BC7,True),
 'stars':tex('T_CoreStars_Emissive',u.TextureCompressionSettings.TC_BC7,True),
 'gold':tex('T_CoreGold_BaseColor',u.TextureCompressionSettings.TC_BC7,True),
 'orm':tex('T_CoreGold_ORM',u.TextureCompressionSettings.TC_MASKS,False),
 'normal':tex('T_CoreGold_Normal',u.TextureCompressionSettings.TC_NORMALMAP,False)}
def node(m,cls,**props):
    n=L.create_material_expression(m,cls,0,0);assert n
    for k,v in props.items():n.set_editor_property(k,v)
    return n
def link(a,out,b,inp):assert L.connect_material_expressions(a,out,b,inp),(str(a),out,str(b),inp)
def output(m,a,out,prop):assert L.connect_material_property(a,out,prop),str(prop)
def scalar(m,name,value):return node(m,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
def vector(m,value):return node(m,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*value,1))
def constant(m,value):return node(m,u.MaterialExpressionConstant,r=value)
def start(name):
    path=DEST+'/Materials/'+name;m=u.load_asset(path)
    if m:
        if E.get_metadata_tag(m,'CoreStarfieldMaterialComplete')=='V1':return m,False
        # Recover only our unreferenced, unfinished candidate; no shared graph is touched.
        assert not E.find_package_referencers_for_asset(path,True),path
        L.delete_all_material_expressions(m)
        return m,True
    m=A.create_asset(name,DEST+'/Materials',u.Material,u.MaterialFactoryNew());assert m
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE);return m,True
def compile_save(m):
    errors=L.recompile_material(m);receipt['compile_results'][m.get_path_name()]=[str(x) for x in errors] if errors is not None else []
    assert not errors,errors
    E.set_metadata_tag(m,'CoreStarfieldMaterialComplete','V1');save(m)
star,new=start('M_CoreStarfield_V2')
if new:
    star.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    custom=node(star,u.MaterialExpressionCustom,code=(ROOT/'Shaders/Starfield.hlsl').read_text(),output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,description='Seam-safe opaque interior starfield')
    names=['Tex','Stars','P','C','V','Strength','StarStrength','Depth','Rim'];inputs=[]
    for name in names:
        item=u.CustomInput();item.set_editor_property('input_name',name);inputs.append(item)
    custom.set_editor_property('inputs',inputs)
    t=node(star,u.MaterialExpressionTextureObjectParameter,parameter_name='StarfieldMap',texture=textures['star'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    st=node(star,u.MaterialExpressionTextureObjectParameter,parameter_name='StarsMap',texture=textures['stars'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    links=[t,st,node(star,u.MaterialExpressionWorldPosition),node(star,u.MaterialExpressionObjectPositionWS),node(star,u.MaterialExpressionCameraVectorWS),scalar(star,'StarfieldStrength',1.65),scalar(star,'StarsStrength',3.0),scalar(star,'InteriorDepth',.65),scalar(star,'RimStrength',.9)]
    for n,name in zip(links,names):link(n,'',custom,name)
    output(star,custom,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
    output(star,vector(star,(.001,.002,.007)),'',u.MaterialProperty.MP_BASE_COLOR)
    output(star,scalar(star,'SurfaceRoughness',.34),'',u.MaterialProperty.MP_ROUGHNESS)
    output(star,constant(star,0),'',u.MaterialProperty.MP_METALLIC)
    output(star,scalar(star,'SurfaceSpecular',.025),'',u.MaterialProperty.MP_SPECULAR)
    compile_save(star)
gold,new=start('M_CoreEngravedGold_V2')
if new:
    uv=node(gold,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    for key,sampler,prop,pin in [('gold',u.MaterialSamplerType.SAMPLERTYPE_COLOR,u.MaterialProperty.MP_BASE_COLOR,'RGB'),('normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,u.MaterialProperty.MP_NORMAL,'RGB')]:
        n=node(gold,u.MaterialExpressionTextureSample,texture=textures[key],sampler_type=sampler);link(uv,'',n,'UVs');output(gold,n,pin,prop)
    orm=node(gold,u.MaterialExpressionTextureSample,texture=textures['orm'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    link(uv,'',orm,'UVs')
    for pin,prop in [('R',u.MaterialProperty.MP_AMBIENT_OCCLUSION),('G',u.MaterialProperty.MP_ROUGHNESS),('B',u.MaterialProperty.MP_METALLIC)]:output(gold,orm,pin,prop)
    compile_save(gold)
gem,new=start('M_CoreSapphire_V2')
if new:
    gem.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for val,prop in [((.004,.032,.19),u.MaterialProperty.MP_BASE_COLOR),((.002,.025,.10),u.MaterialProperty.MP_EMISSIVE_COLOR)]:output(gem,vector(gem,val),'',prop)
    for val,prop in [(.13,u.MaterialProperty.MP_ROUGHNESS),(.15,u.MaterialProperty.MP_METALLIC)]:output(gem,constant(gem,val),'',prop)
    compile_save(gem)
materials={}
for key,parent in [('Core_Starfield',star),('Core_EngravedGold',gold),('Core_Sapphire',gem)]:
    name='MI_'+key+'_V2';mi=u.load_asset(DEST+'/Materials/'+name)
    if not mi:
        mi=A.create_asset(name,DEST+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew());L.set_material_instance_parent(mi,parent);L.update_material_instance(mi);save(mi)
    materials[key]=mi
meshpath=DEST+'/Meshes/SM_GodSpaceCore_Starfield_V2';fbx=OUT/'SM_GodSpaceCore_Starfield_V2.fbx';sig=hashlib.sha256(fbx.read_bytes()).hexdigest();mesh=u.load_asset(meshpath)
if not mesh or E.get_metadata_tag(mesh,'CoreStarfieldSource')!=sig:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    d=opt.static_mesh_import_data;d.combine_meshes=True;d.convert_scene=True;d.convert_scene_unit=True;d.transform_vertex_to_absolute=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=str(fbx);task.destination_name=meshpath.rsplit('/',1)[1];task.destination_path=DEST+'/Meshes';task.factory=u.FbxFactory();task.options=opt;task.automated=True;task.replace_existing=True;task.save=False
    A.import_asset_tasks([task]);mesh=u.load_asset(meshpath);assert mesh
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        key=str(slot.material_slot_name);assert key in materials,key;mesh.set_material(i,materials[key])
    original=u.load_asset('/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceCore')
    mesh.set_editor_property('nanite_settings',original.get_editor_property('nanite_settings'))
    ob=original.get_bounds();b=mesh.get_bounds();low=b.origin-b.box_extent;high=b.origin+b.box_extent;olo=ob.origin-ob.box_extent;ohi=ob.origin+ob.box_extent
    assert (b.origin-ob.origin).length()<.1,(str(b),str(ob))
    assert all(getattr(b.box_extent,k)<=getattr(ob.box_extent,k)+.02 for k in ['x','y','z']),str(b)
    mesh.set_editor_property('negative_bounds_extension',u.Vector(*[max(0,getattr(low,k)-getattr(olo,k)) for k in ['x','y','z']]))
    mesh.set_editor_property('positive_bounds_extension',u.Vector(*[max(0,getattr(ohi,k)-getattr(high,k)) for k in ['x','y','z']]))
    E.set_metadata_tag(mesh,'CoreStarfieldSource',sig);save(mesh)
receipt.update(candidate_mesh=mesh.get_path_name(),bounds=str(mesh.get_bounds()),materials={k:v.get_path_name() for k,v in materials.items()},texture_sizes={k:[t.blueprint_get_size_x(),t.blueprint_get_size_y()] for k,t in textures.items()},production_mesh_modified=False,source_sha256=sig)
(ROOT/'Receipts').mkdir(exist_ok=True);(ROOT/'Receipts/candidate_import.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt))
