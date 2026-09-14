"""Author project-owned instanced impact materials and short impact sounds.

Run in UE Python commandlet with D3D12 material compilation. This creates assets,
not a game preview or test. No external downloads or source pack mutations.
"""
import array
import math
from pathlib import Path
import random
import wave
import unreal

ROOT = Path(unreal.Paths.project_dir())
SOURCE = ROOT / 'SourceAssets/SurfaceImpacts20260914'
DEST = '/Game/Weapons/GunplayFX/Impacts'
LIB = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
SOURCE.mkdir(parents=True, exist_ok=True)


def node(mat, cls, **props):
    result = LIB.create_material_expression(mat, cls)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result


def wire(src, dst, pin, output=''):
    if isinstance(pin, int):
        pin = str(LIB.get_material_expression_input_names(dst)[pin])
    if not LIB.connect_material_expressions(src, output, dst, pin):
        raise RuntimeError('Material connection failed: ' + pin)


def output(src, prop, pin=''):
    if not LIB.connect_material_property(src, pin, prop):
        raise RuntimeError('Material output connection failed: ' + str(prop))


def constant(mat, value):
    return node(mat, unreal.MaterialExpressionConstant, r=value)


def multiply(mat, a, b):
    result = node(mat, unreal.MaterialExpressionMultiply)
    wire(a, result, 'A'); wire(b, result, 'B')
    return result


def custom(mat, code, inputs):
    result = node(mat, unreal.MaterialExpressionCustom, code=code,
                  output_type=unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    pins = []
    for name in inputs:
        pin = unreal.CustomInput(); pin.set_editor_property('input_name', name); pins.append(pin)
    result.set_editor_property('inputs', pins)
    for name, src in inputs.items():
        wire(src, result, name)
    return result


def material(name):
    existing = unreal.load_asset(DEST + '/' + name)
    if existing:
        return existing, False
    return TOOLS.create_asset(name, DEST, unreal.Material, unreal.MaterialFactoryNew()), True


def save(asset):
    if isinstance(asset, unreal.Material):
        errors = LIB.recompile_material(asset)
        if errors:
            raise RuntimeError('\n'.join(errors))
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, False):
        raise RuntimeError('Could not save ' + asset.get_path_name())
    unreal.log('SURFACE_IMPACT_ASSET_SAVED ' + asset.get_path_name())


def instance_data(mat):
    rgb = node(mat, unreal.MaterialExpressionPerInstanceCustomData3Vector, data_index=0,
               const_default_value=unreal.LinearColor(.5,.5,.5,1))
    alpha = node(mat, unreal.MaterialExpressionPerInstanceCustomData, data_index=3, const_default_value=1.)
    # Per-instance values are vertex inputs; interpolate explicitly for pixel use.
    color_interp = node(mat, unreal.MaterialExpressionVertexInterpolator)
    alpha_interp = node(mat, unreal.MaterialExpressionVertexInterpolator)
    wire(rgb, color_interp, 0); wire(alpha, alpha_interp, 0)
    return color_interp, alpha_interp


