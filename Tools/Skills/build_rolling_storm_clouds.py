"""Save three magic cloud variants based on Slag/M10's rolling density atlas.

Only /Game/Skills/StormClouds/RollingV1 is written. Monster effects, spell
damage, room probes and the previous cloud assets remain production inputs.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters, setdata, assignments, save, CREATED
from build_fireball_flames import FLOAT, VEC2, VEC3, POSITION, COLOR
from build_blizzard_indoor_v5 import smooth, select_cell

DEST = '/Game/Skills/StormClouds/RollingV1'
SOURCE = ROOT / 'SourceAssets/StormCloudRolling20261012'
EAL = u.EditorAssetLibrary
VEC4 = '/Script/CoreUObject.Vector4f'
REVISION = 'StormCloudRolling20261012'
REPORT = {'revision': REVISION, 'saved_assets': [], 'gameplay_tested': False, 'rendered': False}


def own(source, name):
    path = DEST + '/' + name
    asset = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    if not asset:
        raise RuntimeError('Cannot derive ' + path + ' from ' + source)
    return asset


def persist(asset):
    save(asset)
    REPORT['saved_assets'].append(asset.get_path_name())
    (SOURCE / 'asset-authoring.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')


def material(name, hand=False):
    mat = own('/Game/Monsters/HundredEyedSlag/SmokeVisibilityFixV21/M_SlagPersistentBodySmoke', name)
    nodes = list(LIB.get_material_expressions(mat))
    density = next(n for n in nodes if isinstance(n, u.MaterialExpressionCustom) and
                   str(n.get_editor_property('description')) == 'ImpactSmokeCorrosion20260924 Density')
    density.set_editor_property('code', (SOURCE / 'RollingCloudDensity.hlsl').read_text('utf-8'))
    clock = next((n for n in nodes if isinstance(n, u.MaterialExpressionTime) and
                  str(n.get_editor_property('desc')) == REVISION + ' Clock'), None)
    if not clock:
        clock = LIB.create_material_expression(mat, u.MaterialExpressionTime)
        clock.set_editor_property('desc', REVISION + ' Clock')
    if not LIB.connect_material_expressions(clock, '', density, 'Age'):
        raise RuntimeError('Cannot connect the independent cloud clock')
    for node in nodes:
        if isinstance(node, u.MaterialExpressionDepthFade):
            node.set_editor_property('fade_distance_default', 3. if hand else 6.)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('output_translucent_velocity', False)
    mat.set_editor_property('is_translucency_velocity_from_depth', False)
    mat.set_editor_property('enable_responsive_aa', hand)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES, True)
    LIB.recompile_material(mat)
    if not u.PoisonMaggotMonster.compile_material_assets([mat]):
        raise RuntimeError('Rolling cloud material failed to compile')
    persist(mat)
    return mat


def override(system, emitter, stage, values):
    tag = 'Fireball.Assignments.' + emitter + '.' + stage
    owned = REVISION + '.' + emitter + '.' + stage
    module = EAL.get_metadata_tag(system, owned)
    if module:
        EAL.set_metadata_tag(system, tag, module)
    else:
        EAL.remove_metadata_tag(system, tag)
    # Append after the source cell lookup / position, never replace their maps.
    assignments(system, emitter, stage, values)
    EAL.set_metadata_tag(system, owned, EAL.get_metadata_tag(system, tag))


def cloud_renderer(system, emitter, mat, hand=False):
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, emitter),
            {'InterpolatedSpawnMode': 'NoInterpolation', 'SimTarget': 'CPUSim'})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, emitter, renderer=0), {
        'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False,
        'Alignment': 'Unaligned' if hand else 'CustomAlignment',
        'FacingMode': 'FaceCamera' if hand else 'FaceCameraPosition',
        'MotionVectorSetting': 'Precise' if hand else 'Disable',
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False, 'bCastShadows': False})


def domain(mat):
    system = own('/Game/Skills/ElectricMagic/StormDomainV2/NS_StormDomainCloud', 'NS_StormDomainCloud')
    layers = [('DenseDarkBase', .82, '.046,.052,.066', .76),
              ('RollingCloudBody', .55, '.085,.102,.125', .69),
              ('SlateCloudCrown', .16, '.19,.215,.24', .60),
              ('ElectricCloudRim', .36, '.14,.18,.23', .57),
              ('SoftCloudFringe', .50, '.11,.13,.16', .38)]
    for name, level, tint, opacity in layers:
        cloud_renderer(system, name, mat)
        seed = f'(float(Particles.UniqueID)+{level}*29.7)'
        a, b, c = [f'frac({seed}*{v})' for v in ['.618033989', '.754877666', '.569840296']]
        pulse = f'(1+.045*sin(Particles.Age*(.48+{a}*.22)+{b}*6.28))'
        width = f'min(User.RadiusX,User.RadiusY)*(.42+{c}*.26)*{pulse}'
        height = f'min(({width})*.82,max(4,User.CloudThickness)*(.68+{b}*.12))'
        angle = f'({a}*6.283+{level}+.09*sin(Particles.Age*.39+{b}*6.283))'
        radial = f'sqrt({b})*.61'
        z = f'User.CloudHeight-({height})*.5-(User.CloudThickness-({height}))*{level}'
        pos = f'User.CurrentPosition+(User.Side*cos({angle})*User.RadiusX+User.Up*sin({angle})*User.RadiusY)*({radial})+User.SurfaceNormal*({z})'
        envelope = 'saturate(Particles.Age*4)'
        if name == 'SoftCloudFringe':
            envelope += '*saturate((1-Particles.NormalizedAge)*4)'
        fields = {'Particles.Position': (POSITION, pos), 'Particles.SpriteSize': (VEC2, f'float2({width},{height})'),
                  'Particles.Color': (COLOR, f'float4({tint},{opacity}*User.Strength*({envelope}))'),
                  'Particles.SpriteRotation': (FLOAT, '0'), 'Particles.SpriteAlignment': (VEC3, 'User.SurfaceNormal'),
                  'Particles.DynamicMaterialParameter': (VEC4, f'float4({c},0,0,0)')}
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            override(system, name, stage, fields)
    EAL.set_metadata_tag(system, REVISION, 'Slag/M10 density; 48 bounded lobes; original discharges retained')
    persist(system)


def blizzard(mat):
    target = DEST + '/NS_BlizzardStormCloud'
    if any(str(p.get_path_name()) == target for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved Blizzard cloud edits')
    source = u.load_asset(DEST + '/NS_StormDomainCloud')
    if not source:
        raise RuntimeError('Restore the current StormDomain rolling cloud first')
    names = ['DenseDarkBase', 'RollingCloudBody', 'SlateCloudCrown', 'ElectricCloudRim', 'SoftCloudFringe']
    # Copy the actual storm emitters, including their overlap, size, density and
    # animated material. Do not turn the 25 room probes into visible cloud tiles.
    # Embedded emitter handles are not exposed to UE's Python wrapper. Resolve
    # only NiagaraEmitter objects owned by this loaded source system instead.
    templates = [e for e in u.ObjectIterator(u.NiagaraEmitter) if e.get_outer() == source]
    handles = {name: next((e for e in templates if e.get_name() == name or e.get_name().startswith(name + '_')), None)
               for name in names}
    if any(not handles.get(name) for name in names):
        raise RuntimeError('Missing a source storm cloud layer: ' + ', '.join(e.get_name() for e in templates))
    system = own('/Game/Skills/Blizzard/IndoorV5/NS_BlizzardStormCloud', 'NS_BlizzardStormCloud')
    for name in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, name),))

    delta = '(Particles.Position-User.CurrentPosition)'
    x = f'(dot({delta},User.Side)/max(1,User.RadiusX))'
    y = f'(dot({delta},User.Up)/max(1,User.RadiusY))'
    index = f'(clamp(floor(({y}+1)*2.5),0,4)*5+clamp(floor(({x}+1)*2.5),0,4))'
    cell = 'Particles.RoomCell'
    # Sample between cell centres, not at tile edges. Adjacent stair heights
    # blend into a continuous cloud; separate decks never blend into each other.
    gx, gy = f'clamp(({x}+1)*2.5-.5,0,4)', f'clamp(({y}+1)*2.5-.5,0,4)'
    ix, iy = f'floor({gx})', f'floor({gy})'
    lookups = [f'({iy}*5+{ix})', f'({iy}*5+min(4,{ix}+1))',
               f'(min(4,{iy}+1)*5+{ix})', f'(min(4,{iy}+1)*5+min(4,{ix}+1))']
    fx, fy = 'Particles.RoomBlend.x', 'Particles.RoomBlend.y'
    weights = [f'(1-{fx})*(1-{fy})', f'{fx}*(1-{fy})', f'(1-{fx})*{fy}', f'{fx}*{fy}']
    weighted, totals = [], []
    for label, weight in zip('ABCD', weights):
        neighbor = 'Particles.Room' + label
        accepted = f'(({neighbor}.z>0&&abs({neighbor}.x-{cell}.x)<180)?({weight}):0)'
        totals.append(accepted)
        weighted.append(f'({accepted})*({neighbor}.x+min({neighbor}.y,User.CloudHeight))')
    weight_sum = '(' + '+'.join(totals) + ')'
    average = '(' + '+'.join(weighted) + ')/max(.001,' + weight_sum + ')'
    top = f'({weight_sum}>.001?({average}):({cell}.x+min({cell}.y,User.CloudHeight)))'
    top = f'max({cell}.x+4,min({cell}.x+{cell}.y,{top}))'
    band = f'max(4,min(User.CloudThickness,{cell}.y*.46))'
    height = f'min(Particles.SpriteSize.y,({band})*.8)'
    depth = f'saturate((User.CloudHeight-dot({delta},User.SurfaceNormal)-Particles.SpriteSize.y*.5)/max(1,User.CloudThickness-Particles.SpriteSize.y))'
    z = f'Particles.RoomCloudTop-6-({height})*.5-(({band})-({height}))*({depth})'
    pos = f'Particles.Position+User.SurfaceNormal*(({z})-dot({delta},User.SurfaceNormal))'
    # Open cells keep the full storm-cloud width. Only wall-limited cells narrow.
    width = f'({cell}.z>=.999?Particles.SpriteSize.x:min(Particles.SpriteSize.x,min(User.RadiusX,User.RadiusY)*.4*{cell}.z))'
    mask = f'saturate({cell}.z*12)*{smooth(cell+".y",90,180)}'
    fields = {'Particles.Position': (POSITION, pos),
              'Particles.SpriteSize': (VEC2, f'float2({width},{height})'),
              'Particles.Color': (COLOR, f'float4(Particles.Color.rgb,Particles.Color.a*({mask}))')}
    for name in names:
        API.call_method('AddEmitter', (system, handles[name], name))
        detach_cloud_parent(system, name)
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            tag = 'Fireball.Assignments.' + name + '.' + stage
            # Sampling, height and final placement follow the copied storm position/colour. Each
            # rebuild replaces the five emitters, so no stale module names recur.
            EAL.remove_metadata_tag(system, tag)
            samples = {'Particles.RoomCell': (VEC3, select_cell(index, 'User.RoomCell')),
                       'Particles.RoomBlend': (VEC2, f'float2(frac({gx}),frac({gy}))')}
            samples.update({'Particles.Room'+label: (VEC3, select_cell(lookup, 'User.RoomCell'))
                            for label, lookup in zip('ABCD', lookups)})
            assignments(system, name, stage, samples)
            EAL.remove_metadata_tag(system, tag)
            assignments(system, name, stage, {'Particles.RoomCloudTop': (FLOAT, top)})
            EAL.remove_metadata_tag(system, tag)
            assignments(system, name, stage, fields)
    EAL.set_metadata_tag(system, REVISION, 'StormDomain cloud emitter copies; 48 core lobes plus fringe; local room clipping')
    EAL.set_metadata_tag(system, 'Blizzard.CloudSource', source.get_path_name())
    EAL.set_metadata_tag(system, 'Blizzard.CloudLayout', 'StormDomainLayers20261012')
    EAL.set_metadata_tag(system, 'Blizzard.HeightInterpolation', 'BilinearStairsCeilingClamp20261013')
    REPORT['blizzard_layout'] = 'StormDomainLayers20261012'
    REPORT['blizzard_source'] = source.get_path_name()
    REPORT['blizzard_cloud_emitters'] = names
    REPORT['blizzard_height_interpolation'] = 'bilinear stairs; separate decks; physical ceiling clamp'
    persist(system)


def detach_cloud_parent(system, name):
    # AddEmitter creates inheritance even for a system's private sub-emitter.
    # Match FVersionedNiagaraEmitterData::RemoveParent after copying its graph,
    # otherwise SavePackage rejects the external private-object reference.
    parent = {'Emitter': 'None', 'Version': '00000000-0000-0000-0000-000000000000'}
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'VersionedParent': parent, 'VersionedParentAtLastMerge': parent})


def gather(mat):
    system = own('/Game/Skills/Blizzard/ChargedV3/NS_BlizzardGatherCloud', 'NS_BlizzardGatherCloud')
    for i, name in enumerate(emitters(system)):
        cloud_renderer(system, name, mat, hand=True)
        seed = f'frac((float(Particles.UniqueID)+{i}*17.23)*.569840296)'
        fields = {'Particles.DynamicMaterialParameter': (VEC4, f'float4({seed},0,0,0)'),
                  'Particles.Color': (COLOR, f'float4(.12,.15,.18,User.Strength*(.60+{seed}*.16))')}
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            override(system, name, stage, fields)
    EAL.set_metadata_tag(system, REVISION, '29 local-space lobes; existing hand motion and lifecycle retained')
    persist(system)


def build():
    if any(str(p.get_path_name()).startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved RollingV1 cloud assets')
    EAL.make_directory(DEST)
    world = material('M_RollingStormCloud')
    hand = material('M_RollingGatherCloud', hand=True)
    domain(world)
    blizzard(world)
    gather(hand)
    REPORT.update(stage='assets_saved', atlas_source='HundredEyedSlag SmokeVisibilityFixV21 / M10 LocalGas',
                  texture_samples_per_pixel=2, new_density_textures=0,
                  core_particles={'storm_domain':48, 'blizzard':48, 'gather':29},
                  monster_assets_modified=False, gameplay_modified=False)
    (SOURCE / 'asset-authoring.json').write_text(json.dumps(REPORT, indent=2), encoding='utf-8')
    print('ROLLING_STORM_CLOUDS_SAVED '+json.dumps(REPORT))


if __name__ == '__main__':
    build()
