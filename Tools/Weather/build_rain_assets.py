"""Owned weather assets only. Procedural, texture-free rain/surface materials; no downloads.
Run in an isolated UE editor commandlet after the baseline capture.
"""
import json
from pathlib import Path
import unreal
OUT=Path(unreal.Paths.project_saved_dir())/'RainUpgrade'
LIB=unreal.MaterialEditingLibrary
TOOLS=unreal.AssetToolsHelpers.get_asset_tools()
API=unreal.get_default_object(unreal.NiagaraToolset_System)
DEST='/Game/Weather/Materials'
report=[]
def node(m,cls): return LIB.create_material_expression(m,cls)
def scalar(m,name,value):
    n=node(m,unreal.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def vector(m,name,value):
    n=node(m,unreal.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',unreal.LinearColor(*value));return n
def wire(a,b,socket): assert LIB.connect_material_expressions(a,'',b,socket)
def prop(a,p): assert LIB.connect_material_property(a,'',getattr(unreal.MaterialProperty,'MP_'+p))
def custom(m,code,inputs,kind):
    n=node(m,unreal.MaterialExpressionCustom);n.set_editor_property('code',code);n.set_editor_property('output_type',getattr(unreal.CustomMaterialOutputType,'CMOT_FLOAT'+str(kind)))
    ins=[]
    for name in inputs:
        i=unreal.CustomInput();i.set_editor_property('input_name',name);ins.append(i)
    n.set_editor_property('inputs',ins)
    for name,src in inputs.items():wire(src,n,name)
    return n
def create(name):
    m=unreal.load_asset(DEST+'/'+name)
    if not m:m=TOOLS.create_asset(name,DEST,unreal.Material,unreal.MaterialFactoryNew())
    else: LIB.delete_all_material_expressions(m)
    return m
def save(m):
    LIB.recompile_material(m)
    assert unreal.EditorAssetLibrary.save_loaded_asset(m,False)
    report.append(m.get_path_name())
def card(name,mist=False,splash=False):
    m=create(name);m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided',True);m.set_editor_property('disable_depth_test',False)
    LIB.set_material_usage(m,unreal.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    uv=node(m,unreal.MaterialExpressionTextureCoordinate)
    depth=node(m,unreal.MaterialExpressionPixelDepth)
    age=node(m,unreal.MaterialExpressionParticleRelativeTime)
    shape='float2 p=(UV-.5)*2; float a=exp(-p.x*p.x*20)*pow(saturate(1-abs(p.y)),1.5);'
    if mist:shape='float2 p=(UV-.5)*2;float a=pow(saturate(1-dot(p,p)),3)*(0.65+0.35*sin(p.x*7+sin(p.y*5)));'
    if splash:shape='float2 p=(UV-.5)*2;float a=pow(saturate(1-dot(p,p)),2);'
    code=shape+'return a*smoothstep(0,0.10,Age)*(1-smoothstep(.65,1,Age))*smoothstep(60,160,Depth)*'+('.055' if mist else '.46' if splash else '.38')+';'
    alpha=custom(m,code,dict(UV=uv,Depth=depth,Age=age),1)
    fade=node(m,unreal.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',18 if mist else 2);wire(alpha,fade,'Opacity');prop(fade,'OPACITY')
    color=vector(m,'Tint',(.38,.40,.42,1) if mist else (.65,.68,.70,1));prop(color,'BASE_COLOR')
    prop(scalar(m,'Roughness',.35 if mist else .12),'ROUGHNESS');prop(scalar(m,'Specular',.5),'SPECULAR')
    save(m);return m

if not all(unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+n) for n in ['M_RainStreak','M_RainDroplet','M_RainMist','M_RainWetSurface']):
    rainmat=card('M_RainStreak')
    splashmat=card('M_RainDroplet',splash=True)
    mistmat=card('M_RainMist',mist=True)
    m=create('M_RainWetSurface');m.set_editor_property('material_domain',unreal.MaterialDomain.MD_DEFERRED_DECAL)
    m.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    uv=node(m,unreal.MaterialExpressionTextureCoordinate);wp=node(m,unreal.MaterialExpressionWorldPosition);time=node(m,unreal.MaterialExpressionTime)
    wet=scalar(m,'Wetness',0);rain=scalar(m,'Rain',0);step=vector(m,'StepPosition',(0,0,0,0));steptime=scalar(m,'StepTime',-100)
    code='''
    float2 p=World.xy/180;
    float noise=.5+.22*sin(p.x*1.7+sin(p.y*1.3))+.18*cos(p.y*2.1-p.x*.7);
    float puddle=smoothstep(.57,.78,noise)*smoothstep(.18,.8,Wet);
    float2 q=World.xy/48; float2 cell=floor(q);float hash=frac(sin(dot(cell,float2(127.1,311.7)))*43758.5453);
    float phase=frac(Time*1.6+hash);float2 d=frac(q)-float2(.25+.5*hash,.25+.5*frac(hash*9.3));
    float r=length(d);float ring=exp(-abs(r-phase*.68)*65)*(1-phase)*Rain*puddle;
    float age=Time-StepTime;float2 sd=(World.xy-Step.xy)/100;float sr=length(sd);
    float foot=exp(-abs(sr-age*1.6)*22)*saturate(1-age/1.4)*step(0,age)*puddle;
    float edge=smoothstep(0,.12,UV.x)*smoothstep(0,.12,UV.y)*smoothstep(0,.12,1-UV.x)*smoothstep(0,.12,1-UV.y);
    float2 normal=(normalize(d+0.0001)*ring*.12+normalize(sd+0.0001)*foot*.16);
    return float4(normal,edge*Wet*(.14+puddle*.58),lerp(.43,.09,puddle));
    '''
    data=custom(m,code,dict(UV=uv,World=wp,Time=time,Wet=wet,Rain=rain,Step=step,StepTime=steptime),4)
    prop(custom(m,'return Data.b;',dict(Data=data),1),'OPACITY')
    prop(custom(m,'return Data.a;',dict(Data=data),1),'ROUGHNESS')
    prop(custom(m,'return normalize(float3(Data.rg,1));',dict(Data=data),3),'NORMAL')
    prop(vector(m,'WetTint',(.065,.075,.078,1)),'BASE_COLOR');prop(scalar(m,'Specular',.5),'SPECULAR');save(m)


def ref(system,emitter,script='',module='',inputs=(),renderer=-1):
    r=unreal.NiagaraExt_StackItemReference()
    for k,v in dict(system=system,emitter_name=emitter,script_name=script,module_name=module,input_name_stack=list(inputs),renderer_index=renderer).items():r.set_editor_property(k,v)
    return r
def setvalue(r,typepath,text):
    assert unreal.RainAssetEditor.set_input(r.get_editor_property('system'),str(r.get_editor_property('emitter_name')),str(r.get_editor_property('script_name')),str(r.get_editor_property('module_name')),str(r.get_editor_property('input_name_stack')[0]),typepath,text),(r.export_text(),text)
def setfloat(s,e,sc,mod,p,v):setvalue(ref(s,e,sc,mod,[p]),'/Script/Niagara.NiagaraFloat',f'(Value={v})')
def setvec(s,e,sc,mod,p,v):setvalue(ref(s,e,sc,mod,[p]),'/Script/CoreUObject.Vector3f','(X=%s,Y=%s,Z=%s)'%v)
def setdata(method,typ,r,d):
    v=typ();v.set_editor_property('property_values',json.dumps(d));API.call_method(method,(r,v))
def configure(s,e,kind):
    # Template creation leaves a second, uncontrolled stateless Fountain emitter.
    # Remove it completely; otherwise every rain/splash pool produces blue fountain blobs.
    summary=API.call_method('GetSystemSummary',(s,)).export_text()
    if 'EmitterName="Fountain"' in summary:API.call_method('RemoveEmitter',(ref(s,'Fountain'),))
    summary=API.call_method('GetSystemSummary',(s,)).export_text()
    assert summary.count('EmitterName=')==1 and 'EmitterName="'+e+'"' in summary,summary
    # Detach world particles from the camera. Kill particles on collision instead of sliding blue cards.
    setdata('SetEmitterData',unreal.NiagaraExt_EmitterData,ref(s,e),{'bLocalSpace':False,'SimTarget':'GPUComputeSim','bDeterminism':True})
    matname={'rain':'M_RainStreak','drip':'M_RainStreak','splash':'M_RainDroplet','mist':'M_RainMist'}[kind]
    renderer={'Material':'/Game/Weather/Materials/'+matname+'.'+matname,'Alignment':'VelocityAligned' if kind in ['rain','drip'] else 'Unaligned','FacingMode':'FaceCamera','bCastShadows':False}
    setdata('SetRendererData',unreal.NiagaraExt_RendererData,ref(s,e,renderer=0),renderer)
    topology=API.call_method('GetEmitterTopology',(ref(s,e),)).export_text()
    for mod in (['WindForce','AerodynamicDrag','InitialMeshOrientation','AlignSpriteToMeshOrientation','AlignParticlesWithCollisionPlane'] if kind!='splash' else []):
        sc='ParticleSpawnScript' if mod=='InitialMeshOrientation' else 'ParticleUpdateScript'
        if 'ModuleName="'+mod+'"' in topology or 'ModuleName='+mod+',' in topology:API.call_method('RemoveModule',(ref(s,e,sc,mod),))
    setvalue(ref(s,e,'ParticleSpawnScript','InitializeParticle',['Color']),'/Script/CoreUObject.LinearColor','(R=1,G=1,B=1,A=1)')
    lifetime=(.18,.32) if kind=='splash' else (2.8,3.3) if kind=='mist' else (1.4,1.8)
    for p,v in zip(['Lifetime Min','Lifetime Max'],lifetime):setfloat(s,e,'ParticleSpawnScript','InitializeParticle',p,v)
    size={'rain':(3.0,65),'drip':(1.2,14),'mist':(320,190),'splash':(.8,2.2)}[kind]
    if kind=='splash':
        for p,v in zip(['Uniform Sprite Size Min','Uniform Sprite Size Max'],size):setfloat(s,e,'ParticleSpawnScript','InitializeParticle',p,v)
    else:setvalue(ref(s,e,'ParticleSpawnScript','InitializeParticle',['Sprite Size']),'/Script/CoreUObject.Vector2f',f'(X={size[0]},Y={size[1]})')
    setvec(s,e,'ParticleSpawnScript','ShapeLocation','Box Size',{'rain':(2200,2200,300),'mist':(4500,4500,900),'drip':(18,18,5),'splash':(210,210,4)}[kind])
    setvec(s,e,'ParticleUpdateScript','GravityForce','Gravity', (65,20,-2100) if kind=='rain' else (0,0,-980) if kind in ['splash','drip'] else (15,8,-15))
    API.call_method('SetModuleEnabled',(ref(s,e,'ParticleUpdateScript','ScaleSpriteSize'),False)) if kind!='splash' else None
    if kind=='splash':setfloat(s,e,'ParticleSpawnScript','AddVelocity','Velocity Speed',65)
    if kind!='splash':
        API.call_method('SetModuleEnabled',(ref(s,e,'ParticleUpdateScript','Collision'),kind!='mist'))
        if kind!='mist':
            # Spawn volume is above the view: offscreen newborns must survive until falling into view.
            for p,v in [('Kill Offscreen Particles',0),('Kill Occluded Particles',-1),('KillOnCollision',-1)]:
                setvalue(ref(s,e,'ParticleUpdateScript','Collision',[p]),'/Script/Niagara.NiagaraBool',f'(Value={v})')
            setfloat(s,e,'ParticleUpdateScript','Collision','Particle Radius Scale',.02)
    assert unreal.RainAssetEditor.compile_rain(s),s.get_path_name()
    assert unreal.EditorAssetLibrary.save_loaded_asset(s,False)
    report.append(s.get_path_name())

# These four shipped systems contain the emitter graphs and user bindings.
# Never recreate or load the retired blue-card systems.
for name in ['NS_FPS_RainFine','NS_FPS_SurfaceSplashes','NS_FPS_RainMist','NS_FPS_RoofDrips']:
    assert unreal.EditorAssetLibrary.does_asset_exist('/Game/Weather/VFX/'+name),'Restore shipped asset '+name
rainasset=unreal.load_asset('/Game/Weather/VFX/NS_FPS_RainFine')
configure(rainasset,'RainDrops','rain')
configure(unreal.load_asset('/Game/Weather/VFX/NS_FPS_SurfaceSplashes'),'RainSplashes','splash')
configure(unreal.load_asset('/Game/Weather/VFX/NS_FPS_RainMist'),'RainDrops','mist')
configure(unreal.load_asset('/Game/Weather/VFX/NS_FPS_RoofDrips'),'RainDrops','drip')
(OUT/'assets-created.json').write_text(json.dumps(report,indent=2))
import runpy
runpy.run_path(str(Path(__file__).with_name('validate_rain_assets.py')))
unreal.log('RAIN_ASSETS_BUILD_PASS')
