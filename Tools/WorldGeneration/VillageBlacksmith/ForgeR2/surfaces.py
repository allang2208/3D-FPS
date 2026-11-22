from pathlib import Path
import unreal as u
from author_shop import require
from ForgeR2.refit import ROOT
from TradeSign.surfaces import save

FOLDER=ROOT+'/Materials'
TEX=FOLDER+'/T_SmithWeatheredOak_'
PAINT=FOLDER+'/M_SmithWeatheredSign'
EMBERS=FOLDER+'/M_SmithSideBlastCoals'
PACKAGES=[TEX+k for k in ('Color','NormalDX','ORM')]+[PAINT,EMBERS]
edit=u.MaterialEditingLibrary
assets=u.EditorAssetLibrary

def wire(src,out,dst,pin):
    if not edit.connect_material_expressions(src,out,dst,pin):raise RuntimeError('Cannot connect '+pin)
def prop(src,pin,key):
    if not edit.connect_material_property(src,pin,getattr(u.MaterialProperty,'MP_'+key)):raise RuntimeError('Cannot bind '+key)
def sample(mat,tex,kind):
    n=edit.create_material_expression(mat,u.MaterialExpressionTextureSample)
    n.texture=tex
    n.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+('VIRTUAL_' if tex.virtual_texture_streaming else '')+kind)
    return n
def custom(mat,code,inputs):
    n=edit.create_material_expression(mat,u.MaterialExpressionCustom)
    n.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    n.set_editor_property('code',code)
    pins=[]
    for label,_,_ in inputs:
        inp=u.CustomInput();inp.set_editor_property('input_name',label);pins.append(inp)
    n.set_editor_property('inputs',pins)
    for label,src,out in inputs:wire(src,out,n,label)
    return n
def finish(mat):
    edit.layout_material_expressions(mat);edit.recompile_material(mat);save(mat)

def palette(source):
    textures={}
    for key,compression in [('Color','TC_DEFAULT'),('NormalDX','TC_NORMALMAP'),('ORM','TC_MASKS')]:
        path=TEX+key
        task=u.AssetImportTask();task.filename=str(source/('T_SmithWeatheredOak_'+key+'.png'))
        task.destination_path=FOLDER;task.destination_name=path.rsplit('/',1)[1]
        task.automated=True;task.replace_existing=True
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        tex=require(path);tex.modify()
        tex.compression_settings=getattr(u.TextureCompressionSettings,compression)
        tex.srgb=key=='Color';tex.address_x=tex.address_y=u.TextureAddress.TA_CLAMP
        if key=='NormalDX':tex.set_editor_property('flip_green_channel',False)
        save(tex);textures[key]=tex
    mat=(require(PAINT) if assets.does_asset_exist(PAINT) else
         u.AssetToolsHelpers.get_asset_tools().create_asset(PAINT.rsplit('/',1)[1],FOLDER,u.Material,u.MaterialFactoryNew()))
    mat.modify();edit.delete_all_material_expressions(mat)
    base=sample(mat,textures['Color'],'COLOR');norm=sample(mat,textures['NormalDX'],'NORMAL')
    pack=sample(mat,textures['ORM'],'MASKS')
    # Recover the same emblem read on the two independent wood atlases. Add scanned oak micropores.
    fine=sample(mat,require('/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_NormalDX'),'NORMAL')
    uv=edit.create_material_expression(mat,u.MaterialExpressionTextureCoordinate);uv.set_editor_property('u_tiling',3.7);uv.set_editor_property('v_tiling',1.25)
    wire(uv,'',fine,'UVs')
    normal=custom(mat,'return normalize(float3(Main.xy+0.22*Fine.xy,max(0.18,Main.z)));',[('Main',norm,'RGB'),('Fine',fine,'RGB')])
    prop(base,'RGB','BASE_COLOR');prop(normal,'','NORMAL');prop(pack,'R','AMBIENT_OCCLUSION');prop(pack,'G','ROUGHNESS')
    finish(mat)
    coal=('/Game/WorldGeneration/VillageTavern/KitchenHearth/M_TavernHearthCoal')
    hot=require(EMBERS) if assets.does_asset_exist(EMBERS) else assets.duplicate_asset(coal,EMBERS)
    hot.modify()
    for node in list(edit.get_material_expressions(hot)):
        if str(node.get_editor_property('desc'))=='SideBlastHeat':edit.delete_material_expression(hot,node)
    vc=edit.create_material_expression(hot,u.MaterialExpressionVertexColor)
    inv=edit.create_material_expression(hot,u.MaterialExpressionEyeAdaptationInverse)
    scan=next(n for n in edit.get_material_expressions(hot) if isinstance(n,u.MaterialExpressionTextureSample) and n.texture and 'ORM' in n.texture.get_name())
    glow=custom(hot,'float v=0.72+0.28*(1-Occlusion); return (float3(2.7,.22,.017)*Heat.r + float3(5.0,1.05,.065)*Heat.g*Heat.g)*v*InvExposure;',
                [('Heat',vc,''),('Occlusion',scan,'R'),('InvExposure',inv,'')])
    for n in (glow,vc,inv):n.set_editor_property('desc','SideBlastHeat')
    prop(glow,'','EMISSIVE_COLOR');finish(hot)
    work='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/Materials/M_Smith'
    return dict(Paint=mat,HotCoal=hot,Stone=require(work+'HearthStone'),Brick=require(work+'FiredBrick'),
                Iron=require(work+'ScaleIron'),Rubbed=require('/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterIron'),
                Fireclay=require('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_ClayLuting'),
                Soot=require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ChimneyR8/Materials/M_ChimneyFlueSoot'),
                Ash=require('/Game/WorldGeneration/VillageTavern/KitchenHearth/M_TavernHearthAsh'),
                Oak=require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
                Endgrain=require('/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_CarpenterCut'))
