"""Author denser, wet-to-dry ground blood. No game launch or visual test."""
from pathlib import Path
import unreal as u

L = u.MaterialEditingLibrary
T = u.AssetToolsHelpers.get_asset_tools()
DEST = '/Game/Weapons/GunplayFX/Impacts/Blood'
SRC = Path(u.Paths.project_dir())/'SourceAssets/FleshImpacts20260914/GroundV2'
SRC.mkdir(parents=True, exist_ok=True)


def node(m, cls, **props):
    e = L.create_material_expression(m,cls)
    for k,v in props.items(): e.set_editor_property(k,v)
    return e


def wire(a,b,pin,out=''):
    if isinstance(pin,int): pin=str(L.get_material_expression_input_names(b)[pin])
    if not L.connect_material_expressions(a,out,b,pin): raise RuntimeError('Cannot connect '+pin)


def output(n,prop):
    if not L.connect_material_property(n,'',prop): raise RuntimeError('Cannot connect '+str(prop))


def scalar(m,value):
    return node(m,u.MaterialExpressionConstant,r=value)


def multiply(m,a,b):
    n=node(m,u.MaterialExpressionMultiply);wire(a,n,'A');wire(b,n,'B');return n


def custom(m,code,inputs,kind=u.CustomMaterialOutputType.CMOT_FLOAT1):
    n=node(m,u.MaterialExpressionCustom,code=code,output_type=kind)
    pins=[]
    for name in inputs:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    n.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,n,name)
    return n


mask_code=r'''
float2 p=(UV-.5)*2;
float2 warp=float2(sin(p.y*11+Seed*19),cos(p.x*13+Seed*23))*.021;
p+=warp;
float index=floor(saturate(Seed)*5.99);
float2 q=(p+float2(.08,.02))/float2(.76,.64)*.5+.5;
float2 sampleUV=(float2(fmod(index,3),floor(index/3))+clamp(q,.01,.99))/float2(3,2);
float tex=Texture2DSample(Drops,DropsSampler,sampleUV).b;
float2 bound=smoothstep(0,.035,q)*smoothstep(0,.035,1-q);
float core=smoothstep(.025,.60,tex)*bound.x*bound.y;
float specks=0;
[unroll] for(int i=0;i<9;++i)
{
    float h=frac(sin((i+1)*43.17+Seed*31.3)*43758.5453);
    float angle=i*2.39996+Seed*6.283;
    float2 c=float2(cos(angle),sin(angle))*(.45+h*.36);
    float2 radii=float2(.035+h*.07,.035+h*.10);
    float d=length((p-c)/radii);
    specks=max(specks,1-smoothstep(.72,1,d));
}
float grain=.93+.07*sin(p.x*91+sin(p.y*57))*cos(p.y*83);
return saturate(max(core,specks)*grain*.98);
'''
(SRC/'StainMask.hlsl').write_text(mask_code.strip()+'\n',encoding='utf-8')

path=DEST+'/M_FleshStainV2'
if not u.EditorAssetLibrary.does_asset_exist(path):
    m=T.create_asset('M_FleshStainV2',DEST,u.Material,u.MaterialFactoryNew())
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('material_domain',u.MaterialDomain.MD_DEFERRED_DECAL)
    uv=node(m,u.MaterialExpressionTextureCoordinate)
    drops=u.load_asset('/Game/Realistic_Starter_VFX_Pack_Vol2/Textures/T_Droplets_A')
    if not drops:raise RuntimeError('Restore Realistic Starter VFX Pack Vol 2 first')
    tex=node(m,u.MaterialExpressionTextureObject,texture=drops)
    data=node(m,u.MaterialExpressionDecalColor)
    seed=node(m,u.MaterialExpressionComponentMask,r=True,g=False,b=False,a=False)
    birth=node(m,u.MaterialExpressionComponentMask,r=False,g=True,b=False,a=False)
    wire(data,seed,0);wire(data,birth,0)
    time=node(m,u.MaterialExpressionTime)
    age=custom(m,'return saturate(max(0.0,Clock-Born)/12.0);',{'Clock':time,'Born':birth})
    mask=custom(m,mask_code,{'UV':uv,'Seed':seed,'Drops':tex})
    lifetime=node(m,u.MaterialExpressionDecalLifetimeOpacity)
    output(multiply(m,mask,lifetime),u.MaterialProperty.MP_OPACITY)
    color=custom(m,'return lerp(float3(.25,.008,.005),float3(.10,.0035,.0025),Age);',
                 {'Age':age},u.CustomMaterialOutputType.CMOT_FLOAT3)
    output(color,u.MaterialProperty.MP_BASE_COLOR)
    rough=custom(m,'return lerp(.26,.68,Age);',{'Age':age})
    output(rough,u.MaterialProperty.MP_ROUGHNESS)
    output(scalar(m,.28),u.MaterialProperty.MP_SPECULAR)
    errors=L.recompile_material(m)
    if errors:raise RuntimeError('\n'.join(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Cannot save '+path)
    u.log('FLESH_GROUND_V2_SAVED '+path)

# Read receiving material properties needed to decide whether the ground needs
# a scoped response change. This does not change any world material or run PIE.
for path in ('/Game/WorldGeneration/TemperateHills/M_TemperateGround',
             '/Game/WorldGeneration/TemperateHills/Rivers/M_TemperateRiverGround',
             '/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround'):
    ground=u.load_asset(path)
    if ground:
        u.log('BLOOD_GROUND_SOURCE '+path+' response='+str(ground.get_editor_property('material_decal_response')))

(SRC/'CREDITS.md').write_text('''# Ground blood V2

Original shader/layout; references the unchanged local Realistic Starter VFX Pack Vol 2
T_Droplets_A, using blue as mask from its 3x2 shape atlas. Source/license details are in
../CREDITS.md. No new download or purchase. Do not independently redistribute source textures.

DecalColor R carries shape variation; G carries world-time birth. Shared material interpolates
fresh dark red / low roughness toward dried darker blood / higher roughness over 12 seconds.
Lifetime fade remains controlled by the pooled decal component. No per-decal material instance.
Authoring only; user performs in-game visual/performance testing.
''',encoding='utf-8')
u.log('FLESH_GROUND_V2_CREATED gameplay_not_run')
