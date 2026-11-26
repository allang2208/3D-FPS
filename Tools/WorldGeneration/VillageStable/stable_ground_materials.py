"""Author stable-local ground finishes from the windmill's existing scan textures."""
import hashlib
from pathlib import Path
import unreal as ue

from stable_actors import ROOT

DEST = ROOT+'/GroundDetailR4'
SRC = Path(__file__).resolve().parents[3]/'SourceAssets/HillsVillageStable/SurfaceR4'
MAT = ue.MaterialEditingLibrary
LIB = ue.EditorAssetLibrary
TOOLS = ue.AssetToolsHelpers.get_asset_tools()


def load(path):
    obj=ue.load_asset(path)
    if not obj:
        raise RuntimeError('Missing ground dependency '+path)
    return obj


def save(obj):
    if not LIB.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())


def atlas(name,normal=False):
    src=SRC/(name+'.png')
    path=DEST+'/T_'+name
    stamp=hashlib.sha256(src.read_bytes()).hexdigest()
    tex=ue.load_asset(path) if LIB.does_asset_exist(path) else None
    if tex and LIB.get_metadata_tag(tex,'StableGroundSource')==stamp:
        return tex
    task=ue.AssetImportTask()
    task.filename=str(src)
    task.destination_path=DEST
    task.destination_name='T_'+name
    task.automated=True
    task.replace_existing=True
    TOOLS.import_asset_tasks([task])
    tex=load(path)
    tex.srgb=False
    tex.compression_settings=ue.TextureCompressionSettings.TC_NORMALMAP if normal else ue.TextureCompressionSettings.TC_MASKS
    if normal:
        tex.flip_green_channel=False
    tex.address_x=tex.address_y=ue.TextureAddress.TA_CLAMP
    LIB.set_metadata_tag(tex,'StableGroundSource',stamp)
    save(tex)
    return tex


def material(name,weights,impressions,interior,extent_cm=(3600.,4400.)):
    path=DEST+'/'+name
    mat=(load(path) if LIB.does_asset_exist(path) else
         TOOLS.create_asset(name,DEST,ue.Material,ue.MaterialFactoryNew()))
    MAT.delete_all_material_expressions(mat)
    if interior:
        MAT.set_base_material_usage(mat,ue.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    else:
        mat.set_editor_property('material_domain',ue.MaterialDomain.MD_DEFERRED_DECAL)
        mat.set_editor_property('blend_mode',ue.BlendMode.BLEND_TRANSLUCENT)

    def expr(cls):
        return MAT.create_material_expression(mat,cls)

    def wire(output,to,pin):
        node,channel=output
        if not MAT.connect_material_expressions(node,channel,to,pin):
            raise RuntimeError('Cannot connect '+pin+' on '+to.get_name())

    def finish(output,prop):
        if not MAT.connect_material_property(*output,prop):
            raise RuntimeError('Cannot connect ground property '+str(prop))

    def constant(v):
        n=expr(ue.MaterialExpressionConstant)
        n.set_editor_property('r',v)
        return n,''

    def pair(a,b):
        n=expr(ue.MaterialExpressionConstant2Vector)
        n.set_editor_property('r',a);n.set_editor_property('g',b)
        return n,''

    def op(cls,a,b):
        n=expr(cls)
        wire(a,n,'A');wire(b,n,'B')
        return n,''

    def lerp(a,b,alpha):
        n=expr(ue.MaterialExpressionLinearInterpolate)
        wire(a,n,'A');wire(b,n,'B');wire(alpha,n,'Alpha')
        return n,''

    def sample(texture,uv):
        n=expr(ue.MaterialExpressionTextureSample)
        # UE selects the sampler from this texture's compression and color space.
        n.set_editor_property('texture',texture)
        wire(uv,n,'UVs')
        return n

    uv=expr(ue.MaterialExpressionTextureCoordinate),''
    mul=ue.MaterialExpressionMultiply
    if interior:
        # PackedFloor's imported UV0 is (local X/180, 1-local Y/180).
        # Its one placed instance is centred on village (4400,3950) cm.
        uv=op(ue.MaterialExpressionAdd,op(mul,uv,pair(180/3600,-180/4400)),
              pair(1700/3600,(3950-300+180)/4400))
    span_x,span_y=extent_cm
    tiled=op(mul,uv,pair(span_x/145.,span_y/145.))
    stone_uv=op(mul,uv,pair(span_x/108.,span_y/108.))
    weights=sample(weights,uv)
    gravel=(weights,'G');wet=(weights,'B')
    earth='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
    rock='/Game/WorldGeneration/TemperateHills/Upland/Textures/T_RockySteppe_'
    def surfaces(es,rs,ch):
        return lerp((sample(load(earth+es),tiled),ch),
                    (sample(load(rock+rs),stone_uv),ch),gravel)
    base=surfaces('B','BaseColor','RGB')
    finish(op(mul,base,lerp(constant(1),constant(.66),wet)),ue.MaterialProperty.MP_BASE_COLOR)
    finish(lerp(surfaces('ORM','ARH','G'),constant(.47),wet),ue.MaterialProperty.MP_ROUGHNESS)
    surface_normal=surfaces('N','Normal','RGB')
    relief=(sample(impressions,uv),'RGB')
    combine=expr(ue.MaterialExpressionMaterialFunctionCall)
    combine.set_editor_property('material_function',load('/Engine/Functions/Engine_MaterialFunctions02/Utility/BlendAngleCorrectedNormals'))
    pins=MAT.get_material_expression_input_names(combine)
    wire(surface_normal,combine,pins[0]);wire(relief,combine,pins[1])
    normal=(combine,'')
    if interior:
        # The atlas runs south; this mesh's tangent V runs north.
        sign=expr(ue.MaterialExpressionConstant3Vector)
        sign.set_editor_property('constant',ue.LinearColor(1,-1,1,1))
        normal=op(mul,normal,(sign,''))
    finish(normal,ue.MaterialProperty.MP_NORMAL)
    if not interior:
        finish((weights,'R'),ue.MaterialProperty.MP_OPACITY)
    MAT.layout_material_expressions(mat)
    errors=MAT.recompile_material(mat)
    if errors:
        raise RuntimeError(mat.get_name()+': '+'\n'.join(errors))
    save(mat)


def author():
    LIB.make_directory(DEST)
    weights=atlas('StableGroundWeights')
    relief=atlas('StableImprintsDX',True)
    material('M_StableYardSoil',weights,relief,False)
    material('M_StableStallFloor',weights,relief,True)


def author_west_paddock():
    LIB.make_directory(DEST)
    weights=atlas('StableWestPaddockWeights')
    relief=atlas('StableWestPaddockImprintsDX',True)
    material('M_StableWestPaddockSoil',weights,relief,False,extent_cm=(2300.,1500.))
