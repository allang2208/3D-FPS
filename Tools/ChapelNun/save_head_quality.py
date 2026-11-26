"""Import the repaired head and grooms into an isolated production revision."""
from pathlib import Path
base=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/save_assets.py').read_text(encoding='utf-8-sig')
exec(compile(base.split('E.make_directory(DEST)')[0],'<nun authoring helpers>','exec'))
R=P/'SourceAssets/ChapelNun20261115/HeadQualityR2';O=R/'Authored'
DEST='/Game/Characters/ChapelNun20261115/HeadQualityR2'
receipt_path=R/'saved_assets.json';receipt=read(receipt_path) if receipt_path.exists() else {'assets':{},'completed':False,'runtime_tested':False}
E.make_directory(DEST)

textures={channel:texture(channel) for channel in ('base_color','normal','roughness')}
for channel,tex in textures.items():
    group=u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP if channel=='normal' else u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR if channel=='roughness' else u.TextureGroup.TEXTUREGROUP_CHARACTER
    tex.set_editor_property('lod_group',group);save(tex)

def face_material(name,kind):
    mat=new(name,'Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    mat.set_editor_property('use_material_attributes',False)
    mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE)
    base=node(mat,u.MaterialExpressionTextureSample,texture=textures['base_color'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    normal=node(mat,u.MaterialExpressionTextureSample,texture=textures['normal'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    rough=node(mat,u.MaterialExpressionTextureSample,texture=textures['roughness'],sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    prop(base,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    # Keep the original normal detail and add restrained sub-millimetre skin variation.
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    strength=.20 if kind=='eye' else .6 if kind=='lip' else .72
    code='float2 p=UV*1900.;float a=sin(p.x*1.17+sin(p.y*.73))*sin(p.y*1.31);float b=sin(p.y*1.07+sin(p.x*.89))*sin(p.x*1.53);return normalize(float3(N.xy*%s+float2(a,b)*%s,max(.1,N.z)));'%(strength,0 if kind=='eye' else .012 if kind=='lip' else .026)
    detail=node(mat,u.MaterialExpressionCustom,code=code,output_type=u.CustomMaterialOutputType.CMOT_FLOAT3)
    detail.set_editor_property('inputs',[pin('UV'),pin('N')]);wire(uv,detail,'UV');wire(normal,detail,'N','RGB')
    prop(color(mat,(0.,0.,1.)) if kind=='eye' else detail,'',u.MaterialProperty.MP_NORMAL)
    if kind=='skin':
        remap=node(mat,u.MaterialExpressionMultiply,const_b=.20);wire(rough,remap,'A','R')
        bias=node(mat,u.MaterialExpressionAdd,const_b=.43);wire(remap,bias,'A');prop(bias,'',u.MaterialProperty.MP_ROUGHNESS)
    else:prop(constant(mat,.22 if kind=='eye' else .44),'',u.MaterialProperty.MP_ROUGHNESS)
    prop(constant(mat,0),'',u.MaterialProperty.MP_METALLIC)
    prop(constant(mat,.5 if kind=='eye' else .34),'',u.MaterialProperty.MP_SPECULAR)
    if kind=='eye':
        scatter=node(mat,u.MaterialExpressionMultiply,const_b=.3);wire(base,scatter,'A','RGB')
        prop(scatter,'',u.MaterialProperty.MP_SUBSURFACE_COLOR);prop(constant(mat,.85),'',u.MaterialProperty.MP_OPACITY)
    else:
        prop(color(mat,(.38,.16,.10)),'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
        prop(constant(mat,.65),'',u.MaterialProperty.MP_OPACITY)
    L.recompile_material(mat);save(mat);return mat

def scalp_material():
    mat=new('M_Nun_ScalpFoundation','Materials',u.Material,u.MaterialFactoryNew());L.delete_all_material_expressions(mat)
    L.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
    mat.set_editor_property('opacity_mask_clip_value',.35)
    uv=node(mat,u.MaterialExpressionTextureCoordinate)
    noise=node(mat,u.MaterialExpressionCustom,code='float n=frac(sin(dot(floor(UV*float2(1800,900)),float2(127.1,311.7)))*43758.5453);return smoothstep(.003,.035,UV.y+(n-.5)*.016);',output_type=u.CustomMaterialOutputType.CMOT_FLOAT1)
    noise.set_editor_property('inputs',[pin('UV')]);wire(uv,noise,'UV');prop(noise,'',u.MaterialProperty.MP_OPACITY_MASK)
    prop(color(mat,(.009,.008,.007)),'',u.MaterialProperty.MP_BASE_COLOR)
    prop(constant(mat,.67),'',u.MaterialProperty.MP_ROUGHNESS);prop(constant(mat,.24),'',u.MaterialProperty.MP_SPECULAR)
    L.recompile_material(mat);return save(mat)

mats=[face_material('M_NunSkin_R2','skin'),load('/Game/Characters/KaitlinPlayer20261023/Native/Kaitlin/Face/Materials/MI_Face_Skin_Baked_LOD1'),face_material('M_Nun_EyeSurface','eye'),face_material('M_Nun_Lips','lip'),scalp_material()]
head=skeletal('head.json','SK_Nun_Head_R2_Final',mats)
factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
policy=u.load_asset(DEST+'/Meshes/DA_NunFaceLOD') or A.create_asset('DA_NunFaceLOD',DEST+'/Meshes',u.SkeletalMeshLODSettings,factory)
groups=[]
for ratio,screen in ((1.,1.),(.70,.18),(.42,.065)):
    group=u.SkeletalMeshLODGroupSettings();reduction=group.get_editor_property('reduction_settings')
    for key,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,welding_threshold=0.,recalc_normals=False).items():reduction.set_editor_property(key,value)
    group.set_editor_property('reduction_settings',reduction);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
policy.set_editor_property('lod_groups',groups);head.set_editor_property('lod_settings',policy)
models=list(head.get_editor_property('source_models'))
for i,model in enumerate(models):model.set_editor_property('reduction_settings',groups[min(i,2)].get_editor_property('reduction_settings'))
head.set_editor_property('source_models',models);save(policy)
u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem).regenerate_lod(head,3,True,False)
head.set_editor_property('positive_bounds_extension',u.Vector(3,12,3));head.set_editor_property('negative_bounds_extension',u.Vector(3,3,7));save(head)
hair_mat=load('/Game/Characters/ChapelNun20261115/Materials/MI_Nun_Hair')
for name,sim in [('Nun_LowBun_Core_R2',False),('Nun_LowBun_Loose_R2',True)]:
    asset,binding=groom(name,head,sim,hair_mat)
    group=asset.get_editor_property('hair_groups_rendering')[0]
    geo=group.get_editor_property('geometry_settings');geo.set_editor_property('hair_width',.011 if not sim else .0085);geo.set_editor_property('hair_tip_scale',.30);group.set_editor_property('geometry_settings',geo)
    shadow=group.get_editor_property('shadow_settings');shadow.set_editor_property('hair_shadow_density',.85);group.set_editor_property('shadow_settings',shadow)
    asset.set_editor_property('hair_groups_rendering',[group])
    lod=asset.get_editor_property('hair_groups_lod')[0]
    lod.import_text('(LODs=((ScreenSize=1.0,GeometryType=Strands),(CurveDecimation=0.65,VertexDecimation=0.75,ScreenSize=0.15,ThicknessScale=1.15,GeometryType=Strands),(CurveDecimation=0.30,VertexDecimation=0.55,ScreenSize=0.045,ThicknessScale=1.45,GeometryType=Strands,Simulation=Disable)))')
    asset.set_editor_property('hair_groups_lod',[lod]);save(asset)
    final_binding_name=name+'_Final_Binding'
    final_binding=u.load_asset(DEST+'/Grooms/'+final_binding_name)
    if not final_binding:
        final_binding=u.GroomLibrary.create_new_groom_binding_asset_with_path(DEST+'/Grooms/'+final_binding_name,asset,head,100,None,0)
    save(final_binding);receipt['assets'][final_binding_name]=final_binding.get_path_name();record()
receipt['materials']=[x.get_path_name() for x in mats];receipt['completed']=True;record()
print('HEAD_QUALITY_ASSETS_SAVED',flush=True)