for kind in ('Spark', 'Dust', 'Chip'):
    mat, fresh = material('M_Impact' + kind + 'V1')
    if not fresh:
        continue
    mat.set_editor_property('two_sided', kind != 'Chip')
    mat.set_editor_property('blend_mode', unreal.BlendMode.BLEND_ADDITIVE if kind == 'Spark' else
                            unreal.BlendMode.BLEND_TRANSLUCENT if kind == 'Dust' else unreal.BlendMode.BLEND_MASKED)
    mat.set_editor_property('shading_model', unreal.MaterialShadingModel.MSM_UNLIT if kind == 'Spark' else unreal.MaterialShadingModel.MSM_DEFAULT_LIT)
    LIB.set_base_material_usage(mat, unreal.MaterialUsage.MATUSAGE_INSTANCED_STATIC_MESHES, True)
    color, alpha = instance_data(mat)
    if kind == 'Chip':
        output(color, unreal.MaterialProperty.MP_BASE_COLOR)
        output(constant(mat,.78), unreal.MaterialProperty.MP_ROUGHNESS)
        dither = node(mat, unreal.MaterialExpressionMaterialFunctionCall)
        dither.set_editor_property('material_function',unreal.load_asset('/Engine/Functions/Engine_MaterialFunctions02/Utility/DitherTemporalAA'))
        wire(alpha,dither,0)
        output(dither,unreal.MaterialProperty.MP_OPACITY_MASK)
    else:
        uv = node(mat, unreal.MaterialExpressionTextureCoordinate)
        code = ('float2 p=(UV-.5)*2; return pow(saturate(1-dot(p,p)),2);' if kind == 'Spark' else
                'float2 p=(UV-.5)*2; float n=sin(p.x*7+sin(p.y*5))*cos(p.y*6); '
                'float r=length(p)+n*.055; return pow(saturate(1-r),1.4)*(.85+.15*n);')
        (SOURCE / (kind + 'Mask.hlsl')).write_text(code+'\n', encoding='utf-8')
        mask=custom(mat,code,{'UV':uv})
        fade=node(mat,unreal.MaterialExpressionDepthFade,fade_distance_default=.6 if kind=='Spark' else 2.)
        wire(multiply(mat,mask,alpha),fade,'Opacity')
        output(fade,unreal.MaterialProperty.MP_OPACITY)
        if kind=='Spark':
            inverse=node(mat,unreal.MaterialExpressionEyeAdaptationInverse)
            output(multiply(mat,multiply(mat,color,constant(mat,7.)),inverse),unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        else:
            output(color,unreal.MaterialProperty.MP_BASE_COLOR)
            output(multiply(mat,color,constant(mat,.025)),unreal.MaterialProperty.MP_EMISSIVE_COLOR)
            output(constant(mat,.95),unreal.MaterialProperty.MP_ROUGHNESS)
    save(mat)

mark, fresh = material('M_ImpactMarkV1')
if fresh:
    # Set a legal decal blend mode before changing domains; setting the domain
    # first launches an intermediate compile with the default opaque blend.
    mark.set_editor_property('blend_mode',unreal.BlendMode.BLEND_TRANSLUCENT)
    mark.set_editor_property('material_domain',unreal.MaterialDomain.MD_DEFERRED_DECAL)
    uv=node(mark,unreal.MaterialExpressionTextureCoordinate)
    code=('float2 p=(UV-.5)*2; float a=atan2(p.y,p.x); '
          'float r=length(p)/(1+.08*sin(a*7)+.045*cos(a*11)); '
          'float edge=1-smoothstep(.60,.94,r); '
          'return edge*(.70+.30*(1-smoothstep(.15,.6,r)));')
    (SOURCE/'ImpactMarkMask.hlsl').write_text(code+'\n',encoding='utf-8')
    mask=custom(mark,code,{'UV':uv})
    life=node(mark,unreal.MaterialExpressionDecalLifetimeOpacity)
    opacity=node(mark,unreal.MaterialExpressionScalarParameter,parameter_name='MarkOpacity',default_value=.8)
    output(multiply(mark,multiply(mark,mask,life),opacity),unreal.MaterialProperty.MP_OPACITY)
    tint=node(mark,unreal.MaterialExpressionVectorParameter,parameter_name='MarkTint',default_value=unreal.LinearColor(.07,.055,.04,1))
    # Dark center and lighter abrasion ring, entirely procedural.
    edge=custom(mark,'return .28+.72*smoothstep(.12,.65,length((UV-.5)*2));',{'UV':uv})
    output(multiply(mark,tint,edge),unreal.MaterialProperty.MP_BASE_COLOR)
    output(constant(mark,.85),unreal.MaterialProperty.MP_ROUGHNESS)
    save(mark)

names=('Metal','Wood','Stone','Dirt','Glass','Flesh')
tints=((.17,.18,.19),(.19,.105,.044),(.22,.21,.19),(.10,.065,.025),(.36,.42,.44),(.13,.016,.012))
for name,tint in zip(names,tints):
    path=DEST+'/MI_ImpactMark_'+name
    mi=unreal.load_asset(path)
    if not mi:
        mi=TOOLS.create_asset('MI_ImpactMark_'+name,DEST,unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
        LIB.set_material_instance_parent(mi,mark)
        LIB.set_material_instance_vector_parameter_value(mi,'MarkTint',unreal.LinearColor(*tint,1))
        LIB.set_material_instance_scalar_parameter_value(mi,'MarkOpacity',.55 if name=='Glass' else .8)
        save(mi)

# Original short Foley-like transients: dry impact + material resonances, three
# deterministic variations each. No borrowed footstep, explosion or gunfire clip.
sample_rate=48000
for bank,name in enumerate(names):
    for variant in range(3):
        rng=random.Random(140900+bank*37+variant)
        length=(.27,.14,.18,.12,.24,.12)[bank]
        frames=[]; low=0.; previous=0.
        freqs=((2900,4700,6900),(380,810,1450),(1300,2800,5200),(160,420,960),(3800,6200,9400),(180,330,780))[bank]
        for i in range(int(length*sample_rate)):
            t=i/sample_rate; noise=rng.uniform(-1,1)
            low+=.22*(noise-low); high=noise-previous; previous=noise
            attack=min(1.,t/.0007)
            snap=high*math.exp(-t/(.006 if bank in (0,4) else .014))*.26
            grain=low*math.exp(-t/(.022 if bank in (1,3,5) else .035))*.65
            ring=0.
            for j,f in enumerate(freqs):
                decay=(.065 if bank==0 else .045 if bank==4 else .013)/(1+j*.3)
                ring+=math.sin(math.tau*f*(1+variant*.017)*t)*math.exp(-t/decay)*(.13/(j+1))
            end=min(1.,max(0.,(length-t)/.008))
            frames.append((snap+grain+ring)*attack*end)
        gain=.65/max(.001,max(abs(v) for v in frames))
        pcm=array.array('h',(int(max(-32767,min(32767,v*gain*32767))) for v in frames))
        filename=SOURCE/f'Impact_{name}_{variant}.wav'
        with wave.open(str(filename),'wb') as wav:
            wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(sample_rate);wav.writeframes(pcm.tobytes())
        asset_name=f'S_Impact_{name}_{variant}'
        if not unreal.EditorAssetLibrary.does_asset_exist(DEST+'/'+asset_name):
            task=unreal.AssetImportTask()
            task.set_editor_property('filename',str(filename))
            task.set_editor_property('destination_path',DEST)
            task.set_editor_property('destination_name',asset_name)
            task.set_editor_property('automated',True)
            task.set_editor_property('save',True)
            TOOLS.import_asset_tasks([task])
        sound=unreal.load_asset(DEST+'/'+asset_name)
        if not sound:
            raise RuntimeError('Sound import failed: '+asset_name)
        sound.set_editor_property('loading_behavior',unreal.SoundWaveLoadingBehavior.FORCE_INLINE)
        save(sound)

(SOURCE/'CREDITS.md').write_text('# Surface impact assets\n\nOriginal procedural HLSL and synthesized mono PCM transients authored for FPSGAME. No downloaded or third-party art/audio. Geometry uses Unreal Engine BasicShapes Plane/Cube under the engine license. Rebuild with Tools/AssetPipeline/build_surface_impact_assets.py.\n\nCreation/import/material compilation only; no game, listening or performance test was run.\n',encoding='utf-8')
unreal.log('SURFACE_IMPACT_ASSETS_CREATED gameplay_not_run')
