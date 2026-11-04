"""Rebuild the Star Marrow blade fire independently of the HUD and shared fire effects."""
import json
import sys
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent / 'VariationV2'))
import install_variation as v2
from author_flame_armor_v2 import API, LIB, FLOAT, VEC2, VEC3, VEC4, COLOR, ref, put, assignments, setdata, user_parameter
from build_fireball_outer_flame import enable_sprite_usage
from build_fireball_slow_burn import smooth

DEST = v2.DEST
SYSTEM = DEST + '/NS_StarMarrowDenseBladeFire'
BED = DEST + '/M_StarMarrowEdgeBed'
TONGUE = DEST + '/M_StarMarrowLivingTongue'
CELLS = 12  # per cutting edge
REVISION = 'DenseBladeFlowV3.2'


def mask_material(path, description, code):
    mat = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    if mat is None:
        mat = u.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1], DEST, u.Material, u.MaterialFactoryNew())
        mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE)
        mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
        mat.set_editor_property('two_sided', True)
        mat.set_editor_property('disable_depth_test', False)
        enable_sprite_usage(mat)
        node = lambda kind: LIB.create_material_expression(mat, kind)
        uv, color = node(u.MaterialExpressionTextureCoordinate), node(u.MaterialExpressionParticleColor)
        params = node(u.MaterialExpressionDynamicParameter)
        params.set_editor_property('param_names', ['EdgePhase','BurnTime','UnusedZ','UnusedW'])
        shape = node(u.MaterialExpressionCustom)
        shape.set_editor_property('desc', description)
        shape.set_editor_property('output_type', u.CustomMaterialOutputType.CMOT_FLOAT1)
        inputs = []
        for name in ['UV','Phase','TimeS']:
            pin = u.CustomInput(); pin.set_editor_property('input_name', name); inputs.append(pin)
        shape.set_editor_property('inputs', inputs)
        def wire(source, output, dest, pin):
            if not LIB.connect_material_expressions(source, output, dest, pin):
                raise RuntimeError('Cannot wire edge bed ' + pin)
        # Channel zero is available by index even in a headless material graph.
        wire(uv,'',shape,'UV'); wire(params,'',shape,'Phase'); wire(node(u.MaterialExpressionTime),'',shape,'TimeS')
        eye = node(u.MaterialExpressionEyeAdaptationInverse)
        wire(color,'RGB',eye,str(LIB.get_material_expression_input_names(eye)[0]))
        opacity = node(u.MaterialExpressionMultiply)
        wire(color,'A',opacity,'A'); wire(shape,'',opacity,'B')
        LIB.connect_material_property(eye,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
        LIB.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
    else:
        shape = next(n for n in LIB.get_material_expressions(mat) if n.get_editor_property('desc')==description)
    if path == TONGUE:
        # Reuse the project's baked flame, temperature and soot channels for the moving folds.
        pins = list(shape.get_editor_property('inputs'))
        if not any(str(pin.get_editor_property('input_name'))=='Combustion' for pin in pins):
            texture = u.load_asset('/Game/Skills/Fireball/FluidCore20260923/T_FireballCombustionFields')
            if not texture: raise RuntimeError('Missing combustion flipbook')
            atlas = LIB.create_material_expression(mat,u.MaterialExpressionTextureObject)
            atlas.set_editor_property('texture',texture)
            atlas.set_editor_property('sampler_type',u.MaterialSamplerType.SAMPLERTYPE_MASKS)
            pin = u.CustomInput(); pin.set_editor_property('input_name','Combustion')
            shape.set_editor_property('inputs',pins+[pin])
            if not LIB.connect_material_expressions(atlas,'',shape,'Combustion'):raise RuntimeError('Cannot bind charge fire flipbook')
    shape.set_editor_property('code',code)
    errors = LIB.recompile_material(mat)
    if errors: raise RuntimeError(str(errors))
    v2.save(mat)
    return mat


EDGE_MASK = '''
float2 p = UV*2-1;
float travel = Phase + p.y*1.2;
float ripple = sin(travel*1.3-TimeS*2.1) + 0.45*sin(travel*3.2+TimeS*3.6);
float transverse = abs(p.x - ripple*0.09);
float width = 0.69 + ripple*0.12;
float root = 1-smoothstep(0.08,width,transverse);
return root*(1-smoothstep(0.46,0.99,abs(p.y)));
'''

# UV.y = 1 at the attached end. Advection bends and erodes the tip but leaves the root connected.
TONGUE_MASK = '''
struct Eddy {
    float hash(float2 p) {float3 q=frac(float3(p.xyx)*.1031); q+=dot(q,q.yzx+33.33); return frac((q.x+q.y)*q.z);}
    float noise2(float2 p) {float2 i=floor(p),f=frac(p); f=f*f*(3-2*f);
        return lerp(lerp(hash(i),hash(i+float2(1,0)),f.x),lerp(hash(i+float2(0,1)),hash(i+1),f.x),f.y);}
};
Eddy e;
float h=saturate(1-UV.y), x=UV.x*2-1, seed=Phase*37;
float drift=e.noise2(float2(h*2.8-TimeS*(1.9+.6*Phase),seed))-.5;
float fold=e.noise2(float2(h*5.1-TimeS*3.2,seed+7))-.5;
float bend=h*(1.05*drift+.40*fold);
float cycle=frac((TimeS*(18+6*Phase)+Phase*59)/64)*64;
float k=floor(cycle), next=fmod(k+1,64);
float2 sampleUV=clamp(float2(.19+.62*UV.x+drift*h*.13,.15+.70*UV.y),.025,.975);
float3 first=Texture2DSampleLevel(Combustion,CombustionSampler,(float2(fmod(k,8),floor(k/8))+sampleUV)/8,0).rgb;
float3 second=Texture2DSampleLevel(Combustion,CombustionSampler,(float2(fmod(next,8),floor(next/8))+sampleUV)/8,0).rgb;
float3 field=lerp(first,second,frac(cycle));
float heat=smoothstep(.08,.77,.74*field.r+.26*field.g-.09*field.b);
float width=(.50+.15*drift+.17*heat)*pow(saturate(1-h),.73)+.018;
float body=1-smoothstep(width*.50,width,abs(x-bend));
float grain=e.noise2(float2(x*2.6+seed,h*4.4-TimeS*3.6));
float rim=smoothstep(.12,.67,grain+.54*(1-h));
float notch=1-.80*smoothstep(.50,.78,h)*(1-smoothstep(.025,.15,abs(x-bend-.12*fold)));
float lace=smoothstep(-.14,.16,heat+.25*grain+.30-h*.72);
float density=lerp(.20,1.,heat)*lerp(.8,1.,grain);
return body*rim*notch*lace*density*smoothstep(0,.15,h)*(1-smoothstep(.80,1.,h));
'''


def emit(system, name, kind, rate, salt):
    core = kind == 'core'
    free = kind in ('motion','ember')
    h0,h1,h2 = [v2.seed(i,salt) for i in range(3)]
    # Persistent pairs follow opposite cutting edges, while short tongues sample the full span.
    ordinal = '(float(Particles.UniqueID)+.5)'
    cell = f'frac({ordinal}/{float(CELLS)})'
    alternate = f'(frac({ordinal}*.5)<.5?-1.:1.)'
    station = f'(.055+.91*{cell})' if core else '(.055+.91*frac(float(Particles.UniqueID)*.61803399+frac(User.VariationSeed*.013)))'
    edge = f'(frac({ordinal}/{float(2*CELLS)})<.5?-1.:1.)' if core else alternate
    if kind == 'curl':
        # Consecutive siblings rise from one spot and split later in life.
        pair = 'floor(float(Particles.UniqueID)*.5)'
        station = f'(.055+.91*frac({pair}*.61803399+frac(User.VariationSeed*.013)))'
        edge = f'(frac({ordinal}*.25)<.5?-1.:1.)'
    # Star Marrow is widest just beyond the guard, narrows gradually, then tapers to the point.
    half_width = f'((5.48-1.65*{station})*(1-.92*{smooth(".82","1.",station)}))'
    side = f'(User.BladeSide*{edge})'
    radial = f'({side}*({half_width}+.22))'
    anchor = f'(User.WeaponEnd*{station}+{radial})'
    flow = f'lerp(User.BaseFlow,User.TipFlow,{station})'
    clock = 'User.FlameClock'
    phase = f'({station}*13.-{clock}*2.4+User.VariationSeed*.17)'
    gust = f'(.58*sin({phase})+.32*sin({phase}*1.74-{clock}*.83))'
    n = 'Particles.NormalizedAge'
    # Growth and lean vary by position and age. The newborn tongue stays rooted as older tips peel away.
    retained_flow = f'lerp({flow},Particles.Velocity,.65*{n})'
    normal = f'cross(normalize(User.WeaponEnd),{side})'
    direction = f'normalize(float3(0,0,1.)+{side}*(.54+.25*{gust})+{normal}*(.21+.53*{gust})-{retained_flow}*(.00025+.0012*{n}))'
    rise = f'(User.WeaponSize*{n}*(4.+8.*{h0})*(1.+.22*{gust}))'
    drift = f'({side}*{n}*{n}*(1.2+3.*{h1})*sin({phase}+{n}*(2.+2.*{h2})))'
    position = f'({anchor}+{direction}*{rise}+{drift})'
    taper = f'(1.-.62*{smooth(".76","1.",station)})'
    grow = f'(.52+.65*sin({n}*2.7))'
    size = f'float2(12.+5.*{h1},12.+18.*pow({h0},2.))*{taper}*{grow}*User.WeaponSize'
    life = f'(.39+.37*{h1})'
    alpha = f'User.Fade*(.64+.24*{h0})'
    scale = 'lerp(.22,1.,User.Detail)'
    velocity = flow if kind in ('flame','curl') else 'float3(0,0,0)'
    spawn = anchor
    if core:
        position, direction, life = anchor, 'normalize(User.WeaponEnd)', '32.'
        size = f'float2((3.9+1.2*{gust})*{taper},length(User.WeaponEnd)*.91/{float(CELLS)}*1.9)'
        alpha, scale = 'User.Fade*.79', '0.'
    elif kind == 'flame':
        position = anchor
    elif kind == 'curl':
        size = f'float2(12.+6.*{h0},13.+8.*{h1})*{grow}*{taper}*User.WeaponSize'
        position = f'{anchor}+{direction}*{rise}*.48+{drift}*.55+{normal}*{alternate}*{n}*{n}*2.*User.WeaponSize'
        direction = f'normalize({direction}+{side}*{gust}*.36)'
        life, alpha = f'(.44+.40*{h2})', 'User.Fade*.56'
    elif free:
        spawn = f'(lerp(lerp(User.PreviousStart,User.PreviousEnd,{station}),lerp(User.WeaponStartWorld,User.WeaponEndWorld,{station}),{h2})+{radial})'
        position = 'Particles.Position+Particles.Velocity*Engine.DeltaTime'
        velocity = f'({flow}*.065+float3(0,0,12.+10.*{h1})+{side}*(2.+3.*{h0}))'
        direction = 'normalize(Particles.Velocity+float3(0,0,.01))'
        size = f'float2(7.+5.*{h1},14.+12.*{h2})*User.WeaponSize*(1.-.65*{n})'
        life, alpha, scale = f'(.14+.12*{h0})', 'User.Fade*.57', 'User.Detail*User.Detail*User.MotionEnergy'
        if kind == 'ember':
            size = f'float2(.65,1.4)*(.65+{h0})'
            scale = 'User.Detail*User.Detail*(.35+.65*User.MotionEnergy)'
    v2.fire.V = h1
    v2.fire.layer(system,name,'flame' if kind=='motion' else kind,rate,not free,life,spawn,position,size,alpha,axis=direction,velocity=velocity,scale=scale)
    extra = {}
    if core:
        API.call_method('AddModule',(ref(system,name,'EmitterUpdateScript'),u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Count',
            f'(HlslExpression="Engine.Emitter.TotalSpawnedParticles < 1 ? {CELLS*2} : 0")','/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
        put(system,name,'EmitterUpdateScript','SpawnBurst_Instantaneous','Spawn Time','(Value=0)')
        extra['Particles.Color'] = (COLOR,'float4(.022,.16,.85,User.Fade*.64)')
        extra['Particles.DynamicMaterialParameter'] = (VEC4,f'float4({station}*19.+User.VariationSeed*.17,{clock},0,0)')
    elif kind=='flame':
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{'PivotInUVSpace':{'X':.5,'Y':.98}})
        envelope = f'{smooth("0.",".10",n)}*(1.-{smooth(".60","1.",n)})'
        extra['Particles.Color'] = (COLOR,f'float4(.018,.29,1.55,User.Fade*{envelope}*(.78+.19*{h1}))')
        extra['Particles.DynamicMaterialParameter'] = (VEC4,f'float4({h1},0,0,0)')
    elif kind=='motion':
        extra['Particles.DynamicMaterialParameter'] = (VEC4,f'float4(.045+.14*{h0}+(.56+.16*{h1})*{smooth(".25",".97",n)},1,1,1)')
    elif kind == 'curl':
        setdata('SetRendererData',u.NiagaraExt_RendererData,ref(system,name,renderer=0),{
            'SubImageSize':{'X':6,'Y':6},'bSubImageBlend':True,'PivotInUVSpace':{'X':.5,'Y':.66}})
        extra['Particles.SubImageIndex'] = (FLOAT,f'min(35.,{n}*(25.+10.*{h1}))')
        extra['Particles.DynamicMaterialParameter'] = (VEC4,f'float4({h0},.74+.9*{h1}+{n}*.55,0,0)')
    if extra:
        for stage in ['ParticleSpawnScript','ParticleUpdateScript']:
            assignments(system,name,stage,extra)


def run():
    if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before saving charge fire')
    if {SYSTEM,BED,TONGUE}.intersection(p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved dense blade fire assets')
    mat = mask_material(BED,'StarMarrow continuous edge density',EDGE_MASK)
    flame = mask_material(TONGUE,'StarMarrow attached flame silhouette',TONGUE_MASK)
    system = u.load_asset(SYSTEM) if u.EditorAssetLibrary.does_asset_exist(SYSTEM) else u.EditorAssetLibrary.duplicate_asset(v2.SYSTEM,SYSTEM)
    if not system: raise RuntimeError('Star Marrow V2 base system is missing')
    for name in ['BaseFlow','TipFlow','BladeSide']:
        user_parameter(system,name,VEC3)
    layers = [('WeaponFireballCore','core',0,11.),('WeaponFireballTongues','flame',44,23.),
              ('WeaponFireballCurls','curl',16,39.),('MotionFireballFlame','motion',14,53.),('WeaponEmbers','ember',4,79.)]
    old_materials, old_seed = v2.fire.MATERIALS, v2.fire.V
    try:
        v2.fire.MATERIALS = {'core':BED,'flame':TONGUE,'curl':DEST+'/M_StarMarrowBlueRoll','ember':DEST+'/M_StarMarrowBlueEmber'}
        for layer in layers:
            v2.fire.MATERIALS['flame'] = DEST+'/MI_StarMarrowBlueFlame' if layer[1]=='motion' else TONGUE
            emit(system,*layer)
    finally:
        v2.fire.MATERIALS, v2.fire.V = old_materials, old_seed
    if not u.RainAssetEditor.compile_rain(system,True): raise RuntimeError('Dense blade fire Niagara compilation failed')
    u.EditorAssetLibrary.set_metadata_tag(system,'StarMarrow.Revision',REVISION)
    v2.save(system)
    receipt = dict(revision=REVISION,saved=[mat.get_path_name(),flame.get_path_name(),system.get_path_name()],edge_cells=2*CELLS,
                   peak_spawn_per_second=sum(row[2] for row in layers),gameplay_tested=False,rendered=False)
    (OUT/'install-receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
    print('STAR_MARROW_DENSE_FIRE_SAVED',receipt)


if __name__=='__main__': run()
