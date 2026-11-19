"""Author the commissioned head and card groom against the exact R4 per-mesh reference pose."""
import gc
import gzip
import json
import os
import hashlib
from pathlib import Path
import unreal as u
PROJECT=Path(__file__).resolve().parents[3]
OUT=PROJECT/'SourceAssets/VillageBlacksmithNPC20261118/HeadHair'
DEST='/Game/Characters/VillageBlacksmithNPC20261118'
PARTS=DEST+'/HeadParts'
A=u.AssetToolsHelpers.get_asset_tools();E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary
G=u.GeometryScript_AssetUtils;B=u.GeometryScript_BoneWeights
owned=[]
def save(obj):
    if not obj or not obj.get_path_name().startswith(DEST+'/'):raise RuntimeError('Unowned destination')
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    path=obj.get_path_name().split('.')[0]
    if path not in owned:owned.append(path)
    return obj

def texture(path,kind):
    name=path.stem
    dst=PARTS+'/Textures/'+name
    asset=u.load_asset(dst)
    if not asset:
        task=u.AssetImportTask();task.filename=str(path);task.destination_path=PARTS+'/Textures';task.destination_name=name
        task.automated=True;task.save=False;A.import_asset_tasks([task])
        asset=u.load_asset(dst)
        if not asset:raise ValueError('Cannot import '+str(path))
    asset.set_editor_property('srgb',kind=='color')
    cfg={'color':(u.TextureCompressionSettings.TC_DEFAULT,u.TextureGroup.TEXTUREGROUP_CHARACTER),
         'normal':(u.TextureCompressionSettings.TC_NORMALMAP,u.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP),
         'rough':(u.TextureCompressionSettings.TC_MASKS,u.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)}
    compression,group=cfg[kind];asset.set_editor_property('compression_settings',compression);asset.set_editor_property('lod_group',group)
    if kind=='normal':asset.set_editor_property('flip_green_channel',True)
    return save(asset)

def material(name,albedo,normal=None,rough=None,hair=False,neck_tint=None):
    path=PARTS+'/'+name
    m=u.load_asset(path) or A.create_asset(name,PARTS,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    L.set_material_usage(m,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    if hair:
        m.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
        m.set_editor_property('two_sided',True);m.set_editor_property('opacity_mask_clip_value',.23)
    else:m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SUBSURFACE)
    def node(cls,**props):
        n=L.create_material_expression(m,cls)
        for key,val in props.items():n.set_editor_property(key,val)
        return n
    def out(n,channel,pin):
        if not L.connect_material_property(n,channel,pin):raise RuntimeError('Material connection failed')
    def const(v,pin):out(node(u.MaterialExpressionConstant,r=v),'',pin)
    bc=node(u.MaterialExpressionTextureSample,texture=albedo,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    if neck_tint is None:out(bc,'RGB',u.MaterialProperty.MP_BASE_COLOR)
    else:
        tint=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*neck_tint,1))
        corrected=node(u.MaterialExpressionMultiply)
        L.connect_material_expressions(bc,'RGB',corrected,'A')
        L.connect_material_expressions(tint,'',corrected,'B')
        pre=node(u.MaterialExpressionPreSkinnedPosition)
        rest=node(u.MaterialExpressionVertexInterpolator)
        if not L.connect_material_expressions(pre,'',rest,''):raise RuntimeError('Cannot interpolate the neck rest position.')
        z=node(u.MaterialExpressionComponentMask,r=False,g=False,b=True,a=False)
        if not L.connect_material_expressions(rest,'',z,''):raise RuntimeError('Cannot read the neck rest height.')
        ramp=node(u.MaterialExpressionSmoothStep,const_min=150.4,const_max=155.30)
        L.connect_material_expressions(z,'',ramp,'Value')
        blend=node(u.MaterialExpressionLinearInterpolate)
        L.connect_material_expressions(bc,'RGB',blend,'A')
        L.connect_material_expressions(corrected,'',blend,'B')
        L.connect_material_expressions(ramp,'',blend,'Alpha')
        out(blend,'',u.MaterialProperty.MP_BASE_COLOR)
    if normal:out(node(u.MaterialExpressionTextureSample,texture=normal,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL),'RGB',u.MaterialProperty.MP_NORMAL)
    if rough:out(node(u.MaterialExpressionTextureSample,texture=rough,sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS),'R',u.MaterialProperty.MP_ROUGHNESS)
    else:const(.64 if hair else .53,u.MaterialProperty.MP_ROUGHNESS)
    if hair:out(bc,'A',u.MaterialProperty.MP_OPACITY_MASK)
    else:
        diffuse=L.get_material_property_input_node(m,u.MaterialProperty.MP_BASE_COLOR)
        scatter=node(u.MaterialExpressionMultiply)
        strength=node(u.MaterialExpressionConstant3Vector,constant=u.LinearColor(.15,.085,.055,1))
        L.connect_material_expressions(diffuse,'RGB' if neck_tint is None else '',scatter,'A')
        L.connect_material_expressions(strength,'',scatter,'B')
        out(scatter,'',u.MaterialProperty.MP_SUBSURFACE_COLOR)
        const(.70,u.MaterialProperty.MP_OPACITY)
    const(.29 if hair else .32,u.MaterialProperty.MP_SPECULAR)
    L.recompile_material(m);return save(m)

