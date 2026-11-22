"""Use the coal scan on the crust and restrict self-emission to the fitted bed's cracks."""
from pathlib import Path
import unreal as u

ROOT='/Game/WorldGeneration/TemperateHills/VillageBlacksmith/Workfloor'
SURFACES=ROOT+'/Materials'
HEAT=SURFACES+'/T_SmithEmberBed_Heat'
MATERIAL=SURFACES+'/M_SmithLiveCoals'
HEARTH=ROOT+'/SM_SmithHearthDressing'
DONOR='/Game/WorldGeneration/VillageTavern/KitchenHearth/M_TavernHearthCoal'
e=u.EditorAssetLibrary
lib=u.MaterialEditingLibrary


def save(obj):
    if not e.save_loaded_asset(obj,False):
        raise RuntimeError('Could not save '+obj.get_path_name())


def build_material():
    source=Path(__file__).resolve().parents[4]/'SourceAssets/HillsVillageBlacksmith20261117/Workfloor/T_SmithEmberBed_Heat.png'
    if not e.does_asset_exist(HEAT):
        task=u.AssetImportTask()
        task.filename=str(source)
        task.destination_path=SURFACES
        task.destination_name=HEAT.rsplit('/',1)[1]
        task.automated=True
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture=e.load_asset(HEAT)
    if not texture:raise RuntimeError('Could not import the coal heat mask')
    texture.modify()
    texture.srgb=False
    texture.compression_settings=u.TextureCompressionSettings.TC_MASKS
    texture.address_x=texture.address_y=u.TextureAddress.TA_CLAMP
    texture.lod_group=u.TextureGroup.TEXTUREGROUP_WORLD_SPECULAR
    save(texture)
    mat=e.load_asset(MATERIAL) if e.does_asset_exist(MATERIAL) else e.duplicate_asset(DONOR,MATERIAL)
    if not mat:raise RuntimeError('Could not create the smith coal surface')
    mat.modify()
    # Only this branch belongs to the hot-coal variant. The scan graph is shared in appearance with the bin.
    prefix='Smith ember bed / '
    for n in list(lib.get_material_expressions(mat)):
        if str(n.get_editor_property('desc')).startswith(prefix):lib.delete_material_expression(mat,n)
    def node(kind,label):
        n=lib.create_material_expression(mat,getattr(u,'MaterialExpression'+kind))
        n.set_editor_property('desc',prefix+label)
        return n
    def link(src,pin,target,name):
        if not lib.connect_material_expressions(src,pin,target,name):raise RuntimeError('Could not wire '+name)
    def custom(label,output,code,inputs):
        n=node('Custom',label)
        n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_'+output))
        n.set_editor_property('code',code)
        pins=[]
        for name,_,_ in inputs:
            item=u.CustomInput()
            item.set_editor_property('input_name',name)
            pins.append(item)
        n.set_editor_property('inputs',pins)
        for name,src,pin in inputs:link(src,pin,n,name)
        return n
    world=node('WorldPosition','World position')
    local=node('TransformPosition','Hearth coordinates')
    local.set_editor_property('transform_source_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD)
    local.set_editor_property('transform_type',u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_LOCAL)
    link(world,'',local,'')
    uv=custom('Bed UV','FLOAT2','return (Pos.xy+float2(40,38))/float2(80,64);',[('Pos',local,'')])
    sample=node('TextureSample','Fissures and hot cores')
    sample.texture=texture
    sample.sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS
    link(uv,'',sample,'UVs')
    inverse=node('EyeAdaptationInverse','Exposure compensation')
    emission=custom('Ember light','FLOAT3',"""
float side = 1.0-smoothstep(91.0,95.8,Pos.z);
float red = Heat.r*(0.57+0.43*side) + 0.34*Heat.b*side;
float hot = Heat.g*(0.78+0.22*side);
return (float3(1.85,0.12,0.009)*red+float3(4.4,0.91,0.049)*hot)*InvExposure;
""",[('Pos',local,''),('Heat',sample,'RGB'),('InvExposure',inverse,'')])
    if not lib.connect_material_property(emission,'',u.MaterialProperty.MP_EMISSIVE_COLOR):
        raise RuntimeError('Could not bind coal emission')
    lib.layout_material_expressions(mat)
    lib.recompile_material(mat)
    save(mat)
    return mat


def bind(mesh,mat):
    index,=[i for i,s in enumerate(mesh.static_materials) if str(s.material_slot_name)=='Coal']
    if mesh.get_material(index)!=mat:
        mesh.modify()
        mesh.set_material(index,mat)
        save(mesh)
