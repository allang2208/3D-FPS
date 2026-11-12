"""Idempotent wet-forest layers used by incremental and canonical authors.
No saves or map changes here; callers own compilation, backups and saving.
"""
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
DATA=ROOT/'SourceAssets/HillsWetForest20261111'
MPC='/Game/WorldGeneration/TemperateHills/Atmosphere20261110/MPC_ForestWind'
GRASS_MPC='/Game/PN_GrassLibrary/Materials/PN_WindParameters'
MOSS='/Game/WorldGeneration/TemperateHills/WetForest/Textures/T_RainforestMoss_'
JUNGLE='/Game/WorldGeneration/TemperateHills/WetForest/Textures/T_JungleGround_'
CARPET='/Game/WorldGeneration/TemperateHills/WetForest/Textures/T_LivingGrass_'
TAG='HillsWet20261111.'
L=u.MaterialEditingLibrary

def node(mat, cls, key):
    found=next((n for n in L.get_material_expressions(mat) if str(n.get_editor_property('desc'))==TAG+key),None)
    if found:
        if not isinstance(found,cls):raise RuntimeError('Wet layer node type changed: '+key)
        return found
    found=L.create_material_expression(mat,cls)
    found.set_editor_property('desc',TAG+key)
    return found

def wire(value, target, pin):
    source, output=value if isinstance(value,tuple) else (value,'')
    if isinstance(target,u.MaterialExpressionReroute):pin=''
    if not L.connect_material_expressions(source,output,target,pin):raise RuntimeError('Wet forest input '+pin)

def custom(mat,key,code,inputs,width=1):
    n=node(mat,u.MaterialExpressionCustom,key)
    n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,n,name)
    return n

def common(mat,collection_path=MPC):
    collection=u.load_asset(collection_path)
    if not collection:raise RuntimeError('Missing existing forest wind MPC')
    def vector(name):
        n=node(mat,u.MaterialExpressionCollectionParameter,name)
        n.set_editor_property('collection',collection);n.set_editor_property('parameter_name',name)
        return n
    p=node(mat,u.MaterialExpressionWorldPosition,'WorldPosition')
    p.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    weather=vector('RainforestWeather')
    region=custom(mat,'RegionMask',(DATA/'RainforestMask.hlsl').read_text(),
        {'P':p,'Region':vector('RainforestRegion'),'Control':vector('RainforestControl')})
    return p,weather,region

def rain(mat,p,weather):
    spacing=node(mat,u.MaterialExpressionScalarParameter,'RainRippleSpacing')
    spacing.set_editor_property('parameter_name','RainRippleSpacingCm')
    spacing.set_editor_property('default_value',72. if mat.get_name()=='M_RiverPilot' else 47.)
    return custom(mat,'RainRipples',(DATA/'RainRipples.hlsl').read_text(),
        {'P':p,'Camera':node(mat,u.MaterialExpressionCameraPositionWS,'Camera'),
         'Clock':node(mat,u.MaterialExpressionTime,'Clock'),'Spacing':spacing,
         'Rain':custom(mat,'RainIntensity','return Weather.y;',{'Weather':weather})},3)

def output(mat,name):
    prop=getattr(u.MaterialProperty,'MP_'+name)
    n=L.get_material_property_input_node(mat,prop)
    if not n:raise RuntimeError('Missing baseline '+mat.get_path_name()+' '+name)
    return n,L.get_material_property_input_node_output_name(mat,prop)

