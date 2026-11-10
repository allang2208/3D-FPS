"""Author hammer-only warm surface fire. Compile/save only; no play or render."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API, LIB, ref, put, setdata, setup_emitter, user_parameter, smooth
from author_flame_armor_v2 import FLOAT, VEC2, VEC3, VEC4, POSITION, COLOR
from build_fireball_assets import emitters

SOURCE = '/Game/Skills/FlameArmor20261108/SwordRestoreV11/NS_FlameArmorSword'
SYSTEM = '/Game/Skills/FlameArmor20261109/HammerSurfaceV13/NS_FlameArmorHammer'
MATERIAL = '/Game/Skills/FlameArmor20261109/HammerSurfaceV13/M_HammerSurfaceFlameV14'
EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
COUNT = 32
SEED, SHAPE = 'Particles.FlameSeed', 'Particles.FlameShape'
ANCHOR, NORMAL = 'Particles.HammerAnchor', 'Particles.HammerNormal'
WANDER, DIRECTION = 'Particles.HammerWander', 'Particles.HammerDirection'
AGE, N = 'Particles.Age', 'Particles.NormalizedAge'


def stage(system, name, script, values):
    entries = []
    for key, (typ, _) in values.items():
        entry = u.NiagaraExt_SetParameterEntry()
        entry.import_text('(Variable=(Name="'+key+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2)))')
        entries.append(entry)
    module = str(API.call_method('AddSetParametersModule', (ref(system, name, script), entries)).get_editor_property('module_name'))
    for key, (_, expression) in values.items():
        put(system, name, script, module, key, '(HlslExpression="'+expression+'")', EXPR)


def random(channel, salt):
    # VectorVM frac uses x-trunc(x), unlike shader frac(x-floor(x)). Make the
    # input positive BEFORE frac: negative seeds selected nonexistent patches
    # and sqrt(negative) put roots at zero, inside the hammer head.
    return f'frac(abs(sin(float(Particles.UniqueID)*{1.173+channel*.379:.6f}+User.VariationSeed*.00131+{salt+channel*23.147:.5f})*43758.5453))'


def noise(t):
    a = f'frac(abs(sin(floor({t})*127.1+19.19)*43758.5453))'
    b = f'frac(abs(sin((floor({t})+1.)*127.1+19.19)*43758.5453))'
    return f'lerp({a},{b},{smooth("0.","1.","frac("+t+")")})'


def select_vertex(prefix):
    # Selection only happens at birth. Uploaded triangles are area-stratified
    # from LOD0 and all three corners remain on the original mesh triangle.
    return '('+'+'.join(f'User.Hammer{prefix}{i}*saturate(1.-abs(Particles.HammerPatch-{i}.))' for i in range(COUNT))+')'


def renderer_material(donor, name):
    data = json.loads(API.call_method('GetRendererData', (ref(donor, name, renderer=0),)).get_editor_property('property_values'))
    path = data['Material']
    if isinstance(path, dict):
        path = path['refPath']
    asset = u.load_asset(path)
    if asset is None:
        raise RuntimeError('Missing restored material '+str(path))
    return asset


def contact_material(source):
    # The sword material's 0.45 cm fade suppresses roots sitting only 0.06 cm
    # above a thick head. Adapt a dedicated copy, retaining its atlas/color.
    mat = u.load_asset(MATERIAL) if u.EditorAssetLibrary.does_asset_exist(MATERIAL) else u.EditorAssetLibrary.duplicate_asset(source.get_path_name(), MATERIAL)
    if not isinstance(mat, u.Material):
        raise RuntimeError('Cannot copy hammer contact material')
    nodes = list(LIB.get_material_expressions(mat))
    tag = 'Hammer V14 surface contact fade'
    contact = next((n for n in nodes if n.get_editor_property('desc') == tag), None)
    if contact is None:
        contact = LIB.create_material_expression(mat, u.MaterialExpressionConstant)
        contact.set_editor_property('desc', tag)
    contact.set_editor_property('r', .08)
    for node in nodes:
        if isinstance(node, u.MaterialExpressionDepthFade):
            if not LIB.connect_material_expressions(contact, '', node, 'FadeDistance'):
                raise RuntimeError('Cannot connect hammer contact fade')
    # The donor's 0.12 radiance was a dim accent beside its bright sword-core
    # layer. This head has no luminous strip underneath: the same value renders
    # as dark alpha wisps in daylight. Calibrate only this dedicated flame copy,
    # before the existing (single) exposure compensation, preserving atlas alpha.
    eye = next(n for n in nodes if isinstance(n, u.MaterialExpressionEyeAdaptationInverse))
    gain = LIB.get_inputs_for_material_expression(mat, eye)[0]
    if not isinstance(gain, u.MaterialExpressionMultiply) or LIB.get_inputs_for_material_expression(mat,gain)[1] is not None:
        raise RuntimeError('Unexpected source flame radiance chain')
    gain.set_editor_property('const_b', 3.0)
    gain.set_editor_property('desc', 'Hammer calibrated flame radiance before exposure')
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(mat, False):
        raise RuntimeError('Cannot save hammer contact material')
    return mat


def birth(system, name, salt, width, height, lifetime, opacity):
    r = [random(i, salt) for i in range(10)]
    stage(system, name, 'ParticleSpawnScript', {
        SEED: (VEC4, f'float4({r[0]},{r[1]},{r[2]},{r[3]})'),
        SHAPE: (VEC4, f'float4({width[0]}+{width[1]}*{r[4]},{height[0]}+{height[1]}*{r[5]},45.+15.*{r[6]},{opacity[0]}+{opacity[1]}*{r[7]})'),
        'Particles.Lifetime': (FLOAT, f'{lifetime[0]}+{lifetime[1]}*{r[8]}'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
    })
    stage(system, name, 'ParticleSpawnScript', {
        'Particles.HammerPatch': (FLOAT, f'min(31.,floor({SEED}.x*32.))'),
    })
    stage(system, name, 'ParticleSpawnScript', {
        'Particles.HammerA': (VEC3, select_vertex('A')),
        'Particles.HammerB': (VEC3, select_vertex('B')),
        'Particles.HammerC': (VEC3, select_vertex('C')),
        NORMAL: (VEC3, f'normalize({select_vertex("N")}+float3(.000001,0,0))'),
    })
    # Uniform barycentric sampling stays on a real triangle, rather than on
    # its enclosing box or a chord interpolated across a rounded head.
    stage(system, name, 'ParticleSpawnScript', {
        ANCHOR: (POSITION, f'Particles.HammerA*(1.-sqrt({SEED}.y))+Particles.HammerB*(sqrt({SEED}.y)*(1.-{SEED}.z))+Particles.HammerC*(sqrt({SEED}.y)*{SEED}.z)+{NORMAL}*.06'),
    })


def appearance(system, name, script, ember=False, bed=False):
    nx = noise(f'({AGE}*(2.1+{SEED}.z*2.3)+{SEED}.x*31.)')
    ny = noise(f'({AGE}*(1.7+{SEED}.w*2.9)+{SEED}.y*47.)')
    nz = noise(f'({AGE}*(2.9+{SEED}.x)+{SEED}.w*59.)')
    stage(system, name, script, {
        WANDER: (VEC3, f'float3(2.*{nx}-1.,2.*{ny}-1.,{nz})'),
    })
    stage(system, name, script, {
        DIRECTION: (VEC3, f'User.FlameUp-{NORMAL}*min(0.,dot(User.FlameUp,{NORMAL}))+{NORMAL}*.3+float3({WANDER}.x,{WANDER}.y,0)*.19-User.HammerFlow*.00022'),
    })
    direction = f'normalize({DIRECTION}-{NORMAL}*min(0.,dot({DIRECTION},{NORMAL}))+{NORMAL}*.06)'
    envelope = f'{smooth("0.",".06",N)}*(1.-{smooth(".76","1.",N)})'
    look = {
        # No velocity integration or random root wandering. Only the tip
        # direction/length breathes; the current weapon frame carries roots.
        'Particles.Position': (POSITION, ANCHOR),
        'Particles.SpriteAlignment': (VEC3, direction),
        'Particles.SpriteRotation': (FLOAT, '0.'),
        # The copied sprite renderer explicitly binds Particles.UVScale.
        'Particles.UVScale': (VEC2, 'float2(1,1)'),
        'Particles.SpriteSize': (VEC2, f'{SHAPE}.xy*float2(.88+.18*{WANDER}.z,.82+.24*{WANDER}.z)*(.92+.08*User.WeaponSize)'),
        'Particles.SubImageIndex': (FLOAT, f'min(62.999,{SEED}.w*14.+{AGE}*{SHAPE}.z)'),
        'Particles.MaterialRandom': (FLOAT, f'{SEED}.w'),
        # Warm color conversion is already in the restored material. Preserve
        # its fire texture/detail; do not compensate with white opacity slabs.
        'Particles.Color': (COLOR, f'float4(lerp(float3(1.,.82,.55),float3(1.,1.,.86),{SEED}.z),User.Fade*{SHAPE}.w*{envelope}*(.92+.08*{WANDER}.z))'),
        'Particles.DynamicMaterialParameter': (VEC4, f'float4(1.05+.10*{SEED}.w,.85+.15*{smooth(".75","1.",N)},1.,1.)'),
    }
    if ember:
        look.update({
            # A small local rise keeps sparks in the head envelope even when
            # the camera moves quickly. No detached world-space flame sheet.
            'Particles.Position': (POSITION, f'{ANCHOR}+{direction}*{AGE}*4.'),
            'Particles.SpriteSize': (VEC2, f'{SHAPE}.xy*(1.-{N}*.5)'),
            'Particles.SubImageIndex': (FLOAT, '0.'),
            'Particles.Color': (COLOR, f'float4(lerp(float3(1.8,.48,.045),float3(.65,.04,.002),{N}),User.Fade*{SHAPE}.w*{envelope})'),
        })
    stage(system, name, script, look)


def layer(system, material, name, rate, salt, width, height, lifetime, opacity, ember=False, bed=False):
    setup_emitter(system, name, material, rate, True)
    activity = noise(f'(User.FlameClock*{.83+salt*.001:.4f}+User.VariationSeed*.019+{salt}.)')
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="{rate}*max(0.,User.Detail)*(.9+.1*User.Coverage)*(.85+.15*{activity})")', EXPR)
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'SubImageSize': {'X': 1 if ember else 8, 'Y': 1 if ember else 8},
        'bSubImageBlend': not ember,
        # Embed the transparent atlas foot into the contact plane. The warm
        # source material still depth-tests against the actual hammer.
        'PivotInUVSpace': {'X': .5, 'Y': .5 if ember else .82 if bed else .87},
        'SortMode': 'None', 'SortOrderHint': 1,
    })
    birth(system, name, salt, width, height, lifetime, opacity)
    for script in ('ParticleSpawnScript', 'ParticleUpdateScript'):
        appearance(system, name, script, ember, bed)


def run():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before saving the hammer surface fire')
    if {SYSTEM,MATERIAL}.intersection(p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved hammer surface assets')
    donor = u.load_asset(SOURCE)
    if donor is None:
        raise RuntimeError('Install restored warm sword fire first')
    source_flame = renderer_material(donor, 'WeaponFireballTongues')
    flame = contact_material(source_flame)
    ember = renderer_material(donor, 'WeaponEmbers')
    system = u.load_asset(SYSTEM) if u.EditorAssetLibrary.does_asset_exist(SYSTEM) else u.EditorAssetLibrary.duplicate_asset(SOURCE, SYSTEM)
    if system is None:
        raise RuntimeError('Cannot create dedicated hammer surface fire')
    keep = {'HammerContactV13', 'HammerTonguesV13', 'HammerSparksV13'}
    for name in emitters(system):
        if name not in keep:
            API.call_method('RemoveEmitter', (ref(system, name),))
    for name in ('FlameUp', 'HammerFlow'):
        user_parameter(system, name, VEC3)
    for name in ('Fade', 'Detail', 'Coverage', 'WeaponSize', 'VariationSeed', 'FlameClock'):
        user_parameter(system, name, FLOAT)
    for i in range(COUNT):
        for prefix in ('A', 'B', 'C', 'N'):
            user_parameter(system, f'Hammer{prefix}{i}', VEC3)
    layer(system, flame, 'HammerContactV13', 72., 31, (6.2,3.6), (8.,5.), (.56,.26), (.80,.18), bed=True)
    layer(system, flame, 'HammerTonguesV13', 42., 109, (6.,3.), (14.,8.), (.55,.28), (.84,.15))
    layer(system, ember, 'HammerSparksV13', 3.5, 223, (.16,.16), (.45,.45), (.25,.20), (.45,.25), ember=True)
    system.set_editor_property('require_current_frame_data', True)
    system.set_editor_property('fixed_tick_delta', False)
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-160,-160,-160), max=u.Vector(160,160,160)))
    setdata('SetSystemData', u.NiagaraExt_SystemData, system, {'bFixedBounds': True})
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Hammer surface Niagara compilation failed')
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.Revision', 'HammerSurfaceVisibleFireV16-20261109')
    if not u.EditorAssetLibrary.save_loaded_asset(system, False):
        raise RuntimeError('Cannot save hammer surface Niagara')
    profiles = json.loads((OUT/'surface-data.json').read_text(encoding='utf-8'))
    (OUT/'install-receipt.json').write_text(json.dumps(dict(
        revision='HammerSurfaceVisibleFireV16', saved_assets=[flame.get_path_name(),system.get_path_name()], source=SOURCE,
        random_hash='frac(abs(sin(...)*43758.5453)); nonnegative in CPU VectorVM and GPU HLSL',
        source_flame_material=source_flame.get_path_name(), reused_materials=[ember.get_path_name()],
        material_changes='hammer-only copy: contact fade 0.45 to 0.08 cm; flame radiance 0.12 to 3.0 before original exposure node', shared_material_changes=False,
        uv_scale_attribute='Particles.UVScale', contact_fade_cm=.08,
        mesh_profiles=[p['mesh'] for p in profiles], triangles_per_mesh=COUNT,
        birth_sampling='uniform barycentric inside area-stratified actual LOD0 triangles',
        root_clearance_cm=.06, root_motion='rigid weapon-local; no integration',
        local_layers=sorted(keep), world_space_layers=0, persistent_strip_particles=0,
        maximum_systems_per_hammer=1, geometry_scans_per_frame=0,
        mesh_parameters_upload='equipment, geometry or scale change only',
        spawn_rate_ceiling=dict(contact=72.,tongues=42.,sparks=3.5),
        lifetime_ceiling_seconds=dict(contact=.82,tongues=.83,sparks=.45),
        nominal_flame_height_cm=dict(contact=[8,13],tongues=[14,22]),
        runtime_tested=False, rendered=False), indent=2), encoding='utf-8')
    print('HAMMER_SURFACE_FIRE_SAVED', system.get_path_name())


if __name__ == '__main__':
    run()