def write_skeletal(filename,name,materials,ref,source):
    path=DEST+'/'+name
    part_receipt=OUT/(name+'_saved.json')
    with gzip.open(OUT/filename,'rb') as raw:geometry_hash=hashlib.sha256(raw.read()).hexdigest()
    if part_receipt.exists():
        prior=json.loads(part_receipt.read_text())
        existing=u.load_asset(path)
        if existing and prior['geometry_hash']==geometry_hash:
            owned.extend(prior['packages'])
            return existing
    start=len(owned)
    with gzip.open(OUT/filename,'rt',encoding='utf8') as stream:d=json.load(stream)
    dm=u.DynamicMesh()
    buffers=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*x) for x in d['p']],normals=[u.Vector(*x) for x in d['n']],
                 uv0=[u.Vector2D(*x) for x in d['uv']],triangles=[u.IntVector(*x) for x in d['tri']])
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buffers,0,True)
    B.copy_bones_from_mesh(ref,dm);B.mesh_create_bone_weights(dm)
    if 'w' in d:
        single_cache={}
        for index,weights in enumerate(d['w']):
            if len(weights)==1:
                bone=weights[0][0]
                if bone not in single_cache:single_cache[bone]=[u.GeometryScriptBoneWeight(bone_index=bone,weight=1.)]
                w=single_cache[bone]
            else:w=[u.GeometryScriptBoneWeight(bone_index=i,weight=v) for i,v in weights]
            B.set_vertex_bone_weights(dm,index,w)
    else:
        w=[u.GeometryScriptBoneWeight(bone_index=d['rigid'],weight=1.)]
        for index in range(len(d['p'])):B.set_vertex_bone_weights(dm,index,w)
    if 'm' in d:
        funcs=u.GeometryScript_Materials
        set_all=next(getattr(funcs,n) for n in dir(funcs) if n.lower().replace('_','')=='setalltrianglematerialids')
        set_all(dm,u.GeometryScript_List.convert_array_to_index_list(d['m'],u.GeometryScriptIndexType.MATERIAL_ID),True)
    opts=u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    opts.use_mesh_bone_proportions=True;opts.enable_recompute_normals=False;opts.enable_recompute_tangents=True;opts.materials=materials
    obj=u.load_asset(path)
    if obj:raise RuntimeError('A saved head package already exists in this authoring host: '+path)
    obj,result=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,source.skeleton,path,opts)
    if result!=u.GeometryScriptOutcomePins.SUCCESS or not obj:raise RuntimeError('Cannot create '+name)
    factory=u.DataAssetFactory();factory.set_editor_property('data_asset_class',u.SkeletalMeshLODSettings)
    policy_name='DA_Smith_'+('Hair' if filename.startswith('hair') else 'Face')+'LOD'
    policy=u.load_asset(PARTS+'/'+policy_name) or A.create_asset(policy_name,PARTS,u.SkeletalMeshLODSettings,factory)
    groups=[]
    for ratio,screen in ((1.,1.),(.54,.23),(.23,.08)):
        group=u.SkeletalMeshLODGroupSettings();red=group.get_editor_property('reduction_settings')
        for prop,value in dict(num_of_triangles_percentage=ratio,num_of_vert_percentage=ratio,max_bones_per_vertex=8,
                               lock_edges=True,enforce_bone_boundaries=True,merge_coincident_vert_bones=False,
                               welding_threshold=0.,recalc_normals=False).items():red.set_editor_property(prop,value)
        group.set_editor_property('reduction_settings',red);group.set_editor_property('screen_size',u.PerPlatformFloat(default=screen));groups.append(group)
    policy.set_editor_property('lod_groups',groups);save(policy);obj.set_editor_property('lod_settings',policy)
    ss=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);ss.regenerate_lod(obj,3,True,False)
    save(obj)
    part_receipt.write_text(json.dumps({'geometry_hash':geometry_hash,'packages':owned[start:]},indent=2))
    print('SMITH_SAVED_SKINNED',name,flush=True)
    return obj

local=OUT/'Textures'
materials_only=os.environ.get('SMITH_HAIR_MATERIALS_ONLY')=='1'
fit=json.loads((OUT/'fit.json').read_text()) if (OUT/'fit.json').exists() else {}
integrated=fit.get('integrated_meshy_hair',False)
if materials_only or not integrated:
    hair_mat=material('M_Smith_ShortHair',texture(local/'T_Smith_Fibres.png','color'),hair=True)
if materials_only:
    (OUT/'materials_saved.json').write_text(json.dumps({'assets':owned},indent=2))
else:
    face_bc=texture(local/'T_Smith_Face_BC.png','color')
    npath=local/'T_Smith_Face_N.png';rpath=local/'T_Smith_Face_R.png'
    face_mat=material('M_Smith_MeshyFace',face_bc,texture(npath,'normal') if npath.exists() else None,texture(rpath,'rough') if rpath.exists() else None)
    neck_tex=OUT.parent/'BodyOutfit/Textures/T_Smith_Skin_head_BC.png'
    neck_mat=material('M_Smith_NativeNeck',texture(neck_tex,'color'),u.load_asset('/Game/AsianMale_Jason/Texture/T_Head_LOD2_N'),neck_tint=fit['neck_tint_upper_linear'])
    r4=json.loads((PROJECT/'SourceAssets/JasonStrong20261117/R4_PoseRefined/variant_saved.json').read_text())
    source=u.load_asset(r4['asset'])
    ref,status=G.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('R4 skeleton unavailable')
    head=write_skeletal('face.json.gz','SK_Smith_Head',{'SmithMeshyFace':face_mat,'SmithNativeNeck':neck_mat},ref,source)
    gc.collect()
    if not integrated:
        write_skeletal('hair.json.gz','SK_Smith_Hair',{'SmithHair':hair_mat},ref,source)
    (OUT/'saved.json').write_text(json.dumps({'assets':owned,'skeleton':head.skeleton.get_path_name(),'integrated_meshy_hair':integrated,'source_glb':fit['source'],'runtime_tested':False},indent=2))
