"""Generate owned, texture-free weather presentation; never save source packages.
Run via UnrealEditor-Cmd -run=pythonscript -script=<this file> -unattended.
Existing licensed gun textures remain referenced locally and are not redistributed.
"""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir())
OUT = ROOT/'Saved/WeatherPresentation20260912'
OUT.mkdir(parents=True, exist_ok=True)
SHADERS = ROOT/'SourceAssets/WeatherNatural20260912'
DEST = '/Game/Weather/NaturalV2'
LIB = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
API = unreal.get_default_object(unreal.NiagaraToolset_System)
REPORT = {'materials': [], 'mapping': {}, 'sky_mapping': {}, 'systems': [], 'skipped': []}

def node(m, cls): return LIB.create_material_expression(m, cls)
def wire(a, b, pin, output=''): assert LIB.connect_material_expressions(a, output, b, pin)
def prop(a, name): assert LIB.connect_material_property(a, '', getattr(unreal.MaterialProperty, 'MP_'+name))
def scalar(m, name, value):
    n=node(m, unreal.MaterialExpressionScalarParameter)
    n.set_editor_property('parameter_name', name)
    n.set_editor_property('default_value', value)
    return n
def constant(m, value):
    n=node(m, unreal.MaterialExpressionConstant);n.set_editor_property('r',value);return n
def vector(m, value):
    n=node(m, unreal.MaterialExpressionConstant3Vector);n.set_editor_property('constant',unreal.LinearColor(*value,1));return n
def custom(m, code, inputs, kind, label=''):
    n=node(m,unreal.MaterialExpressionCustom)
    n.set_editor_property('code',code)
    n.set_editor_property('output_type',getattr(unreal.CustomMaterialOutputType,'CMOT_FLOAT'+str(kind)))
    n.set_editor_property('description',label)
    entries=[]
    for name in inputs:
        i=unreal.CustomInput();i.set_editor_property('input_name',name);entries.append(i)
    n.set_editor_property('inputs',entries)
    for name, source in inputs.items():
        if isinstance(source,tuple):wire(source[0],n,name,source[1])
        else:wire(source,n,name)
    return n
def create(name):
    m=unreal.load_asset(DEST+'/'+name) if unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+name) else None
    if not m:m=TOOLS.create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
    return m
def save(m):
    if isinstance(m,unreal.Material):LIB.recompile_material(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m,False),m.get_path_name()
    if isinstance(m,unreal.MaterialInterface):REPORT['materials'].append(m.get_path_name())
    return m
def duplicate(source, name):
    dest=DEST+'/'+name
    if unreal.EditorAssetLibrary.does_asset_exist(dest):return unreal.load_asset(dest),False
    return TOOLS.duplicate_asset(name,DEST,source),True

def lens():
    m=create('M_ScreenEdgeRain')
    if LIB.get_material_expressions(m):
        for n in LIB.get_material_expressions(m):
            if isinstance(n,unreal.MaterialExpressionCustom):n.set_editor_property('code',(SHADERS/'ScreenEdgeRain.hlsl').read_text())
        return save(m)
    m.set_editor_property('material_domain',unreal.MaterialDomain.MD_POST_PROCESS)
    m.set_editor_property('blendable_location',unreal.BlendableLocation.BL_SCENE_COLOR_AFTER_TONEMAPPING)
    uv=node(m,unreal.MaterialExpressionScreenPosition)
    scene=node(m,unreal.MaterialExpressionSceneTexture)
    scene.set_editor_property('scene_texture_id',unreal.SceneTextureId.PPI_POST_PROCESS_INPUT0)
    result=custom(m,(SHADERS/'ScreenEdgeRain.hlsl').read_text(),dict(
        UV=(uv,'ViewportUV'),Scene=(scene,'Color'),InvSize=(scene,'InvSize'),
        Time=node(m,unreal.MaterialExpressionTime),Wet=scalar(m,'ScreenWetness',0),
        Strength=scalar(m,'RainStrength',.75),Aim=scalar(m,'AimProtection',0)),3,'Screen edge droplets')
    prop(result,'EMISSIVE_COLOR');return save(m)

