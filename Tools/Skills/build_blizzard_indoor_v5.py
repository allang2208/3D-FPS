"""Author Blizzard's local-room VFX and footprint materials; no game or render.

Run through the serialized editor bridge when UE is already open, otherwise
UnrealEditor-Cmd -run=pythonscript. Only IndoorV5 assets are written.
"""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
sys.path.insert(0, str(ROOT / 'Tools/Skills'))
from build_fireball_assets import API, LIB, ref, emitters, setdata, put, assignments, save, CREATED
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from build_fireball_flight import user_parameter, expression
from build_blizzard_assets import custom
from build_blizzard_charged_v3 import cloud_lifecycle

DEST = '/Game/Skills/Blizzard/IndoorV5'
EAL = u.EditorAssetLibrary
V3 = '/Game/Skills/Blizzard/ChargedV3/'


def own(source, name):
    path = DEST + '/' + name
    asset = u.load_asset(path) if EAL.does_asset_exist(path) else EAL.duplicate_asset(source, path)
    if not asset:
        raise RuntimeError('Missing Blizzard source ' + source)
    return asset


def select_cell(index, prefix):
    return '(' + ''.join(f'{index}<{i + .5}?{prefix}{i}:' for i in range(24)) + prefix + '24)'


def smooth(value, low, high):
    # Niagara's CPU Vector VM has no HLSL smoothstep intrinsic.
    t = f'saturate(({value}-{low})/{high-low}.0)'
    return f'(({t})*({t})*(3-2*({t})))'


def footprint_material(name):
    material = own(V3 + name, name)
    # Idempotent extension of the original frost / red aim artwork.
    if not EAL.get_metadata_tag(material, 'Blizzard.IndoorV5Mask'):
        opacity = LIB.get_material_property_input_node(material, u.MaterialProperty.MP_OPACITY)
        channel = LIB.get_material_property_input_node_output_name(material, u.MaterialProperty.MP_OPACITY)
        inputs = {'A': (opacity, channel)}
        world = LIB.create_material_expression(material, u.MaterialExpressionWorldPosition)
        inputs['World'] = (world, '')
        for key in ['RoomCenter', 'RoomSide', 'RoomForward'] + [f'RoomCell{i}' for i in range(25)]:
            parameter = LIB.create_material_expression(material, u.MaterialExpressionVectorParameter)
            parameter.set_editor_property('parameter_name', key)
            inputs[key] = (parameter, 'RGB')
        for key in ['RadiusX', 'RadiusY']:
            parameter = LIB.create_material_expression(material, u.MaterialExpressionScalarParameter)
            parameter.set_editor_property('parameter_name', key)
            parameter.set_editor_property('default_value', 300.)
            inputs[key] = (parameter, '')
        code = ('float3 delta=World-RoomCenter; '
                'float2 p=float2(dot(delta,RoomSide)/max(1,RadiusX),dot(delta,RoomForward)/max(1,RadiusY)); '
                'float2 grid=clamp(floor((p+1)*2.5),0,4); float index=grid.y*5+grid.x; '
                'float3 cell=' + select_cell('index', 'RoomCell') + '; '
                'float2 local=abs(p-(grid-2)*.4)/.2; '
                'float area=cell.z>=.999?1:saturate((cell.z-max(local.x,local.y))*14); '
                'float band=min(65,max(8,cell.y*.45)); '
                'float floorMask=saturate((band-abs(delta.z-cell.x))/min(25,max(4,band*.4))); '
                'return A*area*floorMask*saturate((1-dot(p,p))*20);')
        mask = custom(material, code, inputs)
        if not LIB.connect_material_property(mask, '', u.MaterialProperty.MP_OPACITY):
            raise RuntimeError('Cannot connect indoor footprint mask')
        EAL.set_metadata_tag(material, 'Blizzard.IndoorV5Mask', '1')
    errors = LIB.recompile_material(material)
    if errors:
        raise RuntimeError(str(errors))
    save(material)


def room_fields(system, emitter, stage):
    tag = 'Fireball.Assignments.' + emitter + '.' + stage
    EAL.remove_metadata_tag(system, tag)
    index = '(fmod(float(Particles.UniqueID),25.0))'
    assignments(system, emitter, stage, {'Particles.RoomCell': (VEC3, select_cell(index, 'User.RoomCell'))})
    # Separate assignment stages make the cell available before position/colour.
    EAL.remove_metadata_tag(system, tag)


