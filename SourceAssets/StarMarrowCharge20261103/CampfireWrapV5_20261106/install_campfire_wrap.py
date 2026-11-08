"""Campfire-native blue flames, one bounded sword-following orbit layer. No world run."""
import json
import math
import shutil
import sys
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
sys.path.insert(0, str(OUT.parent))
sys.path.insert(0, str(OUT.parent / 'VariationV2'))
from author_flame_armor_v2 import API, LIB, ref, setdata, assignments, put, setup_emitter
from author_flame_armor_v2 import FLOAT, VEC2, VEC3, VEC4, POSITION, COLOR, smooth
from build_fireball_assets import emitters
from build_fireball_outer_flame import enable_sprite_usage
from install_flames import blue
from install_variation import seed, save

BASE = '/Game/Weapons/FrostCrystalSword20260915/StarMarrowCharge20261103'
SYSTEM = BASE + '/NS_StarMarrowDenseBladeFire'
DONOR = '/Game/Building/Campfire20261013/TorchFire/NS_CampfireTorchFire'
DEST = BASE + '/CampfireWrapV5'
MATERIAL = DEST + '/M_StarMarrowCampfireBlue'
BLADE = '/Game/Weapons/FrostCrystalSword20260915/StarMarrow20261102/SM_FrostSword_Blade_star_marrow'
REVISION = 'DenseBladeFlowV5-CampfireBlueWrap-20261106'
RATE = 30
PEAK_SPAWN_RATE = RATE + 14 + 4  # Unchanged motion fire and embers.


def material():
    source = u.load_asset(DONOR)
    if source is None:
        raise RuntimeError('Missing active campfire fire system')
    renderer = json.loads(API.call_method('GetRendererData', (ref(source, 'Fire', renderer=0),)).get_editor_property('property_values'))
    path = renderer['Material']
    if isinstance(path, dict):
        path = path['refPath']
    mat = u.load_asset(MATERIAL) if u.EditorAssetLibrary.does_asset_exist(MATERIAL) else u.EditorAssetLibrary.duplicate_asset(path, MATERIAL)
    if not isinstance(mat, u.Material):
        raise RuntimeError('Expected the active campfire fire material')
    nodes = list(LIB.get_material_expressions(mat))
    tag = 'StarMarrow campfire blended SubUV'
    atlas = next((n for n in nodes if n.get_editor_property('desc') == tag), None)
    if atlas is None:
        # The campfire uses a plain texture sample, which cannot blend frames.
        # Retain all downstream RGB/alpha powers and replace only that sample.
        sample = next(n for n in nodes if isinstance(n, u.MaterialExpressionTextureSample)
                      and n.get_editor_property('texture') is not None)
        atlas = LIB.create_material_expression(mat, u.MaterialExpressionTextureSampleParameterSubUV)
        atlas.set_editor_property('desc', tag)
        atlas.set_editor_property('parameter_name', 'CampfireFlameAtlas')
        atlas.set_editor_property('texture', sample.get_editor_property('texture'))
        atlas.set_editor_property('sampler_type', sample.get_editor_property('sampler_type'))
        atlas.set_editor_property('blend', True)
        for target in nodes:
            names = LIB.get_material_expression_input_names(target)
            for index, connection in enumerate(LIB.get_inputs_for_material_expression(mat, target)):
                if connection == sample:
                    output = LIB.get_input_node_output_name_for_material_expression(target, sample)
                    if not LIB.connect_material_expressions(atlas, output, target, str(names[index])):
                        raise RuntimeError('Cannot retain campfire texture channel')
    # The 4 cm campfire fade would erase small flames at the crystal surface.
    fade_tag = 'StarMarrow campfire blade contact fade'
    contact = next((n for n in nodes if n.get_editor_property('desc') == fade_tag), None)
    if contact is None:
        contact = LIB.create_material_expression(mat, u.MaterialExpressionConstant)
        contact.set_editor_property('desc', fade_tag)
    contact.set_editor_property('r', .45)
    for node in nodes:
        if isinstance(node, u.MaterialExpressionDepthFade):
            if not LIB.connect_material_expressions(contact, '', node, 'FadeDistance'):
                raise RuntimeError('Cannot adapt blade contact fade')
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_AFTER_DOF)
    enable_sprite_usage(mat)
    blue(mat)  # Native campfire opacity and exposure; final output remains blue.
    return mat, path