def wet_master(source):
    key=hashlib.sha1(source.get_path_name().encode()).hexdigest()[:10]
    m,fresh=duplicate(source,'M_Wet_'+source.get_name()+'_'+key)
    if not fresh:
        for n in LIB.get_material_expressions(m):
            if isinstance(n,unreal.MaterialExpressionCustom) and n.get_editor_property('description')=='WeatherBeads':
                n.set_editor_property('code',(SHADERS/'WeaponBeads.hlsl').read_text())
        return save(m)
    original={}
    for name,default in [('BASE_COLOR',(.5,.5,.5)),('ROUGHNESS',.5),('NORMAL',(0,0,1))]:
        p=getattr(unreal.MaterialProperty,'MP_'+name)
        src=LIB.get_material_property_input_node(m,p)
        original[name]=(src,LIB.get_material_property_input_node_output_name(m,p)) if src else (vector(m,default) if isinstance(default,tuple) else constant(m,default))
    data=custom(m,(SHADERS/'WeaponBeads.hlsl').read_text(),dict(UV=node(m,unreal.MaterialExpressionTextureCoordinate),Wet=scalar(m,'WeaponWetness',0)),4,'WeatherBeads')
    prop(custom(m,'return Base * (1 - Data.a * .07);',dict(Base=original['BASE_COLOR'],Data=data),3),'BASE_COLOR')
    prop(custom(m,'return lerp(lerp(Base,max(.085,Base*.70),Data.a),.065,Data.b*.8);',dict(Base=original['ROUGHNESS'],Data=data),1),'ROUGHNESS')
    prop(custom(m,'if(Data.a<.0001)return Base;return normalize(float3(Base.xy*(1-Data.b*.35)+Data.xy,Base.z));',dict(Base=original['NORMAL'],Data=data),3),'NORMAL')
    LIB.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_SKELETAL_MESH)
    return save(m)

masters={}
def wet_material(source):
    path=source.get_path_name()
    if path in REPORT['mapping']:return unreal.load_asset(REPORT['mapping'][path])
    # Preserve glass, emissive reticles and hands; they need different optical treatment.
    if any(s in path.lower() for s in ['manny','armsblack','reticle','lens','glass']):return None
    base=source
    while isinstance(base,unreal.MaterialInstance):base=base.get_editor_property('parent')
    if not isinstance(base,unreal.Material):return None
    if base.get_editor_property('blend_mode') not in [unreal.BlendMode.BLEND_OPAQUE,unreal.BlendMode.BLEND_MASKED]:
        REPORT['skipped'].append(path);return None
    if LIB.get_material_property_input_node(base,unreal.MaterialProperty.MP_MATERIAL_ATTRIBUTES) or LIB.get_material_property_input_node(base,unreal.MaterialProperty.MP_FRONT_MATERIAL):
        REPORT['skipped'].append(path);return None
    master=masters.get(base.get_path_name())
    if not master:master=wet_master(base);masters[base.get_path_name()]=master
    if isinstance(source,unreal.MaterialInstanceConstant):
        key=hashlib.sha1(path.encode()).hexdigest()[:10]
        result,_=duplicate(source,'MI_Wet_'+source.get_name()+'_'+key)
        LIB.set_material_instance_parent(result,master);save(result)
    else:result=master
    REPORT['mapping'][path]=result.get_path_name()
    return result

def gun_materials():
    sources={}
    paths=['/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416','/Game/Weapons/AKMIntegration/SovietFab/Attachments/SK_AKM_MannyNative']
    for p in paths:
        mesh=unreal.load_asset(p);assert mesh,p
        for slot in mesh.get_editor_property('materials'):
            mat=slot.get_editor_property('material_interface')
            if mat:sources[mat.get_path_name()]=mat
    dirs=['M4AngledForegripCompact75','M4CantedForegrip','M4Drum','M4FoldingSights','PrismHandstopV1','M4VerticalGripCompact75','M4Holographic','LPVO1to6X','PrismScope2XMachined','PanoramicRedDot','M4Muzzle','AKMIntegration/SovietFab/OpticSteel','AKMIntegration/SovietFab/Optics']
    reg=unreal.AssetRegistryHelpers.get_asset_registry()
    for d in dirs:
        for item in reg.get_assets_by_path('/Game/Weapons/'+d,recursive=True):
            if str(item.asset_class_path.asset_name)!='StaticMesh':continue
            mesh=item.get_asset()
            for slot in mesh.get_editor_property('static_materials'):
                mat=slot.get_editor_property('material_interface')
                if mat:sources[mat.get_path_name()]=mat
    return {path:wet for path,mat in sources.items() if (wet:=wet_material(mat))}

