"""Adapt the restored four-layer warm sword fire to every other weapon surface.

Copies the saved V11 effect and reuses its materials. Geometry fitting is appended after
the original appearance modules; their flames, atlas, alpha and timing remain.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
SOURCE = '/Game/Skills/FlameArmor20261108/SwordRestoreV11/NS_FlameArmorSword'
SYSTEM = '/Game/Skills/FlameArmor20261108/AllWeaponsV12/NS_FlameArmorWeapon'
sys.path.insert(0, str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API, ref, put, setdata, user_parameter, smooth
from author_flame_armor_v2 import FLOAT, VEC2, VEC3, VEC4, POSITION
from build_fireball_assets import emitters
from flame_expression_compat import nonnegative_random_hashes

EXPR = '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression'
P = 'Particles.SourceFlamePosition'
Q = 'Particles.SurfaceCoordinates'
C = 'Particles.WeaponSection'
AXIS = 'normalize(User.WeaponEnd)'
SIDE, NORMAL = 'User.WeaponSide', 'User.WeaponNormal'
STATION = f'saturate(dot(Particles.Position,{AXIS})/max(.1,length(User.WeaponEnd)))'
SOURCE_DEPTH = 2.1709518432617188  # Saved original V5 campfire wrap source profile.


def stage(system, name, script, values):
    entries = []
    for key, (typ, _) in values.items():
        entry = u.NiagaraExt_SetParameterEntry()
        entry.import_text('(Variable=(Name="'+key+'",Type=(ClassStructOrEnum="'+typ+'",UnderlyingType=2)))')
        entries.append(entry)
    module = str(API.call_method('AddSetParametersModule', (ref(system, name, script), entries)).get_editor_property('module_name'))
    for key, (_, value) in values.items():
        put(system, name, script, module, key, '(HlslExpression="'+value+'")', EXPR)
    return module


def surface(t):
    result = 'User.Surface0'
    for i in range(1, 8):
        result = f'lerp({result},User.Surface{i},saturate(({t})*7.-{i-1}.))'
    return '('+result+')'


def source_width(t):
    taper = f'(1.-.92*{smooth(".82", "1.", t)})'
    return f'((5.48-1.65*({t}))*{taper}+.22)'


def fit(system, name, script):
    t = STATION
    taper = f'(1.-.92*{smooth(".82", "1.", t)})'
    width = source_width(t)
    depth = f'({SOURCE_DEPTH}*(.80+.20*(1.-({t})))*{taper}+.22)'
    cache = stage(system, name, script, {
        P: (POSITION, 'Particles.Position'),
        Q: (VEC3, f'float3(dot(Particles.Position,{SIDE})/{width},dot(Particles.Position,{NORMAL})/{depth},dot(Particles.Position,{AXIS}))'),
        C: (VEC4, surface(t)),
    })
    # Flat hammer spans are already on a head face. Bladed tools need their
    # roots on the outer rectangular rim; round barrels/staffs/bows keep the
    # original elliptical orbit. Cross-section offsets preserve curved blades.
    # Float masks avoid the inline-HLSL input parser's ambiguous && namespace
    # tokens, while the runtime still selects exact modes 0, 1 or 2.
    flat = 'saturate(1.-abs(User.SurfaceMode-1.))'
    rim = f'lerp(1.,max(1.,1./max(.01,max(abs({Q}.x),abs({Q}.y)))),saturate(User.SurfaceMode-1.))'
    x = f'({C}.x+{Q}.x*{rim}*({C}.z+.22))'
    y = f'({C}.y+lerp({Q}.y*{rim}*({C}.w+.22),.22+abs({Q}.y)*.22,{flat}))'
    look = {'Particles.Position': (POSITION, f'{AXIS}*{Q}.z+{SIDE}*{x}+{NORMAL}*{y}')}
    # A hammer's four sampled faces all point outwards, including back faces.
    d = 'Particles.SpriteAlignment'
    look['Particles.SpriteAlignment'] = (VEC3,
        f'normalize(lerp({d},{d}-{NORMAL}*dot({d},{NORMAL})+{NORMAL}*abs(dot({d},{NORMAL})),{flat}))')
    if name == 'WeaponFireballCore':
        # The original core's longitudinal size already uses WeaponEnd. Only
        # its cross-width needs fitting; other tongues retain WeaponSize scaling.
        station = f'saturate({Q}.z/max(.1,length(User.WeaponEnd)))'
        look['Particles.SpriteSize'] = (VEC2,
            f'Particles.SpriteSize*float2(clamp(({C}.z+.22)/{source_width(station)},.1,2.)*.45,1.)')
        # The sword's luminous bed becomes oversized beads on short blades,
        # shovel rims and staff crowns. Keep it as a narrow contact glow; the
        # original animated campfire tongues now supply the readable flame.
        look['Particles.Color'] = ('/Script/CoreUObject.LinearColor', 'float4(Particles.Color.rgb,Particles.Color.a*.35)')
    result = stage(system, name, script, look)
    return [cache, result]


def run():
    if '-run=' not in u.SystemLibrary.get_command_line().lower():
        if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('End PIE before saving the all-weapon fire copy')
    if SYSTEM in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved all-weapon fire asset')
    donor = u.load_asset(SOURCE)
    if donor is None:
        raise RuntimeError('Install restored warm sword V11 first')
    system = u.load_asset(SYSTEM) if u.EditorAssetLibrary.does_asset_exist(SYSTEM) else u.EditorAssetLibrary.duplicate_asset(SOURCE, SYSTEM)
    if system is None:
        raise RuntimeError('Cannot copy restored warm fire')
    for key in ('WeaponSide', 'WeaponNormal'):
        user_parameter(system, key, VEC3)
    for i in range(8):
        user_parameter(system, 'Surface'+str(i), VEC4)
    user_parameter(system, 'SurfaceMode', FLOAT)
    system.set_editor_property('require_current_frame_data', True)
    system.set_editor_property('fixed_tick_delta', False)
    layers, adapted = emitters(donor), []
    for name in layers:
        setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
                {'bLocalSpace': True, 'bInterpolatedSpawning': False})
        for script in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            tag = 'FlameArmor.SurfaceFitV12.'+name+'.'+script
            old = u.EditorAssetLibrary.get_metadata_tag(system, tag)
            for module in json.loads(old) if old else []:
                API.call_method('RemoveModule', (ref(system, name, script, module),))
            modules = API.call_method('GetScriptStackInputValues', (ref(donor, name, script),))
            for module in modules:
                module_name = str(module.get_editor_property('module_name'))
                for entry in module.get_editor_property('inputs'):
                    input_name = str(entry.get_editor_property('name'))
                    value = str(u.RainAssetEditor.read_input(donor, name, script, module_name, input_name))
                    if 'HlslExpression=' not in value:
                        continue
                    fitted = nonnegative_random_hashes(value).replace('normalize(cross(normalize(User.WeaponEnd),User.BladeSide))', NORMAL)
                    if script == 'ParticleUpdateScript' and input_name == 'Particles.Position':
                        # Keep free flame/spark integration in the original
                        # source frame. Never feed last frame's fitted position
                        # back through the profile scale a second time.
                        fitted = fitted.replace('Particles.Position', P)
                    # Refresh source expressions even when this input needs no
                    # geometry conversion: an existing V12 copy can still have
                    # the old signed hash after its V11 donor has been repaired.
                    put(system, name, script, module_name, input_name, fitted, EXPR)
                    if fitted != value:
                        adapted.append(dict(emitter=name, script=script, input=input_name))
            owned = fit(system, name, script)
            u.EditorAssetLibrary.set_metadata_tag(system, tag, json.dumps(owned))
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-240,-240,-240), max=u.Vector(240,240,240)))
    setdata('SetSystemData', u.NiagaraExt_SystemData, system, {'bFixedBounds': True})
    if not u.RainAssetEditor.compile_rain(system, True):
        raise RuntimeError('All-weapon fire Niagara compilation failed')
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.Revision', 'RestoredWarmAllWeaponsV12-20261108')
    if not u.EditorAssetLibrary.save_loaded_asset(system, False):
        raise RuntimeError('Cannot save all-weapon fire')
    (OUT/'install-receipt.json').write_text(json.dumps(dict(
        revision='RestoredWarmAllWeaponsV12', source=SOURCE, saved_assets=[system.get_path_name()],
        source_revision=u.EditorAssetLibrary.get_metadata_tag(donor, 'FlameArmor.Revision'),
        original_layers=layers, geometry_adaptations=adapted, source_blade_half_depth_cm=SOURCE_DEPTH,
        material_changes=False, textures_added=False, appearance_layers_added=False,
        opacity_changed=True, core_opacity_multiplier=.35, core_width_multiplier=.45,
        cpu_random_hash='nonnegative before frac', spawn_rates_changed=False, lifetimes_changed=False,
        current_sword_preserved=True, blue_charge_preserved=True, geometry_scans_per_frame=0,
        maximum_held_systems=4, maximum_flying_arrow_systems_per_world=8,
        runtime_tested=False, rendered=False), indent=2), encoding='utf-8')
    print('RESTORED_WARM_ALL_WEAPONS_SAVED', SYSTEM, layers)


if __name__ == '__main__':
    run()
