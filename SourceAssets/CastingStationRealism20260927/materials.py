"""Local materials reuse the installed Normandy scans and Clearwater water resources."""
from pathlib import Path
import sys
import unreal as u
ROOT=Path(u.Paths.project_dir());HERE=ROOT/'SourceAssets/CastingStationRealism20260927'
DEST='/Game/Props/CastingStation20260926/RealismV5'
sys.path.insert(0,str(ROOT/'Tools/Forging'))
from forge_materials import node,wire,prop,custom,scalar,vector,surface
E,L,A=u.EditorAssetLibrary,u.MaterialEditingLibrary,u.AssetToolsHelpers.get_asset_tools()

def material(name):
    path=DEST+'/'+name
    m=u.load_asset(path) or A.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    L.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_OPAQUE)
    m.set_editor_property('used_with_nanite',True)
    return m

def tex(m,path,kind,uv):
    t=u.load_asset(path)
    if not t:raise RuntimeError('Missing existing texture '+path)
    n=node(m,u.MaterialExpressionTextureSample);n.set_editor_property('texture',t)
    n.set_editor_property('sampler_type',getattr(u.MaterialSamplerType,'SAMPLERTYPE_'+kind))
    wire(uv,n,'UVs');return n

def anvil(blackened=False):
    m=material('M_BlackenedAnvil' if blackened else 'M_WorkedAnvil');uv=node(m,u.MaterialExpressionTextureCoordinate)
    uv2=custom(m,'return UV*2.5;',{'UV':uv},2)
    root='/Game/Props/BlastFurnace20260923/Textures/T_BlastFurnace_WroughtIron_'
    base=tex(m,root+'BaseColor','COLOR',uv2)
    rough=tex(m,root+'Roughness','MASKS',uv2)
    normal=tex(m,root+'Normal','NORMAL',uv2)
    ao=tex(m,root+'AO','MASKS',uv2)
    metal=tex(m,root+'Metallic','MASKS',uv2)
    wear=node(m,u.MaterialExpressionVertexColor)
    zone=custom(m,'return smoothstep(.2,.95,Wear)*Amount;',{'Wear':(wear,'R'),'Amount':scalar(m,'WorkingFaceAmount',1)})
    body_tint=vector(m,'BodyTint',(.020,.022,.021) if blackened else (.050,.052,.049))
    face_tint=vector(m,'FaceTint',(.065,.068,.064) if blackened else (.115,.119,.112))
    oxide=custom(m,'''float rust=smoothstep(.006,.10,Scan.r-max(Scan.g,Scan.b));
return saturate(rust*.8+(1-Metal)*.22)*(1-Zone*.86);''',
        {'Scan':(base,'RGB'),'Metal':(metal,'R'),'Zone':zone})
    color=custom(m,'''float luminance=dot(Scan,float3(.2126,.7152,.0722));
float variation=lerp(.64,1.24,smoothstep(.015,.32,luminance));
float3 body=lerp(Body*variation,Scan*float3(.16,.15,.15),Oxide*OxideAmount);
float3 face=Face*lerp(.75,1.10,Grain);
float3 steel=lerp(body,face,Zone)*lerp(.48,1,AO);
float ash=smoothstep(.72,.97,Grain)*saturate(Up.z)*.10*(1-Zone);
return lerp(steel,float3(.065,.061,.052),ash);''',
        {'Scan':(base,'RGB'),'Grain':(rough,'R'),'Zone':zone,'AO':(ao,'R'),'Oxide':oxide,
         'OxideAmount':scalar(m,'OxideAmount',.38 if blackened else .72),
         'Up':node(m,u.MaterialExpressionVertexNormalWS),
         'Body':(body_tint,'RGB'),'Face':(face_tint,'RGB')},3)
    nr=custom(m,'return normalize(float3(N.xy*lerp(.32,.06,Zone),max(N.z,.55)));',{'N':(normal,'RGB'),'Zone':zone},3)
    ro=custom(m,'return lerp(clamp(.43+.38*Grain+Oxide*.1,.48,.86),.32+.22*Grain,Zone);',
              {'Grain':(rough,'R'),'Oxide':oxide,'Zone':zone})
    me=custom(m,'return lerp(lerp(.65,.16,Oxide),.82,Zone);',{'Zone':zone,'Oxide':oxide})
    surface(m,{'BASE_COLOR':color,'ROUGHNESS':ro,'METALLIC':me,'NORMAL':nr,'SPECULAR':scalar(m,'Specular',.28 if blackened else .5)})
    return m

