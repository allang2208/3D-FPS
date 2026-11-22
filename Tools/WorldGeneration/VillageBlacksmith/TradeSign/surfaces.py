"""Layer the approved ochre, iron red and lime-white pigments over the scanned timber surface."""
import unreal as u
from author_shop import require
from TradeSign.layout import ROOT

FOLDER=ROOT+'/Materials'
MASK=FOLDER+'/T_SmithTradeSign_Pigment'
PAINT=FOLDER+'/M_SmithTradeSign_PaintedOak'
CARPENTER='/Game/WorldGeneration/TemperateHills/VillageCarpenter/Props/Surfaces/M_Carpenter'
TIMBER='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelTimber_'
edit=u.MaterialEditingLibrary
assets=u.EditorAssetLibrary

def save(obj):
    if not assets.save_loaded_asset(obj,False):raise RuntimeError('Could not save '+obj.get_path_name())

def palette(source):
    task=u.AssetImportTask()
    task.filename=str(source/'T_SmithTradeSign_Pigment.png')
    task.destination_path=FOLDER
    task.destination_name=MASK.rsplit('/',1)[1]
    task.automated=True
    task.replace_existing=True
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    pigment=require(MASK)
    pigment.modify()
    pigment.compression_settings=u.TextureCompressionSettings.TC_MASKS
    pigment.srgb=False
    pigment.address_x=pigment.address_y=u.TextureAddress.TA_CLAMP
    save(pigment)
    mat=(require(PAINT) if assets.does_asset_exist(PAINT) else
         u.AssetToolsHelpers.get_asset_tools().create_asset(PAINT.rsplit('/',1)[1],FOLDER,u.Material,u.MaterialFactoryNew()))
    mat.modify()
    edit.delete_all_material_expressions(mat)
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    mat.set_editor_property('used_with_nanite',True)
    def node(kind):return edit.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
    def wire(src,pin,dst,slot):
        if not edit.connect_material_expressions(src,pin,dst,slot):raise RuntimeError('Cannot bind '+slot)
    def prop(src,pin,slot):
        if not edit.connect_material_property(src,pin,getattr(u.MaterialProperty,'MP_'+slot)):raise RuntimeError('Cannot bind '+slot)
    def sample(tex,kind):
        n=node('TextureSample');n.texture=tex
        if tex.virtual_texture_streaming:kind='VIRTUAL_'+kind
        n.sampler_type=getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind)
        return n
    mask=sample(pigment,'MASKS')
    oak=sample(require(TIMBER+'Color'),'COLOR')
    normal=sample(require(TIMBER+'NormalDX'),'NORMAL')
    packed=sample(require(TIMBER+'ARH'),'MASKS')
    col=node('Custom')
    col.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    col.set_editor_property('code',"""
float relief=dot(Grain,float3(.30,.57,.13));
float3 bare=Grain*float3(.83,.70,.51)+float3(.032,.022,.013);
float3 paint=lerp(float3(.238,.049,.024),float3(.75,.645,.47),Stencil.g);
paint=lerp(paint,float3(.52,.299,.084),Stencil.b);
paint=lerp(paint,float3(.065,.054,.047),min(Stencil.g,Stencil.b));
return lerp(bare,paint*clamp(.78+relief*.78,.79,1.14),Stencil.r);
""")
    inputs=[]
    for name in ('Grain','Stencil'):
        pin=u.CustomInput();pin.set_editor_property('input_name',name);inputs.append(pin)
    col.set_editor_property('inputs',inputs)
    wire(oak,'RGB',col,'Grain');wire(mask,'RGB',col,'Stencil')
    rough=node('LinearInterpolate')
    n=node('Constant');n.r=.83
    wire(packed,'G',rough,'A');wire(n,'',rough,'B');wire(mask,'R',rough,'Alpha')
    prop(col,'','BASE_COLOR');prop(rough,'','ROUGHNESS');prop(normal,'RGB','NORMAL');prop(packed,'R','AMBIENT_OCCLUSION')
    edit.layout_material_expressions(mat)
    edit.recompile_material(mat)
    save(mat)
    return {'Paint':mat,'Sawn':require(CARPENTER+'Sawn'),'Oak':require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/ArtPassR2/Materials/M_VillageR2_Oak'),
            'Endgrain':require(CARPENTER+'Cut'),'Iron':require('/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor/Materials/M_SmithScaleIron'),
            'Rubbed':require(CARPENTER+'Iron')}