def wrap(system, mat, half_depth):
    name = 'WeaponFireballTongues'
    setup_emitter(system, name, mat, RATE, True)
    put(system, name, 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate',
        f'(HlslExpression="{RATE}*User.Detail*(.8+.2*saturate(User.Coverage))")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'SubImageSize': {'X': 8, 'Y': 8}, 'bSubImageBlend': True,
        'PivotInUVSpace': {'X': .5, 'Y': .84}, 'SortMode': 'None',
    })
    # Compute randoms once at birth. Continuous position/phase uses the sword's
    # final endpoints and width axis each frame, without world-space integration.
    h = [seed(i, 101.) for i in range(5)]
    orbit = 'Particles.CampfireOrbit'
    shape = 'Particles.CampfireShape'
    age = 'Particles.Age'
    n = 'Particles.NormalizedAge'
    station = f'clamp({orbit}.x+{age}*(.012+.018*{orbit}.w),.055,.95)'
    angle = f'({orbit}.y+{age}*{orbit}.z+.16*sin({age}*5.3+{orbit}.y))'
    axis = 'normalize(User.WeaponEnd)'
    side = 'User.BladeSide'
    normal = f'normalize(cross({axis},{side}))'
    taper = f'(1.-.92*{smooth(".82", "1.", station)})'
    width = f'((5.48-1.65*{station})*{taper}+.22)'
    depth = f'({half_depth:.5f}*(.80+.20*(1.-{station}))*{taper}+.22)'
    shell = f'({side}*cos({angle})*{width}+{normal}*sin({angle})*{depth})'
    # A bounded elliptical wrap keeps flames on both faces and both edges.
    root = f'(User.WeaponEnd*({station})+{shell})'
    outward = f'normalize({side}*cos({angle})*.6+{normal}*sin({angle}))'
    lean = f'lerp(User.BaseFlow,User.TipFlow,{station})*.00018'
    direction = f'normalize({axis}*.42+{outward}*.62+float3(0,0,.38)-{lean})'
    size = f'float2({shape}.x,{shape}.y)*User.WeaponSize*(1.-.48*{smooth(".78", "1.", station)})*(.84+.16*sin({n}*3.141593))'
    envelope = f'{smooth("0", ".08", n)}*(1.-{smooth(".65", "1", n)})'
    look = {
        'Particles.Position': (POSITION, root),
        'Particles.SpriteAlignment': (VEC3, direction),
        'Particles.SpriteRotation': (FLOAT, '0'),
        'Particles.SpriteSize': (VEC2, size),
        'Particles.UVScale': (VEC2, 'float2(1,1)'),
        # No wrap from the last frame to the first: every particle finishes one
        # independently offset animation, smoothly interpolated at render rate.
        'Particles.SubImageIndex': (FLOAT, f'min(62.999,{orbit}.w*12.+{age}*{shape}.z)'),
        'Particles.Color': (COLOR, f'float4(1,.58,.12,User.Fade*{shape}.w*{envelope})'),
        # Campfire X = RGB exponent, Y = alpha exponent (not erosion offset).
        'Particles.DynamicMaterialParameter': (VEC4, f'float4(1.15+.25*{orbit}.w,.9+.4*{smooth(".65", "1", n)},1,1)'),
    }
    # A separate spawn module makes the cached values available before look
    # expressions read them; update never recalculates the per-particle hashes.
    entries = []
    for key in (orbit, shape):
        entry = u.NiagaraExt_SetParameterEntry()
        entry.import_text('(Variable=(Name="'+key+'",Type=(ClassStructOrEnum="'+VEC4+'",UnderlyingType=2)))')
        entries.append(entry)
    module = str(API.call_method('AddSetParametersModule', (ref(system, name, 'ParticleSpawnScript'), entries)).get_editor_property('module_name'))
    cached = {
        orbit: f'float4(.055+.88*{h[0]},6.2831853*{h[1]},(1.8+1.6*{h[2]})*({h[3]}<.5?-1.:1.),{h[4]})',
        shape: f'float4(10.+6.*{h[2]},16.+10.*{h[3]},48.+12.*{h[1]},.64+.22*{h[4]})',
    }
    for key, expr in cached.items():
        put(system, name, 'ParticleSpawnScript', module, key,
            '(HlslExpression="'+expr+'")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    assignments(system, name, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, f'.55+.30*{orbit}.w'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.MaterialRandom': (FLOAT, f'{orbit}.w'), **look,
    })
    assignments(system, name, 'ParticleUpdateScript', look)
    if 'WeaponFireballCurls' in emitters(system):
        API.call_method('RemoveEmitter', (ref(system, 'WeaponFireballCurls'),))
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            u.EditorAssetLibrary.remove_metadata_tag(system, 'Fireball.Assignments.WeaponFireballCurls.'+stage)


def apply(system):
    if MATERIAL in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved campfire sword material')
    mat, donor_material = material()
    # The currently installed modular blade supplies thickness; width taper is
    # the existing StarMarrow edge-bed profile, so both layers share a silhouette.
    blade = u.load_asset(BLADE)
    if blade is None:
        raise RuntimeError('Missing active StarMarrow blade geometry')
    bounds = blade.get_bounding_box()
    half_depth = max(abs(bounds.min.y), abs(bounds.max.y))
    wrap(system, mat, half_depth)
    u.EditorAssetLibrary.set_metadata_tag(system, 'StarMarrow.Revision', REVISION)
    return [mat.get_path_name()], {'donor_material': donor_material, 'blade_half_depth_cm': half_depth}


def run():
    if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('End PIE before saving sword fire')
    if {SYSTEM, MATERIAL}.intersection(p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved sword fire assets')
    system = u.load_asset(SYSTEM)
    if system is None:
        raise RuntimeError('Install the dense sword fire first')
    before = OUT / 'Before/NS_StarMarrowDenseBladeFire.uasset'
    before.parent.mkdir(parents=True, exist_ok=True)
    if not before.exists():
        shutil.copy2(ROOT / ('Content/'+SYSTEM.removeprefix('/Game/')+'.uasset'), before)
    saved, details = apply(system)
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('Campfire sword Niagara compilation failed')
    save(system)
    receipt = dict(revision=REVISION, saved_assets=saved+[system.get_path_name()], donor=DONOR,
        emitter_count=4, preserved_edge_cells=24, random_flame_spawn_rate=RATE,
        previous_random_flame_spawn_rate=60, peak_spawn_per_second=PEAK_SPAWN_RATE,
        previous_peak_spawn_per_second=78, random_flame_lifetime_s=[.55,.85],
        estimated_peak_random_particles=math.ceil(RATE*.85)+1,
        blended_animation_fps=[48,60], actual_fps_measured=False,
        gameplay_tested=False, rendered=False, **details)
    (OUT/'install-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('STAR_MARROW_CAMPFIRE_WRAP_SAVED', receipt)


if __name__ == '__main__':
    run()
