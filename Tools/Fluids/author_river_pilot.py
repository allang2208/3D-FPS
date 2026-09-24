"""Author the shared full-river material and bounded bullet splash system. No map/PIE."""
import json
from pathlib import Path
import unreal as u

ROOT=Path(u.Paths.project_dir())
OUT=ROOT/'SourceAssets/RiverPilot20260923'
DEST='/Game/Fluids/RiverPilot20260923'
LIB=u.MaterialEditingLibrary
EAL=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
API=u.get_default_object(u.NiagaraToolset_System)
FLOAT='/Script/Niagara.NiagaraFloat'
V2='/Script/CoreUObject.Vector2f'
V3='/Script/CoreUObject.Vector3f'
V4='/Script/CoreUObject.Vector4f'
POSITION='/Script/Niagara.NiagaraPosition'
COLOR='/Script/CoreUObject.LinearColor'
SAVED=[]

def save(obj):
    if isinstance(obj,u.Material):
        errors=LIB.recompile_material(obj)
        if errors:raise RuntimeError(str(errors))
    if isinstance(obj,u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(obj):
        raise RuntimeError('Niagara compile failed '+obj.get_path_name())
    if not u.EditorLoadingAndSavingUtils.save_packages([obj.get_outermost()],False):
        raise RuntimeError('Save failed '+obj.get_path_name())
    SAVED.append(obj.get_path_name());u.log('RIVER_PILOT_SAVED '+obj.get_path_name())

def own(name,source=None):
    path=DEST+'/'+name
    if EAL.does_asset_exist(path):return u.load_asset(path)
    obj=EAL.duplicate_asset(source,path) if source else TOOLS.create_asset(name,DEST,u.Material,u.MaterialFactoryNew())
    if not obj:raise RuntimeError('Cannot create '+path)
    return obj

def node(m,cls):return LIB.create_material_expression(m,cls)
def wire(source,target,pin):
    obj,out=source if isinstance(source,tuple) else (source,'')
    if not LIB.connect_material_expressions(obj,out,target,pin):raise RuntimeError('Cannot connect '+pin)
def prop(m,source,name):
    if not LIB.connect_material_property(source,'',getattr(u.MaterialProperty,'MP_'+name)):raise RuntimeError(name)
def scalar(m,name,value):
    n=node(m,u.MaterialExpressionScalarParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',value);return n
def vector(m,name,value):
    n=node(m,u.MaterialExpressionVectorParameter);n.set_editor_property('parameter_name',name);n.set_editor_property('default_value',u.LinearColor(*value));return n
def custom(m,code,inputs,width=1,description='River pilot'):
    n=node(m,u.MaterialExpressionCustom);n.set_editor_property('code',code)
    n.set_editor_property('description',description)
    n.set_editor_property('output_type',getattr(u.CustomMaterialOutputType,'CMOT_FLOAT'+str(width)))
    pins=[]
    for name in inputs:
        p=u.CustomInput();p.set_editor_property('input_name',name);pins.append(p)
    n.set_editor_property('inputs',pins)
    for name,value in inputs.items():wire(value,n,name)
    return n

def surface():
    from water_wake_authoring import wake_inputs
    source=u.load_asset('/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming').get_editor_property('river_material')
    original=u.load_asset(str(source)) if not isinstance(source,u.MaterialInterface) else source
    if not isinstance(original,u.Material):raise RuntimeError('Expected current river master material, got '+str(source))
    m=own('M_RiverPilot',original.get_path_name())
    # Refresh our custom nodes on reruns, preserving the accepted base river graph.
    if EAL.get_metadata_tag(m,'RiverPilot.Authored'):
        nodes=LIB.get_material_expressions(m)
        flow=next(n for n in nodes if isinstance(n,u.MaterialExpressionVertexColor))
        for n in nodes:
            if not isinstance(n,u.MaterialExpressionCustom):continue
            if n.get_editor_property('description')=='River pilot bullet ripples':
                pins=list(n.get_editor_property('inputs'))
                if not any(str(p.get_editor_property('input_name'))=='Flow' for p in pins):
                    p=u.CustomInput();p.set_editor_property('input_name','Flow');pins.append(p)
                    n.set_editor_property('inputs',pins)
                wire(flow,n,'Flow')
                pins=list(n.get_editor_property('inputs'))
                names={str(p.get_editor_property('input_name')) for p in pins}
                for i in range(8):
                    if 'Meta'+str(i) not in names:
                        p=u.CustomInput();p.set_editor_property('input_name','Meta'+str(i));pins.append(p)
                n.set_editor_property('inputs',pins)
                for i in range(8):
                    parameter=next((p for p in LIB.get_material_expressions(m) if isinstance(p,u.MaterialExpressionVectorParameter)
                                    and str(p.get_editor_property('parameter_name'))=='WaterHitMeta'+str(i)),None)
                    if not parameter:parameter=vector(m,'WaterHitMeta'+str(i),(0,1,1,0))
                    wire((parameter,'RGBA'),n,'Meta'+str(i))
                wake_inputs(m,n)
                n.set_editor_property('code',(OUT/'RippleField.hlsl').read_text())
            elif 'HalfLength-1200' in n.get_editor_property('code'):
                n.set_editor_property('code','return 1.0; // Full river: pilot length restriction retired.')
            elif 'FoamTextureSampler' in n.get_editor_property('code'):
                n.set_editor_property('code',(OUT/'ShoreFoam.hlsl').read_text())
        EAL.set_metadata_tag(m,'RiverPilot.Polish','5-all-water-secondary')
        save(m)
        return m,original.get_path_name()
    baseline={}
    for name in ['NORMAL','BASE_COLOR','OPACITY','ROUGHNESS']:
        p=getattr(u.MaterialProperty,'MP_'+name)
        baseline[name]=(LIB.get_material_property_input_node(m,p),LIB.get_material_property_input_node_output_name(m,p))
        if baseline[name][0] is None:raise RuntimeError('Missing source river output '+name)
    p=node(m,u.MaterialExpressionWorldPosition);t=node(m,u.MaterialExpressionTime)
    uv=node(m,u.MaterialExpressionTextureCoordinate);flow=node(m,u.MaterialExpressionVertexColor)
    scene=node(m,u.MaterialExpressionDepthFade);scene.set_editor_property('fade_distance_default',100.)
    depth=custom(m,'return min(saturate(A),saturate(B))*100;',{'A':(flow,'A'),'B':scene})
    pilot=custom(m,'return 1.0; // Full river',
        {'UV':uv,'Center':scalar(m,'PilotCenterAlong',0),'HalfLength':scalar(m,'PilotHalfLength',6000)})
    ripples=custom(m,(OUT/'RippleField.hlsl').read_text(),
        {'Pilot':pilot,'Position':p,'Clock':t,'Depth':depth,'Flow':flow,
         **{'Hit'+str(i):(vector(m,'WaterHit'+str(i),(0,0,-10000,0)),'RGBA') for i in range(8)},
         **{'Meta'+str(i):(vector(m,'WaterHitMeta'+str(i),(0,1,1,0)),'RGBA') for i in range(8)}},3,'River pilot bullet ripples')
    wake_inputs(m,ripples)
    normal=custom(m,(OUT/'SurfaceNormal.hlsl').read_text(),
        {'Pilot':pilot,'Baseline':baseline['NORMAL'],'Position':p,'Flow':flow,'Clock':t,'Depth':depth,'Ripple':ripples},3)
    prop(m,normal,'NORMAL')
    foamtex=node(m,u.MaterialExpressionTextureObject)
    foamtex.set_editor_property('texture',u.load_asset('/Game/WaterMaterials/Textures/T_Ocean_Foam'))
    foam=custom(m,(OUT/'ShoreFoam.hlsl').read_text(),
        {'Position':p,'Flow':flow,'Clock':t,'Depth':depth,'Ripple':ripples,'FoamTexture':foamtex})
    fresnel=node(m,u.MaterialExpressionFresnel)
    fresnel.set_editor_property('exponent',5.);fresnel.set_editor_property('base_reflect_fraction',.02)
    inputs={'Weight':pilot,'Depth':depth,'Foam':foam,'Fresnel':fresnel}
    prop(m,custom(m,'float a=1-exp(-Depth*.022);float3 c=lerp(float3(.065,.14,.105),float3(.012,.06,.065),a);return lerp(Base,lerp(c,float3(.55,.63,.60),Foam),Weight);',
        {'Base':baseline['BASE_COLOR'],**inputs},3),'BASE_COLOR')
    prop(m,custom(m,'float o=(.055+.48*(1-exp(-Depth*.022))+.20*Fresnel+Foam*.42)*smoothstep(0,5,Depth);return lerp(Base,saturate(o),Weight);',
        {'Base':baseline['OPACITY'],**inputs}),'OPACITY')
    prop(m,custom(m,'return lerp(Base,lerp(.075,.36,Foam),Weight);',{'Base':baseline['ROUGHNESS'],**inputs}),'ROUGHNESS')
    EAL.set_metadata_tag(m,'RiverPilot.Authored','20260923')
    EAL.set_metadata_tag(m,'RiverPilot.Polish','5-all-water-secondary')
    save(m);return m,original.get_path_name()

def splash_material(name,sheet):
    m=own(name);LIB.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('two_sided',True)
    m.set_editor_property('translucency_lighting_mode',u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    LIB.set_base_material_usage(m,u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES,True)
    uv=node(m,u.MaterialExpressionTextureCoordinate);age=node(m,u.MaterialExpressionParticleRelativeTime)
    color=node(m,u.MaterialExpressionParticleColor)
    dynamic=node(m,u.MaterialExpressionDynamicParameter)
    dynamic.set_editor_property('param_names',['Variant','UnusedY','UnusedZ','UnusedW'])
    code=(OUT/('CrownShape.hlsl' if sheet else 'DropShape.hlsl')).read_text()
    shape=custom(m,code,{'UV':uv,'Age':age,'Alpha':(color,'A'),'Variant':dynamic})
    fade=node(m,u.MaterialExpressionDepthFade);fade.set_editor_property('fade_distance_default',2.)
    wire(shape,fade,'Opacity');prop(m,fade,'OPACITY')
    rgb=custom(m,'return Color;',{'Color':(color,'RGB')},3)
    prop(m,rgb,'BASE_COLOR');prop(m,scalar(m,'WaterRoughness',.12 if sheet else .08),'ROUGHNESS')
    prop(m,scalar(m,'WaterSpecular',.65 if sheet else .70),'SPECULAR')
    normal=('float phase=Variant*6.2831853;return normalize(float3(sin(UV.x*35+phase)*.22,cos(UV.y*12-Age*4+phase)*.12,1));') if sheet else (
        'float2 p=(UV-.5)*2;return normalize(float3(p*float2(.68,.40),sqrt(saturate(1-dot(p,p)*.65))+.35));')
    prop(m,custom(m,normal,{'UV':uv,'Age':age,'Variant':dynamic},3),'NORMAL')
    prop(m,custom(m,'return Color*.075;',{'Color':(color,'RGB')},3),'EMISSIVE_COLOR')
    save(m);return m

def ref(s,e,script='',module='',renderer=-1):
    r=u.NiagaraExt_StackItemReference()
    for k,v in dict(system=s,emitter_name=e,script_name=script,module_name=module,renderer_index=renderer).items():r.set_editor_property(k,v)
    return r
def data(method,typ,r,values):
    d=typ();d.set_editor_property('property_values',json.dumps(values));API.call_method(method,(r,d))
def put(s,e,script,module,name,value,typ=FLOAT):
    if not u.RainAssetEditor.set_input(s,e,script,module,name,typ,value):raise RuntimeError(e+'/'+name)
def assign(s,e,script,values):
    entries=[]
    for name,(typ,code) in values.items():
        p=u.NiagaraExt_SetParameterEntry();p.import_text('(Variable=(Name="'+name+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2)))');entries.append(p)
    mod=str(API.call_method('AddSetParametersModule',(ref(s,e,script),entries)).get_editor_property('module_name'))
    for name,(typ,code) in values.items():put(s,e,script,mod,name,'(HlslExpression="'+code+'")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')

def system(drop,sheet):
    s=own('NS_RiverBulletSplash','/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeShotV15')
    for e in API.call_method('GetSystemSummary',(s,)).get_editor_property('emitters'):
        API.call_method('RemoveEmitter',(ref(s,str(e.get_editor_property('emitter_name'))),))
    user_variables=API.call_method('GetUserVariables',(s,)).export_text()
    for name,typ in [('Strength',FLOAT),('Flow',V3)]:
        if 'Name="User.'+name+'"' in user_variables:continue
        v=u.NiagaraExt_UserVariable();v.import_text('(Name="User.'+name+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2))')
        API.call_method('AddUserVariables',(s,[v]))
    enum_source=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    torch=u.load_asset('/Game/Props/RomanColumn20260915/NS_TorchFlame')
    binding=json.loads(API.call_method('GetRendererData',(ref(torch,'NE_Flame_01',renderer=0),)).get_editor_property('property_values'))['SpriteAlignmentBinding']
    for e,mat,count,is_sheet in [('WaterDrops',drop,14,False),('WaterCrown',sheet,3,True)]:
        API.call_method('AddEmitter',(s,u.load_asset('/Game/Vefects/Free_Fire/Shared/Particles/NE_FireFlame'),e))
        top=API.call_method('GetEmitterTopology',(ref(s,e),))
        for script,propname,keep in [('EmitterUpdateScript','emitter_update_script',['EmitterState']),
            ('ParticleSpawnScript','particle_spawn_script',['InitializeParticle']),('ParticleUpdateScript','particle_update_script',['ParticleState'])]:
            for m in top.get_editor_property(propname).get_editor_property('modules'):
                name=str(m.get_editor_property('module_name'))
                if name not in keep:API.call_method('RemoveModule',(ref(s,e,script,name),))
        data('SetEmitterData',u.NiagaraExt_EmitterData,ref(s,e),{'bLocalSpace':False,'SimTarget':'CPUSim','bInterpolatedSpawning':False})
        for key,old,new in [('Life Cycle Mode','System','Self'),('Loop Behavior','Infinite','Once')]:
            value=u.RainAssetEditor.read_input(enum_source,'Explosion','EmitterUpdateScript','EmitterState',key)
            put(s,e,'EmitterUpdateScript','EmitterState',key,value.replace('NewEnumerator0','NewEnumerator1').replace('"'+old+'"','"'+new+'"'),'/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        put(s,e,'EmitterUpdateScript','EmitterState','Loop Duration','(Value=0.1)')
        API.call_method('AddModule',(ref(s,e,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        put(s,e,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count','(Value='+str(count)+')','/Script/Niagara.NiagaraInt32')
        put(s,e,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
        phase='frac(dot(Engine.Owner.Position.xy,float2(.013,.017)))'
        seed='frac(float(Particles.UniqueID)*.61803399+'+phase+')'
        height_seed='frac(float(Particles.UniqueID)*.41421356+'+phase+'*.731)'
        theta='(float(Particles.UniqueID)*2.094395+'+phase+'*6.2831853)' if is_sheet else '('+seed+'*6.2831853)'
        # Incoming bullet Z is downward; it must not cancel the upward splash.
        # Bound presentation scale independently of the gameplay impact strength.
        power='clamp(User.Strength,.85,1.25)'
        vertical='(170+35*'+height_seed+')' if is_sheet else '(225+105*'+height_seed+')'
        radial='(55+25*'+seed+')' if is_sheet else '(90+100*'+seed+')'
        velocity='float3(cos('+theta+')*'+radial+',sin('+theta+')*'+radial+','+vertical+')*'+power+'+float3(User.Flow.xy,0)'
        origin='Engine.Owner.Position+float3(cos('+theta+')*5,sin('+theta+')*5,0)' if is_sheet else 'Engine.Owner.Position'
        size='float2(28+Particles.Age*100,40+Particles.Age*85)*(.9+.2*'+seed+')*'+power if is_sheet else (
            'float2(2.6,3.8+min(length(Particles.SplashVelocity+float3(0,0,-980)*Particles.Age)*.009,3.5))*(.8+.5*'+seed+')*'+power)
        birth_size='float2(28,40)*(.9+.2*'+seed+')*'+power if is_sheet else 'float2(2.6,6.5)*(.8+.5*'+seed+')*'+power
        assign(s,e,'ParticleSpawnScript',{
            'Particles.SplashOrigin':(POSITION,origin),
            'Particles.SplashVelocity':(V3,velocity),
            'Particles.Lifetime':(FLOAT,'2*'+vertical+'*'+power+'/980'),
            'Particles.DynamicMaterialParameter':(V4,'float4('+seed+',0,0,0)'),
            'Particles.SpriteSize':(V2,birth_size),'Particles.SpriteAlignment':(V3,'float3(0,0,1)'),
            'Particles.SpriteRotation':(FLOAT,'0'),'Particles.SpriteUVScale':(V2,'float2(1,1)'),
            'Particles.SubImageIndex':(FLOAT,'0'),
            'Particles.Color':(COLOR,'float4(.84,.90,.94,'+('.88' if is_sheet else '.96')+')'),
            'Particles.Position':(POSITION,origin)})
        fade='saturate((Particles.NormalizedAge-.60)/.40)' if is_sheet else 'saturate((Particles.NormalizedAge-.78)/.22)'
        fade='(1-('+fade+')*('+fade+')*(3-2*('+fade+')))'
        assign(s,e,'ParticleUpdateScript',{
            'Particles.Position':(POSITION,'Particles.SplashOrigin+Particles.SplashVelocity*Particles.Age+float3(0,0,-490)*Particles.Age*Particles.Age'),
            'Particles.Velocity':(V3,'Particles.SplashVelocity+float3(0,0,-980)*Particles.Age'),
            'Particles.SpriteAlignment':(V3,'float3(0,0,1)' if is_sheet else 'normalize(Particles.Velocity+float3(.001,0,0))'),
            'Particles.SpriteRotation':(FLOAT,'0'),'Particles.SpriteUVScale':(V2,'float2(1,1)'),
            'Particles.SubImageIndex':(FLOAT,'0'),'Particles.SpriteSize':(V2,size),
            'Particles.Color':(COLOR,'float4(.84,.90,.94,'+('.88' if is_sheet else '.96')+'*'+fade+')')})
        data('SetRendererData',u.NiagaraExt_RendererData,ref(s,e,renderer=0),{
            'Material':mat.get_path_name(),'MaterialUserParamBinding':{'Parameter':{'Name':'None'}},
            'Alignment':'CustomAlignment','FacingMode':'FaceCamera','SpriteAlignmentBinding':binding,
            'SubImageSize':{'X':1,'Y':1},'bSubImageBlend':False,'PivotInUVSpace':{'X':.5,'Y':.82 if is_sheet else .5},
            'bCastShadows':False,'bUseMaterialCutoutTexture':False,'CutoutTexture':None})
    EAL.set_metadata_tag(s,'RiverPilot.Polish','3')
    save(s)

def main():
    OUT.mkdir(parents=True,exist_ok=True);EAL.make_directory(DEST)
    splash_only=bool(globals().get('RIVER_SPLASH_ONLY',False))
    if splash_only:
        source=json.loads((OUT/'assets.json').read_text(encoding='utf-8'))['river_source']
    else:
        m,source=surface()
    # The current authoring entry must not restore the old procedural fan mask.
    import sys
    sys.path.insert(0,str(ROOT/'Tools/Fluids'))
    import author_river_splash_natural
    river_saved=list(SAVED)
    author_river_splash_natural.author()
    (OUT/'assets.json').write_text(json.dumps({'saved':list(dict.fromkeys(river_saved+author_river_splash_natural.b.SAVED)),'river_source':source,
        'pilot_length_m':120,'particles_per_hit':13,'ripple_max_seconds':2.2,'revision':'ripple-polish2_splash-natural4-emptyframefix',
        'splash_only':splash_only,
        'runtime_tested':False,'visual_tested':False},indent=2),encoding='utf-8')
    u.log('RIVER_PILOT_AUTHORING_COMPLETE')

if __name__=='__main__':
    main()
