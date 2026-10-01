"""Build an ASH-only WS1 graph adapter, preserving its original vertex-color regions.
The shared A762 master/presets are read-only. Assets only, no PIE/render/test.
"""
import json
from pathlib import Path
import unreal as u

HERE=Path(__file__).parent
ROOT='/Game/Weapons/ASH12/SurfaceStandard20260930'
MASTER=ROOT+'/Master/M_ASH12_WS_Regions'
L,E,A=u.MaterialEditingLibrary,u.EditorAssetLibrary,u.AssetToolsHelpers.get_asset_tools()
CARD=json.loads((HERE.parent/'surface_card.json').read_text(encoding='utf-8'))

def load(path):
    obj=u.load_asset(path)
    if not obj: raise RuntimeError('Missing source '+path)
    return obj

def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())

def node(m,cls,**props):
    n=L.create_material_expression(m,cls)
    for k,v in props.items():n.set_editor_property(k,v)
    return n

def wire(src,dst,pin):
    n,out=src if isinstance(src,tuple) else (src,'')
    if not L.connect_material_expressions(n,out,dst,pin):raise RuntimeError('Cannot wire '+pin)

def custom(m,code,inputs,size,label):
    n=node(m,u.MaterialExpressionCustom,code=code,description=label,
        output_type=getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(size)))
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for k,v in inputs.items():wire(v,n,k)
    return n

if not E.does_asset_exist(MASTER):
    mat=E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',MASTER)
    if not mat:raise RuntimeError('Cannot clone WS1 master')
    expressions=list(L.get_material_expressions(mat))
    params={str(n.get_editor_property('parameter_name')):n for n in expressions
        if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter))}
    code={str(n.get_editor_property('description')):n for n in expressions if isinstance(n,u.MaterialExpressionCustom)}
    region=node(mat,u.MaterialExpressionVertexColor)
    # Original R=grip/butt pad, G=bolt, B=bore. Threshold identities so metal remains 0/1.
    rg=custom(mat,'return step(float3(.5,.5,.5),Mask.rgb);',{'Mask':region},3,'ASH12 authored surface regions')
    def scalar(name,value):
        return node(mat,u.MaterialExpressionScalarParameter,parameter_name=name,default_value=value,group='ASH12 Regions')
    def vector(name,value):
        return (node(mat,u.MaterialExpressionVectorParameter,parameter_name=name,default_value=u.LinearColor(*value,1),group='ASH12 Regions'),'RGB')
    red_color=vector('RegionPolymerColor',(.019,.019,.018))
    red_rough=scalar('RegionPolymerRoughness',.55)
    bolt_color=vector('RegionBoltColor',(.034,.035,.037))
    bolt_rough=scalar('RegionBoltRoughness',.34)
    def mix(base,red,green,blue,size,label):
        def const(v):
            if isinstance(v,(int,float)):return node(mat,u.MaterialExpressionConstant,r=float(v))
            if isinstance(v,list):return node(mat,u.MaterialExpressionConstant3Vector,constant=u.LinearColor(*v,1))
            return v
        return custom(mat,'return lerp(lerp(lerp(Base,Red,Mask.r),Green,Mask.g),Blue,Mask.b);',
            {'Base':base,'Red':const(red),'Green':const(green),'Blue':const(blue),'Mask':rg},size,label)
    # Run all regions through the same grain, cavity and water stages as standard WS1.
    wire(mix((params['FinishColor'],'RGB'),red_color,bolt_color,[.004,.004,.004],3,'ASH12 Finish regions'),code['WS_ColorRough'],'Finish')
    wire(mix(params['Roughness'],red_rough,bolt_rough,.85,1,'ASH12 Roughness regions'),code['WS_ColorRough'],'Rough')
    wire(mix(params['Metallic'],0,1,0,1,'ASH12 Metal identity'),code['WS_MetalAO'],'Metal')
    wire(mix(params['EdgeMetallic'],0,1,0,1,'ASH12 Edge identity'),code['WS_MetalAO'],'EdgeMetal')
    wire(mix(params['EdgeWear'],0,params['EdgeWear'],0,1,'ASH12 Edge exposure'),code['WS_Wear'],'EdgeWear')
    wire(mix((params['EdgeColor'],'RGB'),[.024,.024,.023],[.075,.076,.078],[.004,.004,.004],3,'ASH12 Machined edge regions'),code['WS_ColorRough'],'EdgeColor')
    wire(mix(params['EdgeHighlight'],.05,.06,0,1,'ASH12 Edge highlight regions'),code['WS_ColorRough'],'EdgeHL')
    wire(mix(params['Stipple'],.06,0,0,1,'ASH12 Polymer stipple'),code['WS_ColorRough'],'Stipple')
    spec=mix(params['Specular'],.4,.5,.2,1,'ASH12 Specular regions')
    if not L.connect_material_property(spec,'',u.MaterialProperty.MP_SPECULAR):raise RuntimeError('Specular output')
    wet=custom(mat,'return Wet*(1-Mask.b);',{'Wet':params['WeaponWetness'],'Mask':rg},1,'ASH12 Keep bore dry')
    wire(wet,code['WS_Beads'],'Wet')
    E.set_metadata_tag(mat,'WeaponSurfaceGraph','WS1-ASH12-Regions-g1')
    E.set_metadata_tag(mat,'WeaponSurfaceSource','M_WeaponSurface WS1-g1; ASH12 SurfaceRegions R polymer G bolt B bore')
    errors=[str(x) for x in L.recompile_material(mat)]
    if errors:raise RuntimeError('Material compile: '+str(errors))
    save(mat)