def layer(system, name, kind, material):
    API.call_method('AddEmitter', (system, u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core'), name))
    trim(system, name, {'EmitterUpdateScript': ['EmitterState'],
                       'ParticleSpawnScript': ['InitializeParticle'], 'ParticleUpdateScript': ['ParticleState']})
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, name),
            {'bLocalSpace': False, 'SimTarget': 'CPUSim', 'InterpolatedSpawnMode': 'NoInterpolation'})
    cloud, mist = kind == 'cloud', kind == 'mist'
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Material': material.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 8 if mist else 1, 'Y': 8 if mist else 1}, 'bSubImageBlend': mist,
        'Alignment': 'CustomAlignment' if cloud else 'Unaligned',
        'FacingMode': 'FaceCameraPosition' if cloud else 'FaceCamera',
        'SortMode': 'ViewDepth', 'bCastShadows': False, 'MotionVectorSetting': 'Disable',
        'CutoutTexture': None, 'bUseMaterialCutoutTexture': False})
    for key, value in cloud_lifecycle().items():
        put(system, name, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    expression(system, name, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', 'max(.6,User.StormDuration+.6)')
    module = 'SpawnBurst_Instantaneous' if cloud else 'SpawnRate'
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/' + module)))
    if cloud:
        expression(system, name, 'EmitterUpdateScript', module, 'Spawn Count', '50')
        put(system, name, 'EmitterUpdateScript', module, 'Spawn Time', '(Value=0)')
    else:
        rate = {'snow': 95, 'rain': 100, 'mist': 24}[kind]
        expression(system, name, 'EmitterUpdateScript', module, 'SpawnRate',
                   f'{rate}*saturate(User.Strength)*(1-.75*saturate(User.DetailReduction))')
    a, b = 'frac(float(Particles.UniqueID)*.618033989)', 'frac(float(Particles.UniqueID)*.754877666)'
    index = 'fmod(float(Particles.UniqueID),25.0)'
    cell = 'Particles.RoomCell'
    # Analytic bounded motion prevents a snow sprite drifting through a wall or
    # surviving above a newly lowered ceiling. No scene collision controls damage.
    sway = '.022' if cloud else ('.10' if mist else '.15')
    x = f'((fmod({index},5.0)-2)*.4+{sway}*{cell}.z*((2*{a}-1)*.65+sin(Particles.Age*2+{b}*6.28)*.35))'
    y = f'((floor({index}/5.0)-2)*.4+{sway}*{cell}.z*((2*{b}-1)*.65+cos(Particles.Age*2+{a}*6.28)*.35))'
    valid = f'saturate({cell}.z*12)*saturate((1-({x})*({x})-({y})*({y}))*16)'
    height = f'max(2,{cell}.y-10)'
    width = f'min(User.RadiusX,User.RadiusY)*.32*{cell}.z'
    life = 'max(.6,User.StormDuration+.6)' if cloud else (f'1.2+{b}*.7' if mist else ('.35' if kind == 'rain' else f'1.4+{b}*.7'))
    if cloud:
        thickness = f'max(4,min(min({width}*.62,{cell}.y*.2),240))'
        z = f'{cell}.x+max(4+({thickness})*.5,{cell}.y-8-({thickness})*(.55+floor(float(Particles.UniqueID)/25.0)*.5))'
        size = f'float2({width},{thickness})'
        rgb, alpha = '.20,.24,.27', f'.70*User.Strength*{smooth(cell+".y",90,180)}'
        fade = 'saturate(Particles.Age*5)'
    elif mist:
        size = f'float2(1,.48)*min(80,min(min(User.RadiusX,User.RadiusY)*.12*{cell}.z,{cell}.y*.45))'
        z = f'{cell}.x+min(30,{cell}.y*.3)*(1+.12*sin(Particles.Age*2+{a}*6.28))'
        rgb, alpha = '.62,.76,.83', '.38*User.Strength'
        fade = 'saturate(Particles.NormalizedAge*6)*saturate((1-Particles.NormalizedAge)*4)'
    else:
        z = f'{cell}.x+5+({height})*lerp(.25+.14*sin(Particles.Age*4+{a}*6.28),1-Particles.NormalizedAge,{smooth(cell+".y",70,160)})'
        if kind == 'snow':
            size, rgb, alpha = f'float2(1.6,2.6)*(1+{b}*1.5)', '.86,.94,.98', '.85*User.Strength'
        else:
            size, rgb, alpha = 'float2(.6,8)', '.49,.65,.73', f'.38*User.Strength*{smooth(cell+".y",100,200)}'
        fade = 'saturate(Particles.NormalizedAge*8)*saturate((1-Particles.NormalizedAge)*8)'
    position = f'User.CurrentPosition+User.Side*User.RadiusX*({x})+User.Up*User.RadiusY*({y})+User.SurfaceNormal*({z})'
    fields = {'Particles.Position': (POSITION, position), 'Particles.SpriteSize': (VEC2, size),
              'Particles.Color': (COLOR, f'float4({rgb},({alpha})*({valid})*({fade}))'),
              'Particles.SpriteRotation': (FLOAT, '0' if cloud or kind == 'rain' else f'{a}*360'),
              'Particles.SpriteAlignment': (VEC3, 'User.SurfaceNormal'),
              'Particles.SubImageIndex': (FLOAT, 'clamp(Particles.NormalizedAge*56,0,63)' if mist else '0')}
    for stage in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        room_fields(system, name, stage)
        values = dict(fields)
        if stage == 'ParticleSpawnScript':
            values['Particles.Lifetime'] = (FLOAT, life)
        assignments(system, name, stage, values)


def system(name, layers):
    result = own(V3 + name, name)
    for en in emitters(result):
        API.call_method('RemoveEmitter', (ref(result, en),))
    for key, typ in [('CurrentPosition', POSITION), ('Side', VEC3), ('Up', VEC3), ('SurfaceNormal', VEC3),
                     ('Wind', VEC3), ('RadiusX', FLOAT), ('RadiusY', FLOAT), ('CloudHeight', FLOAT),
                     ('CloudThickness', FLOAT), ('StormDuration', FLOAT), ('CloudEmission', FLOAT),
                     ('Strength', FLOAT), ('DetailReduction', FLOAT)] + [(f'RoomCell{i}', VEC3) for i in range(25)]:
        user_parameter(result, key, typ)
    expression(result, '', 'SystemUpdateScript', 'SystemState', 'Loop Duration', 'max(.6,User.StormDuration+.6)')
    for kind, material in layers:
        mat = u.load_asset(material)
        if not mat:
            raise RuntimeError('Missing VFX material ' + material)
        layer(result, 'Indoor' + kind.title(), kind, mat)
    result.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-1600, -1600, -900), max=u.Vector(1600, 1600, 2200)))
    save(result)


