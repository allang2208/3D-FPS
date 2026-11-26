"""Save the original Meshy face and bind the existing black grooms to it."""
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_assets.py').read_text(encoding='utf-8-sig')
exec(compile(base.split('E.make_directory(DEST)')[0],'<nun authoring helpers>','exec'))
R=P/'SourceAssets/ChapelNun20261115/OriginalMeshyFaceR3';O=R/'Authored'
DEST='/Game/Characters/ChapelNun20261115/OriginalMeshyFaceR3'
receipt_path=R/'saved_assets.json'
receipt=read(receipt_path) if receipt_path.exists() else {'assets':{},'completed':False,'runtime_tested':False}
source=read(R/'original_material.json');source_mat=source['material']
E.make_directory(DEST)

textures={}
for channel,filename in source['images'].items():
    name='T_NunOriginal_'+channel;path=DEST+'/Textures/'+name
    tex=u.load_asset(path)
    if not tex:
        task=u.AssetImportTask();task.filename=filename;task.destination_path=DEST+'/Textures'
        task.destination_name=name;task.automated=True;task.save=False
        A.import_asset_tasks([task]);tex=load(path)
    is_normal=channel=='normal';is_color=channel=='base_color'
    tex.set_editor_property('srgb',is_color)
    tex.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if is_normal else u.TextureCompressionSettings.TC_DEFAULT if is_color else u.TextureCompressionSettings.TC_MASKS)
    tex.set_editor_property('lod_group',u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if is_normal else u.TextureGroup.TEXTUREGROUP_CHARACTER if is_color else u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
    if is_normal:tex.set_editor_property('flip_green_channel',True)
    textures[channel]=save(tex);receipt['assets'][name]=tex.get_path_name()
record()

mat=new('M_Nun_OriginalMeshy','Materials',u.Material,u.MaterialFactoryNew())
L.delete_all_material_expressions(mat);L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
mat.set_editor_property('use_material_attributes',False)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_DEFAULT_LIT)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
mat.set_editor_property('two_sided',source_mat.get('doubleSided',False))
base_sample=node(mat,u.MaterialExpressionTextureSample,texture=textures['base_color'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
mr_sample=node(mat,u.MaterialExpressionTextureSample,texture=textures['metallic_roughness'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
normal_sample=node(mat,u.MaterialExpressionTextureSample,texture=textures['normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
pbr=source_mat['pbrMetallicRoughness']
base_factor=node(mat,u.MaterialExpressionMultiply)
wire(base_sample,base_factor,'A','RGB');wire(color(mat,pbr.get('baseColorFactor',[1,1,1,1])[:3]),base_factor,'B')
prop(base_factor,'',u.MaterialProperty.MP_BASE_COLOR)
for channel,factor,material_property in [('G',pbr.get('roughnessFactor',1),u.MaterialProperty.MP_ROUGHNESS),('B',pbr.get('metallicFactor',1),u.MaterialProperty.MP_METALLIC)]:
    product=node(mat,u.MaterialExpressionMultiply,const_b=factor);wire(mr_sample,product,'A',channel);prop(product,'',material_property)
prop(normal_sample,'RGB',u.MaterialProperty.MP_NORMAL)
prop(constant(mat,.5),'',u.MaterialProperty.MP_SPECULAR)
L.recompile_material(mat);save(mat);receipt['assets']['M_Nun_OriginalMeshy']=mat.get_path_name();record()

mats=[mat,load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face/Materials/MI_Face_Skin_Baked_LOD1'),load('/Game/Characters/ChapelNun20261115/HeadQualityR2/Materials/M_Nun_ScalpFoundation')]
head=skeletal('head.json','SK_Nun_OriginalMeshyFace',mats)
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
policy=u.load_asset(DEST+'/Meshes/DA_NunOriginalFaceLOD') or A.create_asset('DA_NunOriginalFaceLOD',DEST+'/Meshes',u.SkeletalMeshLODSettings,factory)
groups=[]
for ratio,screen in ((1.,1.),(.70,.18),(.42,.065)):
    group=u.SkeletalMeshLODGroupSettings();reduction=group.get_editor_property('reduction_settings')
    for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():
        reduction.set_editor_property(key,value)
    group.set_editor_property('reduction_settings',reduction);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
policy.set_editor_property('lod_groups',groups);head.set_editor_property('lod_settings',policy)
models=list(head.get_editor_property('source_models'))
for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
head.set_editor_property('source_models',models);save(policy)
u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(head,3,True,False)
head.set_editor_property('positive_bounds_extension',u.Vector(3,12,3));head.set_editor_property('negative_bounds_extension',u.Vector(3,3,7));save(head)
receipt['assets']['DA_NunOriginalFaceLOD']=policy.get_path_name();record()

for part in ('Core','Loose'):
    groom_asset=load('/Game/Characters/ChapelNun20261115/HeadQualityR2/Grooms/Nun_LowBun_'+part+'_R2')
    name='Nun_LowBun_'+part+'_OriginalFace_Binding'
    binding=u.load_asset(DEST+'/Grooms/'+name)
    if not binding:binding=u.GroomLibrary.create_new_groom_binding_asset_with_path(DEST+'/Grooms/'+name,groom_asset,head,100,None,0)
    save(binding);receipt['assets'][name]=binding.get_path_name();receipt['assets']['retained_'+part+'_groom']=groom_asset.get_path_name();record()

receipt['materials']=[x.get_path_name() for x in mats]
receipt['source']=source['source'];receipt['source_material']=source_mat
receipt['normal_convention']='Original OpenGL normal texture with UE green-channel conversion only'
receipt['facial_processing']='No facial smoothing, reshaping, added pores, eye/lip split, or PBR remapping'
receipt['completed']=True;record();print('ORIGINAL_MESHY_FACE_ASSETS_SAVED',flush=True)