def wood(name,barrel):
    m=material(name);uv=node(m,u.MaterialExpressionTextureCoordinate)
    root='/Game/UnrealNormandy/Textures/T_WoodSurface_00A_'
    base=tex(m,root+'BaseColor','COLOR',uv);packed=tex(m,root+'RHAOM','MASKS',uv)
    normal=tex(m,root+'Normal','NORMAL',uv)
    wet=(node(m,u.MaterialExpressionVertexColor),'G') if barrel else scalar(m,'Wetness',0)
    color=custom(m,'''float gray=dot(C,float3(.2126,.7152,.0722));
float dirt=saturate((R-.55)*1.6+(1-AO)*.8);
float3 timber=lerp(gray.xxx,C,.46)*float3(.52,.49,.45);
timber*=lerp(.45,1,AO)*lerp(1,.70,dirt)*lerp(1,.48,saturate(Wet));
float ash=smoothstep(.80,.98,R)*.13*(1-saturate(Wet));
return lerp(timber,float3(.065,.060,.049),ash);''',
        {'C':(base,'RGB'),'Wet':wet,'AO':(packed,'B'),'R':(packed,'R')},3)
    nr=custom(m,'return normalize(float3(N.xy*.40,max(N.z,.6)));',{'N':(normal,'RGB')},3)
    ro=custom(m,'return lerp(clamp(R*.65+.28,.57,.91),.32,saturate(Wet));',{'R':(packed,'R'),'Wet':wet})
    surface(m,{'BASE_COLOR':color,'ROUGHNESS':ro,'METALLIC':scalar(m,'Metallic',0),'NORMAL':nr,'SPECULAR':scalar(m,'Specular',.28)})
    return m

def water():
    m=material('M_QuenchWater');m.set_editor_property('shading_model',u.MaterialShadingModel.MSM_SINGLE_LAYER_WATER)
    m.set_editor_property('two_sided',True)
    uv=node(m,u.MaterialExpressionTextureCoordinate);clock=node(m,u.MaterialExpressionTime)
    wave=custom(m,(HERE/'BasinWaves.hlsl').read_text(),{'UV':uv,'Clock':clock,
      'QuenchTime':scalar(m,'QuenchTime',-10000),'Hit':vector(m,'QuenchPoint',(0,0,0)),
      'Immersion':scalar(m,'Immersion',0)},3)
    prop(m,custom(m,'return float3(0,0,W.x);',{'W':wave},3),'WORLD_POSITION_OFFSET')
    nuv=custom(m,'return UV*1.35+float2(Clock*.012,-Clock*.009);',{'UV':uv,'Clock':clock},2)
    ripple=tex(m,'/Game/Clearwater/T_ClearwaterRipples_N','LINEAR_COLOR',nuv)
    normal=custom(m,'return normalize(float3(-W.yz+(N.xy*2-1)*.10,1));',{'W':wave,'N':(ripple,'RGB')},3)
    prop(m,normal,'NORMAL')
    prop(m,vector(m,'WaterSurfaceTint',(.018,.024,.023)),'BASE_COLOR')
    prop(m,scalar(m,'WaterSurfaceWeight',.015),'OPACITY')
    prop(m,scalar(m,'WaterRoughness',.085),'ROUGHNESS')
    prop(m,scalar(m,'WaterSpecular',.255),'SPECULAR')
    volume=node(m,u.MaterialExpressionSingleLayerWaterMaterialOutput)
    # Same native optical model as the project's Clearwater surface, tuned for a 39 cm tub.
    wire(vector(m,'ScatteringPerCm',(.0012,.00145,.0013)),volume,'ScatteringCoefficients')
    wire(vector(m,'AbsorptionPerCm',(.012,.007,.008)),volume,'AbsorptionCoefficients')
    wire(scalar(m,'WaterPhaseG',.35),volume,'PhaseG')
    wire(scalar(m,'BehindWaterScale',1),volume,'ColorScaleBehindWater')
    return m

def build_surfaces():
    steel=anvil()
    dark=u.load_asset(DEST+'/MI_DarkForgedIron') or A.create_asset('MI_DarkForgedIron',DEST,u.MaterialInstanceConstant,u.MaterialInstanceConstantFactoryNew())
    # Share the actual furnace parent, including its scan, AO, roughness and oxidised iron response.
    furnace=u.load_asset('/Game/Props/BlastFurnace20260923/Materials/M_BlastFurnace_WroughtIron')
    if not furnace:raise RuntimeError('Missing installed furnace iron master')
    L.set_material_instance_parent(dark,furnace)
    L.clear_all_material_instance_parameters(dark)
    return {'AnvilSteel':anvil(True),'FrameSteel':steel,'DarkSteel':dark,'Wood':wood('M_OakDry',False),
      'BarrelWood':wood('M_OakBarrel',True)}

def build():
    result=build_surfaces();result['Water']=water()
    return result
