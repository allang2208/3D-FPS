"""Create/save only warhammer slam dust, debris and fracture assets. No preview/tests."""
import json
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;R=P.parents[2]
D='/Game/Weapons/SteelWarhammer20261014/SlamFXV2'
if Path(u.Paths.project_dir()).resolve()!=R:raise RuntimeError('Wrong project')
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
receipt={'complete':False,'saved':[],'runtime_tested':False,
    'density_source':'/Game/Weapons/GunplayFX/T_MuzzleSmokeMantaflowV14',
    'pool_slots':8,'max_dust_per_impact':10,'max_debris_per_impact':14,'crack_lifetime_seconds':5}

def save(asset):
    if isinstance(asset,u.Material):
        errors=list(L.recompile_material(asset))
        if errors:raise RuntimeError(str(errors))
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):
        raise RuntimeError('Save failed: '+asset.get_path_name())
    receipt['saved'].append(asset.get_path_name())
    (P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')

def node(m,cls):return L.create_material_expression(m,cls)
def wire(a,b,pin):
    a,out=a if isinstance(a,tuple) else (a,'')
    if not L.connect_material_expressions(a,out,b,pin):raise RuntimeError('Wire '+pin)
def prop(m,a,name):
    if not L.connect_material_property(a,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError(name)
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def constant(m,value):
    n=node(m,u.MaterialExpressionConstant);n.set_editor_property('r',value);return n
def custom(m,code,inputs,width=1):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for key in inputs:
        v=u.CustomInput();v.set_editor_property('input_name',key);pins.append(v)
    n.set_editor_property('inputs',pins)
    for key,value in inputs.items():wire(value,n,key)
    return n
def instance(m,index):
    n=node(m,u.MaterialExpressionPerInstanceCustomData);n.set_editor_property('data_index',index)
    v=node(m,u.MaterialExpressionVertexInterpolator);wire(n,v,str(L.get_material_expression_input_names(v)[0]));return v
def material(name,translucent=False,decal=False):
    m=u.load_asset(D+'/'+name) if E.does_asset_exist(D+'/'+name) else A.create_asset(name,D,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT if translucent or decal else u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL if decal else u.MaterialDomain.MD_SURFACE)
    m.set_editor_property('two_sided',translucent)
    if not decal:L.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES,True)
    if translucent:
        m.set_editor_property('disable_depth_test',False)
        m.set_editor_property('allow_front_layer_translucency',False)
        m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    return m
def surface(m,color,alpha=None,decal=False):
    slab=node(m,u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override',u.MaterialShadingModel.MSM_DEFAULT_LIT)
    wire(color,slab,'BaseColor');wire(constant(m,.95),slab,'Roughness');wire(constant(m,.12),slab,'Specular')
    if alpha:wire(alpha,slab,'Opacity')
    if decal:
        conv=node(m,u.MaterialExpressionSubstrateConvertToDecal)
        wire(slab,conv,str(L.get_material_expression_input_names(conv)[0]));slab=conv
    prop(m,slab,'FRONT_MATERIAL')

m=material('M_WarhammerDust',translucent=True)
tex=node(m,u.MaterialExpressionTextureObjectParameter);tex.set_editor_property('parameter_name','DensityAtlas')
atlas=u.load_asset(receipt['density_source'])
if not atlas:raise RuntimeError('Missing original Mantaflow atlas')
tex.set_editor_property('texture',atlas)
tex.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
seed=instance(m,1)
density=custom(m,(P/'RollingSmoke.hlsl').read_text(),{
    'UV':node(m,u.MaterialExpressionTextureCoordinate),'Atlas':tex,'Age':instance(m,2),'Seed':seed,'Alpha':instance(m,0)})
fade=node(m,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',12.)
wire(density,fade,str(L.get_material_expression_input_names(fade)[0]))
color=custom(m,'return lerp(float3(.22,.19,.15),float3(.34,.30,.25),Seed);',{'Seed':seed},3)
surface(m,color,fade);save(m)

m=material('M_WarhammerDebris')
position=node(m,u.MaterialExpressionWorldPosition)
color=custom(m,'float g=frac(sin(dot(floor(P*2),float3(12.9898,78.233,19.43)))*43758.5453); return lerp(float3(.075,.068,.058),float3(.23,.21,.18),g);',{'P':position},3)
surface(m,color);save(m)
rockmat=m

m=material('M_WarhammerCracks',decal=True)
field=custom(m,(P/'Cracks.hlsl').read_text(),{'UV':node(m,u.MaterialExpressionTextureCoordinate),
    'Age':scalar(m,'Age',.5),'Seed':scalar(m,'Seed',.5)},3)
alpha=custom(m,'return F.x;',{'F':field})
color=custom(m,'return lerp(float3(.012,.011,.009),float3(.25,.23,.20),F.z);',{'F':field},3)
surface(m,color,alpha,decal=True);save(m)

u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False
opt.static_mesh_import_data.auto_generate_collision=False
task=u.AssetImportTask();task.filename=str(P/'SM_WarhammerDebris.fbx');task.destination_path=D
task.destination_name='SM_WarhammerDebris';task.automated=True;task.save=False;task.replace_existing=True;task.options=opt
A.import_asset_tasks([task])
mesh=u.load_asset(D+'/SM_WarhammerDebris')
if not mesh:raise RuntimeError('Mesh import failed')
mesh.set_material(0,rockmat);save(mesh)
receipt['complete']=True
(P/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('WARHAMMER_SLAM_FX_SAVED '+json.dumps(receipt))
