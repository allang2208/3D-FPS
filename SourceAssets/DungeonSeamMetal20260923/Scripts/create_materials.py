"""Build new dungeon-only finishes from already acquired Fab texture dependencies."""
import json
import runpy
from pathlib import Path
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
recipe=runpy.run_path(str(ROOT/'Scripts/material_recipe.py'));BASE=recipe['BASE']
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
master_path=BASE+'/Materials/M_FabIndustrialMetalV2'
mat=u.load_asset(master_path)
if not mat:
    mat=A.create_asset('M_FabIndustrialMetalV2',BASE+'/Materials',u.Material,u.MaterialFactoryNew())
    mat.set_editor_property('used_with_instanced_static_meshes',True)
    mat.set_editor_property('used_with_nanite',True)
    mat.set_editor_property('tangent_space_normal',False)
    def node(cls,**props):
        n=L.create_material_expression(mat,getattr(u,'MaterialExpression'+cls))
        for k,v in props.items():n.set_editor_property(k,v)
        return n
    def link(a,out,b,pin):
        if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Cannot connect '+pin)
    def scalar(name,value):return node('ScalarParameter',parameter_name=name,default_value=value)
    def vector(name,value):return node('VectorParameter',parameter_name=name,default_value=u.LinearColor(*value,1))
    custom=node('Custom',code=(ROOT/'Scripts/metal_surface.ush').read_text(encoding='utf-8'),
        description='Fab industrial paint, exposed steel and oxide; instance space',output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    inputs=['Position','SurfaceNormal','Age','BaseTint','RustChannel','EdgeChannel','TileSize','Metallic',
            'Roughness','RustCoverage','DirtStrength','RustBrightness','MicroNormal','RustNormalStrength',
            'RustColor','RustORM','RustNormal','DirtyMetal']
    custom_inputs=[]
    for x in inputs:
        value=u.CustomInput();value.set_editor_property('input_name',x);custom_inputs.append(value)
    custom.set_editor_property('inputs',custom_inputs)
    custom_outputs=[]
    for name,kind in [('NormalLocal',u.CustomMaterialOutputType.CMOT_FLOAT3),('MetalAO',u.CustomMaterialOutputType.CMOT_FLOAT2)]:
        value=u.CustomOutput();value.set_editor_property('output_name',name);value.set_editor_property('output_type',kind);custom_outputs.append(value)
    custom.set_editor_property('additional_outputs',custom_outputs)
    pos=node('TransformPosition',transform_source_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_WORLD,
        transform_type=u.MaterialPositionTransformSource.TRANSFORMPOSSOURCE_INSTANCE)
    link(node('WorldPosition'),'',pos,'');link(pos,'',custom,'Position')
    normal=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_WORLD,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_INSTANCE)
    link(node('VertexNormalWS'),'',normal,'');link(normal,'',custom,'SurfaceNormal')
    link(node('VertexColor'),'',custom,'Age')
    for name,value in [('BaseTint',(.15,.18,.14)),('RustChannel',(1,0,0)),('EdgeChannel',(0,1,0))]:
        link(vector(name,value),'',custom,name)
    for name,value in [('TileSize',100),('Metallic',.05),('Roughness',.53),('RustCoverage',.3),
                       ('DirtStrength',.65),('RustBrightness',.8),('MicroNormal',.10),('RustNormalStrength',.55)]:
        link(scalar(name,value),'',custom,name)
    rust='/Game/SD_Art/Industrial_Infrastructure/Materials/Rust/Textures/T_Tiling_Rust_'
    sources={'RustColor':rust+'Albedo','RustORM':rust+'ORM','RustNormal':rust+'Normal',
        'DirtyMetal':'/Game/ColdSteelUI/Warehouse20260909/DirtyMetal/T_DirtyMetal_MR_4K'}
    for name,path in sources.items():
        texture=u.load_asset(path)
        if not texture:raise RuntimeError('Acquired Fab dependency missing '+path)
        tex=node('TextureObjectParameter',parameter_name=name,texture=texture,
            sampler_type=u.MaterialSamplerType.SAMPLERTYPE_COLOR if name=='RustColor' else
            u.MaterialSamplerType.SAMPLERTYPE_NORMAL if name=='RustNormal' else
            u.MaterialSamplerType.SAMPLERTYPE_MASKS if name=='DirtyMetal' else u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        link(tex,'',custom,name)
    def mask(out,r=False,g=False,b=False,a=False):
        n=node('ComponentMask',r=r,g=g,b=b,a=a);link(custom,out,n,'');return n
    worldnormal=node('Transform',transform_source_type=u.MaterialVectorCoordTransformSource.TRANSFORMSOURCE_INSTANCE,
        transform_type=u.MaterialVectorCoordTransform.TRANSFORM_WORLD)
    link(custom,'NormalLocal',worldnormal,'')
    for n,prop in [(mask('',True,True,True),'BASE_COLOR'),(mask('',a=True),'ROUGHNESS'),
                   (mask('MetalAO',r=True),'METALLIC'),(mask('MetalAO',g=True),'AMBIENT_OCCLUSION'),(worldnormal,'NORMAL')]:
        if not L.connect_material_property(n,'',getattr(u.MaterialProperty,'MP_'+prop)):raise RuntimeError('Output '+prop)
    L.recompile_material(mat)
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Could not save new metal master')
for row in recipe['ROWS']:
    path=BASE+'/Materials/'+row['name'];mi=u.load_asset(path)
    if not mi:mi=A.create_asset(row['name'],BASE+'/Materials',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.set_material_instance_parent(mi,mat)
    for name,key in [('BaseTint','tint'),('RustChannel','channel'),('EdgeChannel','edge')]:
        L.set_material_instance_vector_parameter_value(mi,name,u.LinearColor(*row[key],1))
    for name,key in [('TileSize','tile'),('Metallic','metal'),('Roughness','rough'),('RustCoverage','rust')]:
        L.set_material_instance_scalar_parameter_value(mi,name,row[key])
    L.update_material_instance(mi)
    if not E.save_loaded_asset(mi,False):raise RuntimeError('Could not save '+path)
data=dict(stage='materials_saved',materials=recipe['remap'](),
    sources=['https://www.fab.com/listings/60cf60a7-3646-40ed-bdc9-0159eefb9db0',
             'https://www.fab.com/listings/17d58a5d-f1a8-4417-9e6f-f21ed6fc7031'],
    acquisition='existing imported Fab assets and launcher cache; no new purchase',runtime_tested=False)
(ROOT/'Receipts/materials.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
(ROOT/'Config/material-remap.json').write_text(json.dumps(recipe['remap'](),indent=2),encoding='utf-8')
print('FAB_DUNGEON_MATERIALS_SAVED',len(recipe['ROWS']),flush=True)