def connect(mat,name,value):
    n,pin=value if isinstance(value,tuple) else (value,'')
    if not L.connect_material_property(n,pin,getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError(name)

def anchor(mat,name,key):
    # A named reroute preserves the input/output channel without serializing a
    # path to a transient expression. Reruns never wrap the layer in itself.
    tag=TAG+key
    n=next((n for n in L.get_material_expressions(mat) if str(n.get_editor_property('desc'))==tag),None)
    source=output(mat,name)
    if n and str(source[0].get_editor_property('desc')).startswith(TAG):return n
    n=n or node(mat,u.MaterialExpressionReroute,key);wire(source,n,'Input');return n

def apply_grass(mat):
    # PN wind + bending already consume both allowed collection slots. Reuse
    # the existing wind collection, as the existing grass interaction does.
    p,weather,region=common(mat,GRASS_MPC)
    for name in ('BASE_COLOR','SUBSURFACE_COLOR'):
        mark='TemperateDryMeadow_'+name
        n=next((n for n in L.get_material_expressions(mat) if str(n.get_editor_property('desc'))==mark),None)
        if not n:raise RuntimeError('Missing grass colour contract '+mark)
        pins=list(n.get_editor_property('inputs'))
        for pin in ('Forest','Weather'):
            if not any(str(i.get_editor_property('input_name'))==pin for i in pins):
                item=u.CustomInput();item.set_editor_property('input_name',pin);pins.append(item)
        n.set_editor_property('inputs',pins);wire(region,n,'Forest');wire(weather,n,'Weather')
        n.set_editor_property('code','''
float patch=.5+.25*sin(P.x*.0011+P.y*.0007)+.25*sin(P.y*.0015-P.x*.0004);
float dry=saturate(Dryness+(R-.5)*Variation+(patch-.5)*.22);
float mix=saturate(.65+(R-.5)*.45+(patch-.5)*.35);
float3 tint=lerp(OliveTint,DryTint,mix);
float luminance=dot(C,float3(.299,.587,.114));
float3 meadow=lerp(C,luminance*tint,dry);
// Muted green variation, consistent on colour and light transmission.
float3 green=lerp(C,luminance*float3(.45,1.05,.28),.78);
green*=lerp(.98,.86,saturate(Weather.x))*(.94+.12*patch);
return lerp(meadow,green,saturate(Forest));
''')
    rough=anchor(mat,'ROUGHNESS','GrassRoughnessAnchor')
    connect(mat,'ROUGHNESS',custom(mat,'GrassRoughness',
        'return lerp(saturate(Base),lerp(.56,.34,saturate(Weather.x)),Forest);',
        {'Base':rough,'Weather':weather,'Forest':region}))

def apply_ground(mat,outputs=None):
    p,weather,region=common(mat)
    # Recolour only the grass family before soil, pebbles and scanned leaf litter
    # are composited; the forest floor must not become uniformly green mud.
    color=next((n for n in L.get_material_expressions(mat) if str(n.get_editor_property('desc'))=='GroundBaseColor'),None)
    if not color:raise RuntimeError('Ground grass family contract missing')
    pins=list(color.get_editor_property('inputs'))
    if not any(str(i.get_editor_property('input_name'))=='Forest' for i in pins):
        item=u.CustomInput();item.set_editor_property('input_name','Forest');pins.append(item)
    color.set_editor_property('inputs',pins);wire(region,color,'Forest')
    color.set_editor_property('code','''
float luminance=dot(A.rgb,float3(.299,.587,.114));
float3 grass=lerp(A.rgb,luminance*float3(.48,.88,.27),saturate(Forest)*.64);
float3 a=grass*W.x+B.rgb*W.y+C.rgb*W.z+D.rgb*W.w;
float grain=dot(DT.rgb,float3(.30,.59,.11));
return a*(1.0+Macro)*lerp(1.0,.78+.44*grain,saturate(DS*Fade));
''')
    base={}
    for name in ('BASE_COLOR','NORMAL','ROUGHNESS','AMBIENT_OCCLUSION'):
        if outputs:
            base[name]=node(mat,u.MaterialExpressionReroute,'GroundAnchor'+name)
            wire(outputs[name],base[name],'Input')
        else:base[name]=anchor(mat,name,'GroundAnchor'+name)
    habitat=node(mat,u.MaterialExpressionTextureCoordinate,'HabitatUV')
    habitat.set_editor_property('coordinate_index',1)
    vertex=node(mat,u.MaterialExpressionVertexColor,'GroundVertex')
    normal=node(mat,u.MaterialExpressionVertexNormalWS,'GroundSlope')
    base,moss_mask,moss_packed=rainforest_floor(mat,base,p,weather,habitat,vertex,normal)
    height=next((n for n in L.get_material_expressions(mat) if str(n.get_editor_property('desc'))=='GroundMaskedSample_T_ForestFloor_ARH'),None)
    if not height:raise RuntimeError('Forest floor height input missing')
    height=custom(mat,'SurfacePuddleHeight','return lerp(Litter,Moss,Mask);',
        {'Litter':height,'Moss':moss_packed,'Mask':moss_mask},4)
    coverage=node(mat,u.MaterialExpressionScalarParameter,'FilmCoverage')
    coverage.set_editor_property('parameter_name','RainforestPuddleCoverage');coverage.set_editor_property('default_value',.95)
    mask=custom(mat,'PuddleMask','''
float patch=.5+.25*sin(P.x*.012+P.y*.004)+.25*sin(P.y*.017-P.x*.006);
float wet=smoothstep(.07,.46,Weather.x)*saturate(Coverage);
float flat=smoothstep(.938,.992,N.z);
// Rising wetness joins separate hollows. Detailed relief breaks up the
// edge of the film without punching holes through the centre of a puddle.
float level=Habitat.y+.16*(patch-.5)+.14*(.5-H.b);
float film=smoothstep(.72-.34*wet,.94-.32*wet,level);
return saturate(Habitat.x*flat*film*wet*(1-smoothstep(.02,.55,Bank.r)));
''',{'P':p,'Weather':weather,'N':normal,'H':height,'Coverage':coverage,'Habitat':habitat,'Bank':vertex})
    ripple=rain(mat,p,weather)
    step_inputs={}
    for i in range(3):
        name='RainforestStep'+str(i)
        n=node(mat,u.MaterialExpressionVectorParameter,name);n.set_editor_property('parameter_name',name)
        n.set_editor_property('default_value',u.LinearColor(0,0,-10000,0));step_inputs['S'+str(i)]=n
    step=custom(mat,'StepRings','''
float2 slope=0;
if(Mask<.025)return float3(0,0,0);
float3 stamps[3]={S0,S1,S2};
[unroll] for(int i=0;i<3;i++)
{
    float age=T-stamps[i].z;
    if(age<0||age>=1.1)continue;
    float2 d=P.xy-stamps[i].xy;
    float r=length(d),band=(r-(3+age*52))/3.9;
    slope+=d/max(r,.01)*sin(band*2.2)*exp(-band*band)*smoothstep(0,.07,age)*(1-smoothstep(.35,1.1,age));
}
return float3(slope*.21,0);
''',{'P':p,'Mask':mask,'T':node(mat,u.MaterialExpressionTime,'Clock'),**step_inputs},3)
    new={
        'BASE_COLOR':custom(mat,'GroundColor','return lerp(Base,Base*.64,Mask);',{'Base':base['BASE_COLOR'],'Mask':mask},3),
        'ROUGHNESS':custom(mat,'GroundRoughness','return lerp(Base,.065,Mask);',{'Base':base['ROUGHNESS'],'Mask':mask}),
        'AMBIENT_OCCLUSION':base['AMBIENT_OCCLUSION'],
        'NORMAL':custom(mat,'GroundNormal','''
float3 wetWorld=normalize(float3(Rain.xy+Foot.xy,1));
float3 wetTangent=TransformWorldVectorToTangent(Parameters.TangentToWorld,wetWorld);
return normalize(lerp(Base,wetTangent,Mask));
''',{'Base':base['NORMAL'],'Rain':ripple,'Foot':step,'Mask':mask},3)}
    spec_pin=L.get_material_property_input_node(mat,u.MaterialProperty.MP_SPECULAR)
    if outputs and 'SPECULAR' in outputs:
        spec=node(mat,u.MaterialExpressionReroute,'GroundAnchorSPECULAR')
        wire(outputs['SPECULAR'],spec,'Input')
    elif spec_pin:
        spec=anchor(mat,'SPECULAR','GroundAnchorSPECULAR')
    else:
        spec=node(mat,u.MaterialExpressionConstant,'GroundDrySpecular')
        spec.set_editor_property('r',.5)
        anchor_pin=node(mat,u.MaterialExpressionReroute,'GroundAnchorSPECULAR')
        wire(spec,anchor_pin,'Input');spec=anchor_pin
    # UE's dielectric specular scalar of .25 corresponds to water F0 near .02.
    new['SPECULAR']=custom(mat,'GroundSpecular','return lerp(Dry,.25,Mask);',{'Dry':spec,'Mask':mask})
    if outputs:
        return {**outputs,**new}
    for name,value in new.items():connect(mat,name,value)

def rainforest_floor(mat,base,p,weather,habitat,vertex,normal):
    """Living grass and moss on land. Wet hollows expose the jungle litter scan.

    Reuse shared wrap samplers and branch before fetching outside the pocket.
    All three maps share translated stochastic tiles; normals are never rotated.
    """
    gate=custom(mat,'MossCoverage','''
// UV1.x is written by the terrain using the saved seed and trail exclusion.
// The land cover does not depend on a weather actor publishing an MPC first.
return smoothstep(0,.90,Habitat.x)*smoothstep(.72,.88,N.z)*(1-smoothstep(.12,.80,Bank.r));
''',{'Habitat':habitat,'N':normal,'Bank':vertex})
    hollow=custom(mat,'CarpetWetHollow','return smoothstep(.64,1.,Habitat.y)*lerp(.42,1.,saturate(Weather.x));',
        {'Habitat':habitat,'Weather':weather})
    uv=custom(mat,'MossUV','return P.xy/100.0+float2(.317,.739);',{'P':p},2)
    def texture_object(family,prefix,suffix,sampler):
        texture=u.load_asset(prefix+suffix)
        if not texture:raise RuntimeError('Missing rainforest scan '+prefix+suffix)
        tex=node(mat,u.MaterialExpressionTextureObject,family+'Texture'+suffix)
        tex.set_editor_property('texture',texture)
        tex.set_editor_property('sampler_type',sampler)
        return tex
    def sample(suffix,sampler,is_normal=False):
        tex=texture_object('Moss',MOSS,suffix,sampler)
        jungle=texture_object('Jungle',JUNGLE,suffix,sampler)
        carpet=texture_object('Carpet',CARPET,suffix,sampler)
        neutral='float4(0,0,1,1)' if is_normal else 'float4(.5,.5,.5,1)'
        code='float2 gx=ddx(UV),gy=ddy(UV);\n[branch] if(Gate<=0) return '+neutral+';\n'
        code+='''
float2 q=UV*.5;
float2 skew=float2(q.x-q.y*.5773502692,q.y*1.1547005384);
float2 cell=floor(skew),f=frac(skew),id0,id1,id2;
float3 w;
if(f.x+f.y<=1)
{id0=cell;id1=cell+float2(1,0);id2=cell+float2(0,1);w=float3(1-f.x-f.y,f.x,f.y);}
else
{id0=cell+1;id1=cell+float2(0,1);id2=cell+float2(1,0);w=float3(f.x+f.y-1,1-f.x,1-f.y);}
w=w*w;w=w*w;w/=max(dot(w,float3(1,1,1)),.00001);
float4 result=0;
'''
        # Select one physical scan per lattice vertex. Neighbouring triangles
        # share that vertex. The same three fetches blend moss and leaf litter.
        for i in range(3):
            code+=f'''
{{
    float2 id=id{i};
    float2 offset=frac(sin(float2(dot(id,float2(127.1,311.7)),dot(id,float2(269.5,183.3))))*43758.5453);
    float mossChance=.18+.06*sin(dot(id,float2(.19,.27)));
    float4 texel;
    [branch] if(offset.x<mossChance)
    {{
        texel=Texture2DSampleGrad(Tex,GetMaterialSharedSampler(TexSampler,Material.Wrap_WorldGroupSettings),UV+offset*8,gx,gy);
    }}
    else
        texel=Texture2DSampleGrad(Carpet,GetMaterialSharedSampler(CarpetSampler,Material.Wrap_WorldGroupSettings),UV*.5+offset*8,gx*.5,gy*.5);
    [branch] if(WetHollow>.01)
        texel=lerp(texel,Texture2DSampleGrad(Jungle,GetMaterialSharedSampler(JungleSampler,Material.Wrap_WorldGroupSettings),UV*.5+offset*8,gx*.5,gy*.5),WetHollow*.89);
    result+=w[{i}]*{'UnpackNormalMap(texel)' if is_normal else 'texel'};
}}
'''
        code+=('return float4(normalize(result.xyz),1);' if is_normal else 'return result;')
        return custom(mat,'MossSample'+suffix,code,{'Tex':tex,'Jungle':jungle,'Carpet':carpet,'UV':uv,'Gate':gate,'WetHollow':hollow},4)
    color=sample('BaseColor',u.MaterialSamplerType.SAMPLERTYPE_COLOR)
    n=sample('Normal',u.MaterialSamplerType.SAMPLERTYPE_NORMAL,True)
    packed=sample('ARH',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    mask=custom(mat,'MossBlend','''
// Height breaks up only the boundary: the interior fully replaces pale dry soil.
return saturate(Gate+Gate*(1-Gate)*(Packed.b-.5)*1.6);
''',{'Gate':gate,'Packed':packed})
    wetness=custom(mat,'MossWetness','return saturate(max(Weather.x,Bank.g));',
        {'Weather':weather,'Bank':vertex})
    result={
        'BASE_COLOR':custom(mat,'MossColor','''
float patch=.5+.25*sin(P.x*.0013+P.y*.0007)+.25*sin(P.y*.0021-P.x*.0004);
float3 moss=Scan.rgb*float3(.91,1.04,.91)*(.94+.12*patch)*lerp(1.0,.85,Wet);
return lerp(Base,moss,Mask);
''',{'Base':base['BASE_COLOR'],'Scan':color,'P':p,'Wet':wetness,'Mask':mask},3),
        'NORMAL':custom(mat,'MossNormal','return normalize(lerp(Base,normalize(float3(Scan.xy*.85,Scan.z)),Mask));',
            {'Base':base['NORMAL'],'Scan':n,'Mask':mask},3),
        'ROUGHNESS':custom(mat,'MossRoughness','return lerp(Base,lerp(clamp(Packed.g,.62,.96),.44,Wet),Mask);',
            {'Base':base['ROUGHNESS'],'Packed':packed,'Wet':wetness,'Mask':mask}),
        'AMBIENT_OCCLUSION':custom(mat,'MossAO','return lerp(Base,lerp(1,clamp(Packed.r,.65,1),.65),Mask);',
            {'Base':base['AMBIENT_OCCLUSION'],'Packed':packed,'Mask':mask})}
    return result,mask,packed

def apply_water(mat):
    p,weather,_=common(mat)
    normal=anchor(mat,'NORMAL','WaterNormalAnchor')
    ripple=rain(mat,p,weather)
    # NativeWater normals are world-space. Preserve waves and impact/wake fields.
    if mat.get_editor_property('tangent_space_normal'):raise RuntimeError('Expected native water world-space normals')
    connect(mat,'NORMAL',custom(mat,'WaterRainNormal',
        'return normalize(float3(Base.xy+Rain.xy,max(.2,Base.z)));',{'Base':normal,'Rain':ripple},3))

def ensure_collection(path=MPC):
    collection=u.load_asset(path)
    values=list(collection.get_editor_property('vector_parameters'))
    names={str(v.get_editor_property('parameter_name')) for v in values}
    for name,value in (('RainforestRegion',(-12000,10000,11000,8500)),('RainforestControl',(0,.35,0,0)),('RainforestWeather',(0,0,0,0))):
        if name not in names:
            p=u.CollectionVectorParameter();p.set_editor_property('parameter_name',name);p.set_editor_property('default_value',u.LinearColor(*value));values.append(p)
    collection.set_editor_property('vector_parameters',values)
    return collection