def rain_card(name,kind):
    m=create(name);m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    if LIB.get_material_expressions(m):
        for n in LIB.get_material_expressions(m):
            if isinstance(n,unreal.MaterialExpressionCustom):
                code=n.get_editor_property('code')
                if 'return a*' in code and '1300,2200' not in code:
                    n.set_editor_property('code',code.replace('smoothstep(85,220,Depth)','smoothstep(85,220,Depth)*(1-smoothstep(1300,2200,Depth))'))
        return save(m)
    m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided',True)
    LIB.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    uv=node(m,unreal.MaterialExpressionTextureCoordinate);age=node(m,unreal.MaterialExpressionParticleRelativeTime)
    rnd=node(m,unreal.MaterialExpressionParticleRandom);depth=node(m,unreal.MaterialExpressionPixelDepth)
    if kind=='mist':
        shape='float2 p=(UV-.5)*2;float a=pow(saturate(1-dot(p,p)),3)*(.65+.35*sin(p.x*7+sin(p.y*5)));'
    elif kind=='splash':
        shape='float2 p=(UV-.5)*2;float r=length(p);float ring=exp(-pow((r-lerp(.12,.72,Age))*20,2));float a=ring*(.55+.45*cos(atan2(p.y,p.x)*7+Random*6));'
    else:
        shape='float2 p=(UV-.5)*2;float width=lerp(24,70,Random);float len=lerp(.5,.96,frac(Random*13.7));float a=exp(-p.x*p.x*width)*pow(saturate(1-abs(p.y)/len),1.4);'
    alpha=custom(m,shape+'return a*smoothstep(0,.08,Age)*(1-smoothstep(.7,1,Age))*smoothstep(85,220,Depth)*(1-smoothstep(1300,2200,Depth))*'+('.028' if kind=='mist' else '.25' if kind=='splash' else '.24')+';',dict(UV=uv,Age=age,Random=rnd,Depth=depth),1)
    fade=node(m,unreal.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',20 if kind=='mist' else 3)
    wire(alpha,fade,'Opacity');prop(fade,'OPACITY')
    prop(vector(m,(.60,.63,.66)),'BASE_COLOR')
    prop(constant(m,.3 if kind=='mist' else .08),'ROUGHNESS');prop(constant(m,.5),'SPECULAR')
    if kind!='mist':prop(custom(m,'float2 p=(UV-.5)*2;return normalize(float3(p.x*.85,p.y*.14,1));',dict(UV=uv),3),'NORMAL')
    return save(m)

def ref(s,e,script='',module='',renderer=-1):
    r=unreal.NiagaraExt_StackItemReference()
    for k,v in dict(system=s,emitter_name=e,script_name=script,module_name=module,renderer_index=renderer).items():r.set_editor_property(k,v)
    return r
def set_input(s,e,script,module,p,typ,val):
    assert unreal.RainAssetEditor.set_input(s,e,script,module,p,typ,val),(s.get_name(),p,val,unreal.RainAssetEditor.read_input(s,e,script,module,p))
def systems():
    mats={k:rain_card('M_Natural_'+k,k) for k in ['rain','splash','mist']}
    result={}
    for kind,name in [('rain','RainFine'),('splash','SurfaceSplashes'),('mist','RainMist'),('drip','RoofDrips')]:
        source=unreal.load_asset('/Game/Weather/VFX/NS_FPS_'+name);assert source,name
        s,_=duplicate(source,'NS_Natural_'+name);e='RainSplashes' if kind=='splash' else 'RainDrops'
        data=unreal.NiagaraExt_RendererData()
        data.set_editor_property('property_values',json.dumps({'Material':mats['rain' if kind=='drip' else kind].get_path_name()}))
        API.call_method('SetRendererData',(ref(s,e,renderer=0),data))
        if kind in ['rain','drip']:
            size=(2.1,48) if kind=='rain' else (.85,10)
            set_input(s,e,'ParticleSpawnScript','InitializeParticle','Sprite Size','/Script/CoreUObject.Vector2f','(X=%s,Y=%s)'%size)
        if kind in ['rain','mist']:
            existing=API.call_method('GetUserVariables',(s,)).export_text()
            if 'WeatherWind' not in existing:
                var=unreal.NiagaraExt_UserVariable()
                var.import_text('(Name="User.WeatherWind",Type=(ClassStructOrEnum="/Script/CoreUObject.Vector3f",UnderlyingType=2))')
                API.call_method('AddUserVariables',(s,[var]))
            expr='float3(User.WeatherWind.xy * 1.5,-2100.0)' if kind=='rain' else 'float3(User.WeatherWind.xy * 0.2,-15.0)'
            set_input(s,e,'ParticleUpdateScript','GravityForce','Gravity','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression','(HlslExpression="'+expr+'")')
        assert unreal.RainAssetEditor.compile_rain(s),s.get_path_name()
        save(s);result[kind]=s
        REPORT['systems'].append({'path':s.get_path_name(),'users':API.call_method('GetUserVariables',(s,)).export_text(),'gravity':unreal.RainAssetEditor.read_input(s,e,'ParticleUpdateScript','GravityForce','Gravity')})
    return result

def skies():
    result={};bases={}
    for path in unreal.EditorAssetLibrary.list_assets('/Game/PWL_Light_Manager/Shader',recursive=True):
        source=unreal.load_asset(path)
        if not isinstance(source,unreal.MaterialInterface):continue
        if 'Sky Intensity' not in [str(x) for x in LIB.get_scalar_parameter_names(source)]:continue
        base=source
        while isinstance(base,unreal.MaterialInstance):base=base.get_editor_property('parent')
        if not isinstance(base,unreal.Material) or base.get_editor_property('material_domain')!=unreal.MaterialDomain.MD_SURFACE:continue
        if base.get_path_name() not in bases:
            key=hashlib.sha1(base.get_path_name().encode()).hexdigest()[:8]
            m,fresh=duplicate(base,'M_Atmospheric_'+base.get_name()+'_'+key)
            if fresh:
                p=unreal.MaterialProperty.MP_EMISSIVE_COLOR
                src=LIB.get_material_property_input_node(m,p)
                if not src:continue
                out=LIB.get_material_property_input_node_output_name(m,p)
                code='''float amount=smoothstep(0,.65,Blend);
                float3 fallback=lerp(float3(.10,.135,.17),float3(.022,.045,.075),saturate(-Direction.z));
                fallback*=lerp(.025,.8,Day);
                float3 background=max(Atmosphere.rgb,fallback);
                return lerp(Base,background,amount);'''
                color=custom(m,code,dict(Base=(src,out),Atmosphere=node(m,unreal.MaterialExpressionSkyAtmosphereViewLuminance),Direction=node(m,unreal.MaterialExpressionCameraVectorWS),Blend=scalar(m,'WeatherSkyBlend',0),Day=scalar(m,'WeatherSkyDaylight',1)),3,'Atmospheric storm backdrop')
                prop(color,'EMISSIVE_COLOR');save(m)
            bases[base.get_path_name()]=m
        target=bases[base.get_path_name()]
        if isinstance(source,unreal.MaterialInstanceConstant):
            key=hashlib.sha1(path.encode()).hexdigest()[:8]
            target,_=duplicate(source,'MI_Atmospheric_'+source.get_name()+'_'+key)
            LIB.set_material_instance_parent(target,bases[base.get_path_name()]);save(target)
        result[source.get_path_name()]=target
        REPORT['sky_mapping'][source.get_path_name()]=target.get_path_name()
    return result

screen=lens()
mapping=gun_materials()
sky_mapping=skies()
fx=systems()
asset_class=unreal.load_class(None,'/Script/FPSGAME.WeatherPresentationAssets')
assert asset_class,'Rebuild the FPSGAME editor module before generating assets'
factory=unreal.DataAssetFactory();factory.set_editor_property('data_asset_class',asset_class)
path=DEST+'/DA_WeatherPresentation'
data=unreal.load_asset(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset('DA_WeatherPresentation',DEST,asset_class,factory)
for key,value in dict(screen_material=screen,wet_materials=mapping,sky_materials=sky_mapping,rain=fx['rain'],splashes=fx['splash'],mist=fx['mist'],drips=fx['drip']).items():data.set_editor_property(key,value)
save(data)
(OUT/'assets-built.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
unreal.log('NATURAL_WEATHER_ASSETS_PASS sources='+str(len(mapping)))
