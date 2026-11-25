"""Create the small mill implements and ground-wear decal in the private yard package."""
import hashlib
import unreal as ue
from import_windmill_assets import ASSETS, MAT, TOOLS, PROJECT, import_fbx, load, save, setup_geometry

YARD='/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard'
FINISH='/Game/WorldGeneration/TemperateHills/VillageWindmill/Materials/'
SOURCE=PROJECT/'SourceAssets/HillsVillageWindmill/Millyard/WorkDetails'


def material(name):
    return TOOLS.create_asset(name,YARD+'/Materials',ue.Material,ue.MaterialFactoryNew())


def sample(mat, texture, sampler):
    node=MAT.create_material_expression(mat,ue.MaterialExpressionTextureSample)
    node.texture=texture
    node.set_editor_property('sampler_type',sampler)
    return node


def finish(mat):
    MAT.layout_material_expressions(mat)
    MAT.recompile_material(mat)
    save(mat)


def linen(name,tint,two_sided=False):
    path=YARD+'/Materials/'+name
    if ASSETS.does_asset_exist(path):
        return load(path)
    mat=material(name)
    mat.set_editor_property('two_sided',two_sided)
    MAT.set_base_material_usage(mat,ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    textures='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Textures/T_VillageR2_Linen_'
    albedo=sample(mat,load(textures+'Color'),ue.MaterialSamplerType.SAMPLERTYPE_COLOR)
    normal=sample(mat,load(textures+'NormalDX'),ue.MaterialSamplerType.SAMPLERTYPE_NORMAL)
    masks=sample(mat,load(textures+'ORM'),ue.MaterialSamplerType.SAMPLERTYPE_MASKS)
    pigment=MAT.create_material_expression(mat,ue.MaterialExpressionConstant3Vector)
    pigment.set_editor_property('constant',ue.LinearColor(*tint,1))
    color=MAT.create_material_expression(mat,ue.MaterialExpressionMultiply)
    MAT.connect_material_expressions(albedo,'RGB',color,'A')
    MAT.connect_material_expressions(pigment,'',color,'B')
    MAT.connect_material_property(color,'',ue.MaterialProperty.MP_BASE_COLOR)
    MAT.connect_material_property(normal,'RGB',ue.MaterialProperty.MP_NORMAL)
    MAT.connect_material_property(masks,'G',ue.MaterialProperty.MP_ROUGHNESS)
    MAT.connect_material_property(masks,'R',ue.MaterialProperty.MP_AMBIENT_OCCLUSION)
    finish(mat)
    return mat


def traffic():
    name='M_MillTraffic'
    if ASSETS.does_asset_exist(YARD+'/Materials/'+name):
        return
    task=ue.AssetImportTask()
    task.filename=str(SOURCE/'MillApronTraffic.png')
    task.destination_path=YARD+'/Textures'
    task.destination_name='T_MillApronTraffic'
    task.automated=True
    TOOLS.import_asset_tasks([task])
    mask=load(task.destination_path+'/'+task.destination_name)
    mask.srgb=False
    mask.compression_settings=ue.TextureCompressionSettings.TC_MASKS
    save(mask)
    mat=material(name)
    mat.set_editor_property('material_domain',ue.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('blend_mode',ue.BlendMode.BLEND_TRANSLUCENT)
    alpha=sample(mat,mask,ue.MaterialSamplerType.SAMPLERTYPE_MASKS)
    MAT.connect_material_property(alpha,'R',ue.MaterialProperty.MP_OPACITY)
    uv=MAT.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate)
    uv.set_editor_property('u_tiling',8.05)
    uv.set_editor_property('v_tiling',5.60)
    soil='/Game/UnrealNormandy/Textures/T_LC_GroundSoilExcavated_00A_'
    for suffix,mode,pin,prop in [('Albedo',ue.MaterialSamplerType.SAMPLERTYPE_COLOR,'RGB',ue.MaterialProperty.MP_BASE_COLOR),
        ('Normal',ue.MaterialSamplerType.SAMPLERTYPE_NORMAL,'RGB',ue.MaterialProperty.MP_NORMAL)]:
        tex=sample(mat,load(soil+suffix),mode)
        MAT.connect_material_expressions(uv,'',tex,'UVs')
        MAT.connect_material_property(tex,pin,prop)
    rough=MAT.create_material_expression(mat,ue.MaterialExpressionConstant)
    rough.set_editor_property('r',.91)
    MAT.connect_material_property(rough,'',ue.MaterialProperty.MP_ROUGHNESS)
    finish(mat)


def yard_margins():
    name='M_MillVergeSurface'
    texture_path=YARD+'/Textures/T_MillVergeMask'
    mask=load(texture_path) if ASSETS.does_asset_exist(texture_path) else None
    mask_file=SOURCE/'MillVergeMask.png'
    stamp=hashlib.sha256(mask_file.read_bytes()).hexdigest()
    if not mask or ASSETS.get_metadata_tag(mask,'MillVergeSourceSHA256')!=stamp:
        task=ue.AssetImportTask()
        task.filename=str(mask_file)
        task.destination_path=YARD+'/Textures'
        task.destination_name='T_MillVergeMask'
        task.automated=True
        task.replace_existing=True
        TOOLS.import_asset_tasks([task])
        mask=load(texture_path)
        mask.srgb=False
        mask.compression_settings=ue.TextureCompressionSettings.TC_MASKS
        ASSETS.set_metadata_tag(mask,'MillVergeSourceSHA256',stamp)
        save(mask)
    if not ASSETS.does_asset_exist(YARD+'/Materials/'+name):
        mat=material(name)
        mat.set_editor_property('blend_mode',ue.BlendMode.BLEND_MASKED)
        mat.set_editor_property('two_sided',True)
        weights=sample(mat,mask,ue.MaterialSamplerType.SAMPLERTYPE_MASKS)
        feather=MAT.create_material_expression(mat,ue.MaterialExpressionMaterialFunctionCall)
        feather.set_editor_property('material_function',load('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
        alpha_pin=MAT.get_material_expression_input_names(feather)[0]
        if not MAT.connect_material_expressions(weights,'R',feather,alpha_pin):
            raise RuntimeError('Missing verge edge opacity input')
        MAT.connect_material_property(feather,'',ue.MaterialProperty.MP_OPACITY_MASK)
        uv=MAT.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate)
        uv.set_editor_property('u_tiling',2240/145)
        uv.set_editor_property('v_tiling',2460/145)
        upland='/Game/WorldGeneration/TemperateHills/Upland/Textures/T_'
        for suffix,mode,pin,prop in [
                ('BaseColor',ue.MaterialSamplerType.SAMPLERTYPE_COLOR,'RGB',ue.MaterialProperty.MP_BASE_COLOR),
                ('Normal',ue.MaterialSamplerType.SAMPLERTYPE_NORMAL,'RGB',ue.MaterialProperty.MP_NORMAL),
                ('ARH',ue.MaterialSamplerType.SAMPLERTYPE_MASKS,'G',ue.MaterialProperty.MP_ROUGHNESS)]:
            blend=MAT.create_material_expression(mat,ue.MaterialExpressionLinearInterpolate)
            for surface,input_pin in [('LitteredGrass','A'),('RockySteppe','B')]:
                node=sample(mat,load(upland+surface+'_'+suffix),mode)
                MAT.connect_material_expressions(uv,'',node,'UVs')
                MAT.connect_material_expressions(node,pin,blend,input_pin)
            MAT.connect_material_expressions(weights,'G',blend,'Alpha')
            MAT.connect_material_property(blend,'',prop)
        finish(mat)
    else:
        mat=load(YARD+'/Materials/'+name)
        if not mat.get_editor_property('two_sided'):
            mat.set_editor_property('two_sided',True)
            finish(mat)
    mesh_path=YARD+'/Meshes/SM_MillVergeSurface'
    surface_file=SOURCE/'SM_MillVergeSurface.fbx'
    surface_stamp=hashlib.sha256(surface_file.read_bytes()).hexdigest()
    skin=load(mesh_path) if ASSETS.does_asset_exist(mesh_path) else None
    if not skin or ASSETS.get_metadata_tag(skin,'MillSurfaceSourceSHA256')!=surface_stamp:
        skin=import_fbx(surface_file,YARD+'/Meshes')
        skin.set_material(0,load(YARD+'/Materials/'+name))
        ASSETS.set_metadata_tag(skin,'MillSurfaceSourceSHA256',surface_stamp)
        save(skin)
    # The large rocks use their actual surfaces for collision. Keep the underlying
    # Normandy and quarry meshes usable as non-blocking scatter everywhere else.
    donors=('/Game/UnrealNormandy/StaticMeshes/SM_Stone_00A','/Game/UnrealNormandy/StaticMeshes/SM_Stone_02A',
            '/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/Fractures/SM_QuarryFallenWedge')
    for variant,donor in zip('ABC',donors):
        path=YARD+'/Meshes/SM_MillFieldstone'+variant
        if not ASSETS.does_asset_exist(path):
            rock=ASSETS.duplicate_asset(donor,path)
            setup_geometry(rock,True,rock.get_num_triangles(0))
            save(rock)
    # Retain the full scanned field tree and its native LODs at this near view.
    alder_path=YARD+'/Meshes/SM_MillGroveFieldAlder'
    if not ASSETS.does_asset_exist(alder_path):
        name='SM_BlackAlder_Field_01_PP'
        donor=ue.load_object(None,'/CitySamplePCG/BlackAlder/Geometry/PivotPainter/'+name+'.'+name)
        if not donor:
            raise RuntimeError('Missing Quixel field alder')
        field=TOOLS.duplicate_asset('SM_MillGroveFieldAlder',YARD+'/Meshes',donor)
        save(field)


def author():
    traffic()
    if not ASSETS.does_asset_exist(YARD+'/Meshes/SM_MillApronWear'):
        wear=import_fbx(SOURCE/'SM_MillApronWear.fbx',YARD+'/Meshes')
        wear.set_material(0,load(YARD+'/Materials/M_MillTraffic'))
        save(wear)
    yard_margins()
    grain_path=YARD+'/Materials/M_MillWheat'
    if not ASSETS.does_asset_exist(grain_path):
        mat=material('M_MillWheat')
        MAT.set_base_material_usage(mat,ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
        color=MAT.create_material_expression(mat,ue.MaterialExpressionLinearInterpolate)
        for pin,rgb in [('A',(.24,.117,.028)),('B',(.72,.47,.17))]:
            vec=MAT.create_material_expression(mat,ue.MaterialExpressionConstant3Vector)
            vec.set_editor_property('constant',ue.LinearColor(*rgb,1))
            MAT.connect_material_expressions(vec,'',color,pin)
        vertex=MAT.create_material_expression(mat,ue.MaterialExpressionVertexColor)
        MAT.connect_material_expressions(vertex,'R',color,'Alpha')
        MAT.connect_material_property(color,'',ue.MaterialProperty.MP_BASE_COLOR)
        rough=MAT.create_material_expression(mat,ue.MaterialExpressionConstant)
        rough.set_editor_property('r',.80)
        MAT.connect_material_property(rough,'',ue.MaterialProperty.MP_ROUGHNESS)
        finish(mat)
    finishes={'Grain':load(grain_path),'Oak':load(FINISH+'M_VillageR2_Oak_Windmill'),
              'End':load(FINISH+'M_VillageR2_Endgrain_Windmill'),'Iron':load(FINISH+'M_CarpenterIron_Windmill'),
              'Flax':linen('M_MillFlax',(.74,.55,.33)),
              'Canvas':linen('M_MillCanvas',(.94,.76,.51),True),
              'Rope':load(FINISH+'MI_Prop_Rope_All_Windmill')}
    for role in ('Measure','Grain','StoneTools','TiedSack','SortingShade','OakSkid','SmokeHood'):
        name='SM_Mill'+role
        if ASSETS.does_asset_exist(YARD+'/Meshes/'+name):
            continue
        m=import_fbx(SOURCE/(name+'.fbx'),YARD+'/Meshes')
        for i,slot in enumerate(m.static_materials):
            m.set_material(i,finishes[str(slot.get_editor_property('imported_material_slot_name'))])
        if role=='SortingShade':
            setup_geometry(m,True,m.get_num_triangles(0))
        save(m)
