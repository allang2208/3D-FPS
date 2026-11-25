"""Author the shared village road decal without rebuilding the level."""
from pathlib import Path
import runpy
import unreal as u

def build(plan):
    root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
    ex,ey=plan.get('surface_extent_m',plan['extent_m'])
    dressing=plan['ground_dressing']
    dest='/Game/WorldGeneration/TemperateHills/AbandonedVillage'
    pack='/Game/UnrealNormandy/'
    lib,edit=u.EditorAssetLibrary,u.MaterialEditingLibrary
    assets=u.AssetToolsHelpers.get_asset_tools()
    def require(path):
        obj=u.load_asset(path)
        if not obj:raise RuntimeError(path)
        return obj
    def save(obj):
        if not lib.save_loaded_asset(obj,False):raise RuntimeError('Save failed: '+obj.get_path_name())
    mask=require(dest+'/T_VillageRoadMask')
    name='M_VillageMudRoad'
    mat=(require(dest+'/'+name) if lib.does_asset_exist(dest+'/'+name) else
         assets.create_asset(name,dest,u.Material,u.MaterialFactoryNew()))
    mat.modify()
    edit.delete_all_material_expressions(mat)
    mat.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    def node(cls):
        return edit.create_material_expression(mat,cls)
    def wire(a,out,b,pin):
        names=edit.get_material_expression_input_names(b)
        if pin=='Input' and len(names)==1:pin=str(names[0])
        if not edit.connect_material_expressions(a,out,b,pin): raise RuntimeError('Missing material input '+pin)
    def output(a,pin,prop):
        if not edit.connect_material_property(a,pin,prop): raise RuntimeError(str(prop))
    def sample(texture,sampler,uv):
        s=node(u.MaterialExpressionTextureSample)
        s.texture=texture
        s.sampler_type=sampler
        wire(uv,'',s,'UVs')
        return s
    base_uv=node(u.MaterialExpressionTextureCoordinate)
    coverage=sample(mask,u.MaterialSamplerType.SAMPLERTYPE_MASKS,base_uv)
    road_uv=node(u.MaterialExpressionTextureCoordinate)
    road_uv.u_tiling=2*ex/3.2
    road_uv.v_tiling=2*ey/3.2
    tex=pack+'Textures/T_LC_GroundRockyRoad_00A_'
    color=sample(require(tex+'Albedo'),u.MaterialSamplerType.SAMPLERTYPE_COLOR,road_uv)
    norm=sample(require(tex+'Normal'),u.MaterialSamplerType.SAMPLERTYPE_NORMAL,road_uv)
    packed=require(tex+'RHAOM')
    stype=(u.MaterialSamplerType.SAMPLERTYPE_MASKS if packed.compression_settings==u.TextureCompressionSettings.TC_MASKS
           else (u.MaterialSamplerType.SAMPLERTYPE_COLOR if packed.srgb else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR))
    rough=sample(packed,stype,road_uv)
    # Continue the chapel's scanned earth onto the wall skirts and street verges.
    soil_uv=node(u.MaterialExpressionTextureCoordinate)
    soil_uv.u_tiling=2*ex/dressing['earth_tile_m']
    soil_uv.v_tiling=2*ey/dressing['earth_tile_m']
    soil_path='/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_'
    soil_color=sample(require(soil_path+'B'),u.MaterialSamplerType.SAMPLERTYPE_COLOR,soil_uv)
    soil_normal=sample(require(soil_path+'N'),u.MaterialSamplerType.SAMPLERTYPE_NORMAL,soil_uv)
    def data_sample(path):
        texture=require(path)
        sampler=(u.MaterialSamplerType.SAMPLERTYPE_ALPHA if texture.compression_settings==u.TextureCompressionSettings.TC_ALPHA
                 else u.MaterialSamplerType.SAMPLERTYPE_MASKS if texture.compression_settings==u.TextureCompressionSettings.TC_MASKS
                 else (u.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.srgb else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR))
        return sample(texture,sampler,soil_uv)
    soil_orm=data_sample(soil_path+'ORM')
    soil_height=data_sample(soil_path+'H')
    edge=runpy.run_path(str(Path(__file__).with_name('village_road_blend.py')))
    weights=edge['build_weights'](mat,coverage,base_uv,soil_height,(ex*200.,ey*200.))
    road=node(u.MaterialExpressionComponentMask)
    for key in ('r','g','b','a'):road.set_editor_property(key,key=='r')
    wire(weights,'',road,'Input')
    skirt=node(u.MaterialExpressionComponentMask)
    for key in ('r','g','b','a'):skirt.set_editor_property(key,key=='g')
    wire(weights,'',skirt,'Input')
    opacity=node(u.MaterialExpressionMax)
    wire(road,'',opacity,'A')
    wire(skirt,'',opacity,'B')
    denominator=node(u.MaterialExpressionMax)
    denominator.set_editor_property('const_b',.0001)
    wire(opacity,'',denominator,'A')
    road_weight=node(u.MaterialExpressionDivide)
    wire(road,'',road_weight,'A')
    wire(denominator,'',road_weight,'B')
    def blend(a,apin,b,bpin):
        result=node(u.MaterialExpressionLinearInterpolate)
        wire(a,apin,result,'A')
        wire(b,bpin,result,'B')
        wire(road_weight,'',result,'Alpha')
        return result
    blended_color=blend(soil_color,'RGB',color,'RGB')
    blended_normal=blend(soil_normal,'RGB',norm,'RGB')
    normal_unit=node(u.MaterialExpressionNormalize)
    wire(blended_normal,'',normal_unit,'VectorInput')
    blended_rough=blend(soil_orm,'G',rough,'R')
    output(blended_color,'',u.MaterialProperty.MP_BASE_COLOR)
    output(normal_unit,'',u.MaterialProperty.MP_NORMAL)
    output(blended_rough,'',u.MaterialProperty.MP_ROUGHNESS)
    output(opacity,'',u.MaterialProperty.MP_OPACITY)
    edit.recompile_material(mat)
    save(mat)
    return mat
