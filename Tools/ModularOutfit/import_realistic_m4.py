"""Build and save the M4-only candidate. No PIE, screenshots or test playback."""
import json, hashlib
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/ModularOutfit20260924/RealisticM4Candidate'
DEST='/Game/Characters/ModularOutfit20260924/RealisticM4Candidate'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish play mode before saving the hand candidate')
saved=[]
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    saved.append(asset.get_path_name())

texture=u.load_asset(DEST+'/T_M4BareArms_Colour')
if not texture:
    task=u.AssetImportTask()
    task.filename=str(ROOT/'Donor/young_lightskinned_male_diffuse.png')
    task.destination_path=DEST;task.destination_name='T_M4BareArms_Colour'
    task.automated=True;task.save=True;task.replace_existing=False
    A.import_asset_tasks([task])
    texture=u.load_asset(DEST+'/T_M4BareArms_Colour')
if not texture:raise RuntimeError('Cannot import licensed skin colour')
texture.set_editor_property('srgb',True)
texture.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER)
save(texture)

profile=u.load_asset(DEST+'/SSP_M4BareArms')
if not profile:
    profile=A.create_asset('SSP_M4BareArms',DEST,u.SubsurfaceProfile,u.SubsurfaceProfileFactory())
    settings=profile.get_editor_property('settings')
    settings.set_editor_property('surface_albedo',u.LinearColor(.45,.28,.21,1))
    settings.set_editor_property('enable_burley',True)
    settings.set_editor_property('mean_free_path_distance',.9)
    profile.set_editor_property('settings',settings)
save(profile)
material=u.load_asset(DEST+'/M_M4BareArms')
if not material:
    material=A.create_asset('M_M4BareArms',DEST,u.Material,u.MaterialFactoryNew())
    def node(cls,**props):
        n=L.create_material_expression(material,cls)
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def scalar(name,value):return node(u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value)
    def out(n,pin,prop):
        if not L.connect_material_property(n,pin,prop):raise RuntimeError('Material connection failed '+str(prop))
    colour=node(u.MaterialExpressionTextureSampleParameter2D,parameter_name='SkinColour',texture=texture,
        sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    tint=node(u.MaterialExpressionVectorParameter,parameter_name='SkinTint',default_value=u.LinearColor(1,1,1,1))
    multiply=node(u.MaterialExpressionMultiply)
    L.connect_material_expressions(colour,'RGB',multiply,'A');L.connect_material_expressions(tint,'',multiply,'B')
    out(multiply,'',u.MaterialProperty.MP_BASE_COLOR)
    inputs={'UV':node(u.MaterialExpressionTextureCoordinate),'PoreTiling':scalar('PoreTiling',1500),
        'SkinRoughness':scalar('SkinRoughness',.5),'DetailStrength':scalar('DetailStrength',.035)}
    detail=node(u.MaterialExpressionCustom,code=(ROOT/'skin_detail.hlsl').read_text(encoding='utf-8'),
        output_type=u.CustomMaterialOutputType.CMOT_FLOAT3,description='Derivative-filtered skin detail')
    custom=[]
    for n in inputs:
        item=u.CustomInput();item.set_editor_property('input_name',n);custom.append(item)
    detail.set_editor_property('inputs',custom)
    rough=u.CustomOutput();rough.set_editor_property('output_name','OutRoughness')
    rough.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
    detail.set_editor_property('additional_outputs',[rough])
    for n,expression in inputs.items():L.connect_material_expressions(expression,'',detail,n)
    out(detail,'',u.MaterialProperty.MP_NORMAL);out(detail,'OutRoughness',u.MaterialProperty.MP_ROUGHNESS)
    out(scalar('SkinSpecular',.35),'',u.MaterialProperty.MP_SPECULAR)
    out(scalar('ScatterStrength',.13),'',u.MaterialProperty.MP_OPACITY)
    out(node(u.MaterialExpressionConstant,r=0),'',u.MaterialProperty.MP_METALLIC)
    material.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE_PROFILE)
    material.set_editor_property('subsurface_profile',profile)
    L.set_material_usage(material,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    L.layout_material_expressions(material)
    errors=L.recompile_material(material)
    if errors:raise RuntimeError('Material build failed '+str(errors))
    E.set_metadata_tag(material,'M4RealisticBareArms','Candidate1')
save(material)
instance=u.load_asset(DEST+'/MI_M4BareArms')
if not instance:
    instance=A.create_asset('MI_M4BareArms',DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(instance,material);L.update_material_instance(instance)
save(instance)

author=(ROOT/'M4_skin.json').read_bytes();d=json.loads(author)
source=u.load_asset(d['source'])
if not source:raise RuntimeError('Missing original M4 source')
src,result=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot copy native M4 reference')
_,bones=B.get_all_bones_info(src);indices={str(b.name):b.index for b in bones}
dm=u.DynamicMesh()
buffers=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*v) for v in d['vertices']],
    normals=[u.Vector(*v) for v in d['normals']],uv0=[u.Vector2D(*v) for v in d['uv']],
    triangles=[u.IntVector(*v) for v in d['triangles']])
u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buffers,0,True)
B.copy_bones_from_mesh(src,dm);B.mesh_create_bone_weights(dm)
for i,w in enumerate(d['weights']):
    B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=indices[n],weight=v) for n,v in w.items()])
name='SK_M4_RealisticBareArms_Candidate';mesh=u.load_asset(DEST+'/'+name)
if not mesh:mesh=A.duplicate_asset(name,DEST,source)
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[instance],
    new_material_slot_names=['ContinuousSkin'],enable_recompute_normals=False,enable_recompute_tangents=True,
    bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,result=G.copy_mesh_to_skeletal_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD())
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save candidate geometry')
mesh.set_editor_property('physics_asset',None)
if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('Cannot author candidate LODs')
if not u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(mesh,3,True,False):
    raise RuntimeError('Cannot build candidate LODs')
E.set_metadata_tag(mesh,'CandidateScope','M4 only; manual opt-in; animations unchanged')
save(mesh)

# Publish only after UE packages exist. Preserve all other profiles/recipes and
# the original default selected by the user, even after subsequent reimports.
config_path=PROJECT/'Content/ColdSteelData/modular_outfits.json'
config=json.loads(config_path.read_text(encoding='utf-8-sig'))
config['profiles'][source.get_path_name()]['bare_arms_candidate']=mesh.get_path_name()
config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
report={'profile':'M4','mesh':mesh.get_path_name(),'source':source.get_path_name(),'skeleton':source.skeleton.get_path_name(),
    'author_sha256':hashlib.sha256(author).hexdigest(),'vertices':len(d['vertices']),'triangles':len(d['triangles']),
    'saved_assets':saved,'activation':'fps.Outfit.BareArmsCandidate 1','default_enabled':False,
    'equipment_support':'Unequip modular shirt and gloves for this first candidate',
    'runtime_tested':False,'visual_acceptance':'Pending user review','animation_assets_modified':False}
(ROOT/'saved.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('M4_REALISTIC_CANDIDATE_SAVED',mesh.get_path_name())