def build_assets():
    if any(str(p.get_path_name()).startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved Blizzard IndoorV5 assets')
    EAL.make_directory(DEST)
    resumed = '-BlizzardResumeSystems' in u.SystemLibrary.get_command_line()
    if not resumed:
        footprint_material('M_BlizzardGroundFrost')
        footprint_material('M_BlizzardAimPreview')
    system('NS_BlizzardStormCloud', [('cloud', V3 + 'MI_BlizzardStormCloud')])
    system('NS_BlizzardPrecipitation', [('snow', '/Game/Skills/IceSpike/FrostV2/M_FrostCrystalSoft'), ('rain', V3 + 'M_BlizzardRain')])
    system('NS_BlizzardBoundaryMist', [('mist', '/Game/Skills/IceSpike/FrostV2/MI_ColdMist')])
    saved = [x for x in CREATED if x.startswith(DEST)]
    if resumed:
        saved += [DEST+'/'+x+'.'+x for x in ['M_BlizzardGroundFrost', 'M_BlizzardAimPreview']]
    receipt = {'saved_assets': saved, 'resumed_after_materials': resumed, 'room_cells': 25,
               'cloud_particles': 50, 'niagara_per_zone': 3, 'decorative_ice_slots': 48,
               'gameplay_tested': False, 'rendered': False}
    folder = ROOT / 'Saved/BlizzardIndoor20261012'
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'asset-authoring.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('BLIZZARD_INDOOR_V5_SAVED ' + json.dumps(receipt))


if __name__ == '__main__':
    build_assets()