else:
    mat=load(MASTER)
    if E.get_metadata_tag(mat,'WeaponSurfaceGraph')!='WS1-ASH12-Regions-g1':raise RuntimeError('Existing graph belongs to another revision')

created=[]
for key in ('CleanSatinSteel','CleanAnodized','CleanPolymer','Rubber','Interior'):
    name='MI_ASH12_WS_Regions_'+key
    path=ROOT+'/Presets/'+name
    mi=load(path) if E.does_asset_exist(path) else A.create_asset(name,ROOT+'/Presets',u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    L.clear_all_material_instance_parameters(mi)
    mi.set_editor_property('parent',mat)
    for k,v in CARD['presets'][key].get('scalars',{}).items():L.set_material_instance_scalar_parameter_value(mi,k,float(v))
    for k,v in CARD['presets'][key].get('vectors',{}).items():L.set_material_instance_vector_parameter_value(mi,k,u.LinearColor(*v,1))
    L.update_material_instance(mi)
    save(mi);created.append(path)
(HERE/'master_receipt.json').write_text(json.dumps({'master':MASTER,'presets':created,'source':'WS1 shared master; read only','tested':False},indent=1),encoding='utf-8')
print('ASH12_SURFACE_REGIONAL_MASTER_SAVED',MASTER,flush=True)

# ASH-only static master: correct usage flags and the original coating normal scale.
STATIC=ROOT+'/Master/M_ASH12_WS_Static'
if not E.does_asset_exist(STATIC):
    sm=E.duplicate_asset('/Game/Weapons/WeaponSurface/Master/M_WeaponSurface',STATIC)
    for usage in ('used_with_skeletal_mesh','used_with_morph_targets','used_with_clothing','automatically_set_usage_in_editor'):
        sm.set_editor_property(usage,False)
    nrm=next(n for n in L.get_material_expressions(sm) if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SurfaceNormal')
    uv=node(sm,u.MaterialExpressionTextureCoordinate,coordinate_index=0)
    scale=node(sm,u.MaterialExpressionScalarParameter,parameter_name='NormalUVScale',default_value=1.,group='Source')
    mul=node(sm,u.MaterialExpressionMultiply);wire(uv,mul,'A');wire(scale,mul,'B');wire(mul,nrm,'UVs')
    E.set_metadata_tag(sm,'WeaponSurfaceGraph','WS1-ASH12-Static-g1')
    errors=[str(x) for x in L.recompile_material(sm)]
    if errors:raise RuntimeError(str(errors))
    save(sm)
else:sm=load(STATIC)

# Preserve ASH extension's alternate UV and its tangent-frame seam reconstruction.
SEAM=ROOT+'/Master/M_ASH12_WS_ExtMag'
if not E.does_asset_exist(SEAM):
    smg=E.duplicate_asset(STATIC,SEAM)
    expressions=list(L.get_material_expressions(smg))
    nrm=next(n for n in expressions if isinstance(n,u.MaterialExpressionTextureSampleParameter2D) and str(n.get_editor_property('parameter_name'))=='SurfaceNormal')
    wn=next(n for n in expressions if isinstance(n,u.MaterialExpressionCustom) and str(n.get_editor_property('description'))=='WS_WetNormal')
    alt=node(smg,u.MaterialExpressionTextureSampleParameter2D,parameter_name='SurfaceNormal',texture=load('/Engine/EngineMaterials/DefaultNormal'),sampler_type=u.MaterialSamplerType.SAMPLERTYPE_NORMAL,group='Source')
    wire(node(smg,u.MaterialExpressionTextureCoordinate,coordinate_index=1),alt,'UVs')
    packed=[node(smg,u.MaterialExpressionTextureCoordinate,coordinate_index=i) for i in range(2,7)]
    rotate=custom(smg,'return float3(dot(N,float3(A.g,-B.r,B.g)),dot(N,float3(-C.r,C.g,-D.r)),dot(N,float3(D.g,-E.r,E.g)));',
        dict(N=(alt,'RGB'),**{k:v for k,v in zip('ABCDE',packed)}),3,'ASH12 original seam tangent frame')
    blend=custom(smg,'return normalize(lerp(N0,N1,saturate(Packed.r)));',{'N0':(nrm,'RGB'),'N1':rotate,'Packed':packed[0]},3,'ASH12 continuous extension normal')
    wire(blend,wn,'Base')
    E.set_metadata_tag(smg,'WeaponSurfaceGraph','WS1-ASH12-ExtMag-g1')
    errors=[str(x) for x in L.recompile_material(smg)]
    if errors:raise RuntimeError(str(errors))
    save(smg)
print('ASH12_SURFACE_STATIC_MASTERS_SAVED',STATIC,SEAM,flush=True)
