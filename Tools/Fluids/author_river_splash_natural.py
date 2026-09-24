"""Install the bounded, baked river splash; no map edits or runtime testing."""
import json
import sys
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir())).resolve()
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
import author_river_pilot as b

SOURCE = ROOT / 'SourceAssets/RiverSplashNatural20260924'
TEXTURES = '/Game/Fluids/RiverSplashNatural20260924'


def texture():
    task = u.AssetImportTask()
    for key, value in dict(filename=str(SOURCE / 'T_RiverSplashPacked.png'),
                           destination_path=TEXTURES, destination_name='T_RiverSplashPacked',
                           automated=True, replace_existing=True, save=False).items():
        task.set_editor_property(key, value)
    b.TOOLS.import_asset_tasks([task])
    paths = task.get_editor_property('imported_object_paths')
    if not paths:
        raise RuntimeError('Splash atlas import failed')
    result = u.load_asset(paths[0])
    for key, value in dict(srgb=False,
                           compression_settings=u.TextureCompressionSettings.TC_BC7,
                           mip_gen_settings=u.TextureMipGenSettings.TMGS_SIMPLE_AVERAGE,
                           address_x=u.TextureAddress.TA_CLAMP,
                           address_y=u.TextureAddress.TA_CLAMP,
                           filter=u.TextureFilter.TF_TRILINEAR,
                           # One bounded 2.67 MiB atlas: coarse resident tails
                           # mix animation tiles and cannot represent coverage.
                           never_stream=True).items():
        result.set_editor_property(key, value)
    b.save(result)
    return result


