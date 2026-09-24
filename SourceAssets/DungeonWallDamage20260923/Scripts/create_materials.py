"""Import the acquired scan derivatives and save the shared dungeon mineral material."""
import json,sys
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1];BASE='/Game/Dungeons/WallDamage20260923'
E=u.EditorAssetLibrary;L=u.MaterialEditingLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if Path(u.Paths.project_dir()).resolve()!=ROOT.parents[1].resolve():raise RuntimeError('Wrong project')
ue=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if ue and ue.get_game_world():raise RuntimeError('PIE active; finish play before editing')
source=json.loads((ROOT/'Sources/provenance.json').read_text(encoding='utf-8'))
textures={}
for channel,file in source['channels'].items():
    name='T_FabExposedConcrete_'+channel;path=BASE+'/Textures/'+name
    texture=u.load_asset(path)
    if not texture:
        task=u.AssetImportTask();task.filename=file;task.destination_path=BASE+'/Textures';task.destination_name=name
        task.automated=True;task.replace_existing=False;task.save=False;A.import_asset_tasks([task]);texture=u.load_asset(path)
    if not texture:raise RuntimeError('Texture import failed '+path)
    texture.set_editor_property('srgb',channel=='BaseColor')
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_NORMALMAP if channel=='Normal' else u.TextureCompressionSettings.TC_MASKS if channel=='ORM' else u.TextureCompressionSettings.TC_DEFAULT)
    texture.set_editor_property('never_stream',False)
    if channel=='Normal':texture.set_editor_property('flip_green_channel',source['normal_green_flip'])
    if not E.save_loaded_asset(texture,False):raise RuntimeError('Texture save failed')
    textures[channel]=texture
path=BASE+'/Materials/M_FabExposedConcrete';mat=u.load_asset(path)
if not mat:
    mat=A.create_asset('M_FabExposedConcrete',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('tangent_space_normal',False)
    mat.set_editor_property('used_with_instanced_static_meshes',True);mat.set_editor_property('used_with_nanite',True)
    def node(cls,**props):
        n=L.create_material_expression(mat,getattr(u,'MaterialExpression'+cls))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def link(a,out,b,pin):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
    custom=node('Custom',code=(ROOT/'Scripts/concrete_surface.ush').read_text(),output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    names=['Position','SurfaceNormal','ObjectOrigin','TileSize','NormalStrength','Variation','Tint','Brightness','RoughnessScale','ScanColor','ScanORM','ScanNormal']
    inputs=[]
    for name in names:
        ci=u.CustomInput();ci.set_editor_property('input_name',name);inputs.append(ci)
    custom.set_editor_property('inputs',inputs);outputs=[]
    for name,kind in [('NormalLocal',u.CustomMaterialOutputType.CMOT_FLOAT3),('AO',u.CustomMaterialOutputType.CMOT_FLOAT1)]:
        co=u.CustomOutput();co.set_editor_property('output_name',name);co.set_editor_property('output_type',kind);outputs.append(co)
    custom.set_editor_property('additional_outputs',outputs)
    pos=node('TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    link(node('WorldPosition'),'',pos,'');link(pos,'',custom,'Position')
    normal=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_INSTANCE)
    link(node('VertexNormalWS'),'',normal,'');link(normal,'',custom,'SurfaceNormal')
    link(node('ObjectPositionWS'),'',custom,'ObjectOrigin')
    for name,value in [('TileSize',55),('NormalStrength',.85),('Variation',.08),('Brightness',1.12),('RoughnessScale',1.0)]:
        link(node('ScalarParameter',parameter_name=name,default_value=value),'',custom,name)
    link(node('VectorParameter',parameter_name='Tint',default_value=u.LinearColor(1.10,1.02,.92,1)),'',custom,'Tint')
    for channel,pin,sampler in [('BaseColor','ScanColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR),('Normal','ScanNormal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL),('ORM','ScanORM',u.MaterialSamplerType.SAMPLERTYPE_MASKS)]:
        link(node('TextureObjectParameter',parameter_name=pin,texture=textures[channel],sampler_type=sampler),'',custom,pin)
    rgb=node('ComponentMask',r=True,g=True,b=True,a=False);link(custom,'',rgb,'')
    rough=node('ComponentMask',r=False,g=False,b=False,a=True);link(custom,'',rough,'')
    world=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    link(custom,'NormalLocal',world,'')
    for n,pin,prop in [(rgb,'','BASE_COLOR'),(rough,'','ROUGHNESS'),(world,'','NORMAL'),(custom,'AO','AMBIENT_OCCLUSION'),(node('Constant',r=0),'','METALLIC')]:
        if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Output '+prop)
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Master save failed')
# The scan has no height map. Preserve the authored mortar height field when
# rebuilding its two instances; only the broken-concrete section keeps this flat master.
sys.path.insert(0,str(ROOT.parent/'DungeonWallReliefRestore20260924/Scripts'))
from restore_wall_relief import ensure_master,configure_instance,RELIEF_INSTANCES
sys.path.insert(0,str(ROOT.parents[1]/'Tools/AssetPipeline'))
import dungeon_wall_release
relief_master=ensure_master()
rows=[('MI_FabBrokenConcrete',60,1.0,1.03,1.03),('MI_FabExposedBed',55,.78,1.15,1.04),('MI_FabBondingMortar',35,.28,1.20,1.10)]
instances={}
for name,tile,strength,brightness,roughness in rows:
    mi=u.load_asset(BASE+'/Materials/'+name) or A.create_asset(name,BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,relief_master if name in RELIEF_INSTANCES else mat)
    for key,value in [('TileSize',tile),('NormalStrength',strength),('Brightness',brightness),('RoughnessScale',roughness)]:L.set_material_instance_scalar_parameter_value(mi,key,value)
    if name in RELIEF_INSTANCES:configure_instance(mi,relief_master)
    dungeon_wall_release.apply_instance(mi,save_asset=False)
    L.update_material_instance(mi)
    if not E.save_loaded_asset(mi,False):raise RuntimeError('Instance save failed')
    instances[name]=mi.get_path_name().split('.')[0]
mapping={
 '/Game/Dungeons/HazardPolish20260922/Materials/MI_FracturedConcrete':instances['MI_FabBrokenConcrete'],
 '/Game/Dungeons/AtmosphereV2/WallRelief/Materials/MI_WallMortar_Bed':instances['MI_FabExposedBed'],
 '/Game/Dungeons/AtmosphereV2/WallRelief/Materials/MI_WallMortar_Finish':instances['MI_FabBondingMortar']}
(ROOT/'Config/material-remap.json').write_text(json.dumps(mapping,indent=2))
(ROOT/'Receipts/materials.json').write_text(json.dumps(dict(stage='materials_saved',materials=mapping,textures=[t.get_path_name() for t in textures.values()],runtime_tested=False),indent=2))
print('WALL_DAMAGE_MATERIALS_SAVED',len(instances),flush=True)