def material(name, sheet, atlas):
    m = b.own(name)
    b.LIB.delete_all_material_expressions(m)
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('translucency_lighting_mode', u.TranslucencyLightingMode.TLM_SURFACE_PER_PIXEL_LIGHTING)
    if sheet:
        # Short-lived atlas cards must not replace the river in front-layer
        # reflection/depth reconstruction with their rectangular proxy surface.
        m.set_editor_property('allow_front_layer_translucency', False)
    b.LIB.set_base_material_usage(m, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    uv = b.node(m, u.MaterialExpressionTextureCoordinate)
    age = b.node(m, u.MaterialExpressionParticleRelativeTime)
    color = b.node(m, u.MaterialExpressionParticleColor)
    dynamic = b.node(m, u.MaterialExpressionDynamicParameter)
    dynamic.set_editor_property('param_names', ['Variant', 'UnusedY', 'UnusedZ', 'UnusedW'])
    if sheet:
        manifest=json.loads((SOURCE/'bake-manifest.json').read_text(encoding='utf-8'))
        valid_frames=[float(min(manifest.get('empty_frames',{}).get(str(i),[33]))-1) for i in range(4)]
        tex = b.node(m, u.MaterialExpressionTextureObject)
        tex.set_editor_property('texture', atlas)
        tex.set_editor_property('sampler_type', u.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        fields = b.custom(m, (SOURCE / 'SplashSample.hlsl').read_text(encoding='utf-8'),
                          {'UV': uv, 'Age': age, 'Variant': dynamic, 'Atlas': tex,
                           'EndFrames': (b.vector(m,'SplashValidFrames',valid_frames),'RGBA')}, 4,
                          'Mantaflow splash: one variant, two interpolated samples')
        foam = b.custom(m, 'return saturate(pow(saturate(Packed.b),1.2)*.85);', {'Packed': fields})
        shape = b.custom(m, 'return Packed.a*(.36+.46*Foam)*Alpha;',
                         {'Packed': fields, 'Foam': foam, 'Alpha': (color, 'A')})
        normal = b.custom(m, 'float2 n=(Packed.rg*2-1)*.8;return normalize(float3(n,sqrt(saturate(1-dot(n,n)))));',
                          {'Packed': fields}, 3)
    else:
        foam = b.custom(m, 'return smoothstep(.54,.92,Variant)*.75;', {'Variant': dynamic})
        shape = b.custom(m, (b.OUT / 'DropShape.hlsl').read_text(encoding='utf-8'),
                         {'UV': uv, 'Age': age, 'Alpha': (color, 'A'), 'Variant': dynamic})
        normal = b.custom(m, 'float2 p=(UV-.5)*2;return normalize(float3(p*float2(.68,.40),sqrt(saturate(1-dot(p,p)*.65))+.35));', {'UV': uv}, 3)
    fade = b.node(m, u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 2.)
    b.wire(shape, fade, 'Opacity'); b.prop(m, fade, 'OPACITY')
    b.prop(m, normal, 'NORMAL')
    b.prop(m, b.custom(m, 'return lerp(float3(.11,.19,.21),float3(.78,.84,.86),Foam);', {'Foam': foam}, 3), 'BASE_COLOR')
    b.prop(m, b.custom(m, 'return lerp(.07,.32,Foam);', {'Foam': foam}), 'ROUGHNESS')
    specular = b.scalar(m, 'WaterSpecular', .5)
    if sheet:
        specular = b.custom(m, 'return Specular*saturate(Packed.a*8);', {'Specular': specular, 'Packed': fields})
    b.prop(m, specular, 'SPECULAR')
    b.prop(m, b.custom(m, 'return float3(.68,.76,.8)*Foam*.025;', {'Foam': foam}, 3), 'EMISSIVE_COLOR')
    # No refraction input, collision query or additional material pass.
    b.EAL.set_metadata_tag(m, 'RiverPilot.Polish', '4')
    if sheet:
        b.EAL.set_metadata_tag(m, 'RiverPilot.CardBackgroundFix', '2-empty-frames')
    b.save(m)
    return m


def system(drop, crown):
    s = b.own('NS_RiverBulletSplash', '/Game/Weapons/GunplayFX/NS_FPS_MuzzleSmokeShotV15')
    s.set_editor_property('determinism', False)
    s.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-150, -150, -20), max=u.Vector(150, 150, 160)))
    for emitter in b.API.call_method('GetSystemSummary', (s,)).get_editor_property('emitters'):
        b.API.call_method('RemoveEmitter', (b.ref(s, str(emitter.get_editor_property('emitter_name'))),))
    enum_source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    torch = u.load_asset('/Game/Props/RomanColumn20260915/NS_TorchFlame')
    binding = json.loads(b.API.call_method('GetRendererData', (b.ref(torch, 'NE_Flame_01', renderer=0),)).get_editor_property('property_values'))['SpriteAlignmentBinding']
    for e, mat, sheet in [('WaterDrops', drop, False), ('WaterCrown', crown, True)]:
        b.API.call_method('AddEmitter', (s, u.load_asset('/Game/Vefects/Free_Fire/Shared/Particles/NE_FireFlame'), e))
        top = b.API.call_method('GetEmitterTopology', (b.ref(s, e),))
        for script, prop, keep in [('EmitterUpdateScript', 'emitter_update_script', ['EmitterState']),
                                    ('ParticleSpawnScript', 'particle_spawn_script', ['InitializeParticle']),
                                    ('ParticleUpdateScript', 'particle_update_script', ['ParticleState'])]:
            for module in top.get_editor_property(prop).get_editor_property('modules'):
                name = str(module.get_editor_property('module_name'))
                if name not in keep:
                    b.API.call_method('RemoveModule', (b.ref(s, e, script, name),))
        b.data('SetEmitterData', u.NiagaraExt_EmitterData, b.ref(s, e),
               {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False, 'bDeterminism': False})
        for key, old, new in [('Life Cycle Mode', 'System', 'Self'), ('Loop Behavior', 'Infinite', 'Once')]:
            value = u.RainAssetEditor.read_input(enum_source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
            b.put(s, e, 'EmitterUpdateScript', 'EmitterState', key,
                  value.replace('NewEnumerator0', 'NewEnumerator1').replace('"' + old + '"', '"' + new + '"'),
                  '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        b.put(s, e, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=0.1)')
        b.API.call_method('AddModule', (b.ref(s, e, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
        count = '1' if sheet else '(User.Strength<.5?(Engine.Owner.LODDistance<4000?4:2):(Engine.Owner.LODDistance<1800?12:(Engine.Owner.LODDistance<4000?7:3)))'
        b.put(s, e, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
              '(HlslExpression="' + count + '")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
        b.put(s, e, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')

        # Engine source: non-deterministic system reset regenerates this seed.
        # Keep the seeded appearance constant for the entire particle lifetime.
        phase = 'frac(sin(float(Engine.System.RandomSeed)*.0001)*43758.5453)'
        seed = 'frac(float(Particles.UniqueID)*.61803399+' + phase + ')'
        height_seed = 'frac(float(Particles.UniqueID)*.41421356+' + phase + '*.731)'
        # Full water bodies receive the accepted .85 minimum from native code.
        # Thin puddles use a quarter-size splash and only four droplets.
        power = 'clamp(User.Strength,.18,1.25)'
        theta = '(' + seed + '*6.2831853)'
        vertical = '(210+100*' + height_seed + ')'
        radial = '(65+105*' + seed + ')'
        velocity = 'float3(cos(' + theta + ')*' + radial + ',sin(' + theta + ')*' + radial + ',' + vertical + ')*' + power + '+float3(User.Flow.xy,0)'
        size = 'float2(64,64)*(.90+.16*' + seed + ')*' + power if sheet else (
            'float2(1.6+1.3*' + seed + ',2.8+min(length(Particles.Velocity)*.008,3.0))*(.85+.3*' + height_seed + ')*' + power)
        birth_size = 'float2(64,64)*(.90+.16*' + seed + ')*' + power if sheet else 'float2(2.4,4.5)*' + power
        life = '(.58+.10*' + height_seed + ')*(User.Strength<.5?.6:1)' if sheet else '2*' + vertical + '*' + power + '/980'
        b.assign(s, e, 'ParticleSpawnScript', {
            'Particles.SplashOrigin': (b.POSITION, 'Engine.Owner.Position'),
            'Particles.SplashVelocity': (b.V3, velocity),
            'Particles.Lifetime': (b.FLOAT, life),
            'Particles.DynamicMaterialParameter': (b.V4, 'float4(' + seed + ',0,0,0)'),
            'Particles.SpriteSize': (b.V2, birth_size),
            'Particles.SpriteAlignment': (b.V3, 'float3(0,0,1)'),
            'Particles.SpriteRotation': (b.FLOAT, '0'), 'Particles.SpriteUVScale': (b.V2, 'float2(1,1)'),
            'Particles.SubImageIndex': (b.FLOAT, '0'),
            'Particles.Color': (b.COLOR, 'float4(1,1,1,1)'),
            'Particles.Position': (b.POSITION, 'Engine.Owner.Position')})
        age_fade = 'saturate((Particles.NormalizedAge-.82)/.18)'
        age_fade = '(1-(' + age_fade + ')*(' + age_fade + ')*(3-2*(' + age_fade + ')))'
        distance_fade = 'saturate((12000-Engine.Owner.LODDistance)/3000)' if sheet else 'saturate((6500-Engine.Owner.LODDistance)/1500)'
        alpha = '1' if sheet else '(.70+.23*' + seed + ')'
        b.assign(s, e, 'ParticleUpdateScript', {
            'Particles.Position': (b.POSITION, 'Particles.SplashOrigin+float3(User.Flow.xy,0)*Particles.Age*.35' if sheet else
                                   'Particles.SplashOrigin+Particles.SplashVelocity*Particles.Age+float3(0,0,-490)*Particles.Age*Particles.Age'),
            'Particles.Velocity': (b.V3, 'Particles.SplashVelocity+float3(0,0,-980)*Particles.Age'),
            'Particles.SpriteAlignment': (b.V3, 'float3(0,0,1)' if sheet else 'normalize(Particles.Velocity+float3(.001,0,0))'),
            'Particles.SpriteRotation': (b.FLOAT, '0'), 'Particles.SpriteUVScale': (b.V2, 'float2(1,1)'),
            'Particles.SubImageIndex': (b.FLOAT, '0'), 'Particles.SpriteSize': (b.V2, size),
            'Particles.Color': (b.COLOR, 'float4(1,1,1,' + alpha + '*' + age_fade + '*' + distance_fade + ')')})
        b.data('SetRendererData', u.NiagaraExt_RendererData, b.ref(s, e, renderer=0), {
            'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
            'Alignment': 'CustomAlignment', 'FacingMode': 'FaceCamera', 'SpriteAlignmentBinding': binding,
            'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
            'PivotInUVSpace': {'X': .5, 'Y': .79 if sheet else .5},
            'bCastShadows': False, 'bUseMaterialCutoutTexture': False, 'CutoutTexture': None,
            'bEnableCameraDistanceCulling': True, 'MinCameraDistance': 0,
            'MaxCameraDistance': 12000 if sheet else 6500})
    b.EAL.set_metadata_tag(s, 'RiverPilot.Polish', '4')
    b.save(s)


def author():
    if ROOT != Path('D:/FPS3D/FPSGAME').resolve():
        raise RuntimeError('Wrong project')
    if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
        editor = u.get_editor_subsystem(u.LevelEditorSubsystem)
        if editor and editor.is_in_play_in_editor():
            raise RuntimeError('End PIE before replacing splash emitter graphs')
    # The source atlas must exist before any material/emitter mutation.
    if not (SOURCE / 'T_RiverSplashPacked.png').is_file():
        raise RuntimeError('Bake the original liquid atlas before importing')
    b.SAVED.clear()
    atlas = texture()
    system(material('M_RiverDrop', False, atlas), material('M_RiverCrown', True, atlas))
    receipt = {'revision': 'splash-natural4-emptyframefix', 'saved': b.SAVED,
               'variants': 4, 'frames_per_variant': 32,
               'particles_per_hit_near': 13, 'particles_per_hit_mid': 8, 'particles_per_hit_far': 4,
               'pool_slots_unchanged': 12, 'max_duration_seconds': .80,
               'atlas_size': [1024, 2048], 'atlas_compression': 'BC7 with resident mips (bounded 2.67 MiB)',
               'estimated_full_mip_texture_bytes': 2796208,
               'runtime_fluid_solver': False, 'refraction': False,
               'native_code_changed': False, 'river_material_changed': False,
               'runtime_tested': False, 'visual_tested': False, 'performance_measured': False}
    (SOURCE / 'delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    manifest_path = b.OUT / 'assets.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest.update(revision='ripple-polish2_splash-natural4-emptyframefix', particles_per_hit=13,
                    saved=list(b.SAVED), splash_only=True, runtime_tested=False, visual_tested=False)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    u.log('RIVER_SPLASH_NATURAL_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    author()
