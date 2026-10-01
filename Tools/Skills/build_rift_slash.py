"""Author/save FPSGAME's tapered sword-energy wave and blade distortion.

Background Python commandlet, or existing editor via the asset mutex bridge.
No previews, gameplay runs or acceptance tests. No Fab assets are used.
"""
import json
import math
import sys
from pathlib import Path
import unreal as u

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_fireball_assets import API, ref, setdata, put

ROOT = Path(u.Paths.project_dir())
SRC = ROOT / 'SourceAssets/RiftSlash20260930'
DEST = '/Game/Weapons/RiftSlash20260930'
TAG = 'FPSGAME.RiftSlash'
VERSION = 'V4'
L = u.MaterialEditingLibrary
A = u.EditorAssetLibrary
T = u.AssetToolsHelpers.get_asset_tools()
SAVED = []
FLOAT = '/Script/Niagara.NiagaraFloat'
VEC2 = '/Script/CoreUObject.Vector2f'
VEC3 = '/Script/CoreUObject.Vector3f'
POSITION = '/Script/Niagara.NiagaraPosition'
COLOR = '/Script/CoreUObject.LinearColor'


def owned(name):
    path = DEST + '/' + name
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved asset: ' + path)
    if not A.does_asset_exist(path):
        return None
    asset = u.load_asset(path)
    if A.get_metadata_tag(asset, TAG) not in ('V1', 'V2', 'V3', VERSION):
        raise RuntimeError('Preserve unowned asset: ' + path)
    return asset


def save(asset):
    A.set_metadata_tag(asset, TAG, VERSION)
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Niagara compile failed: ' + asset.get_path_name())
    if not A.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed: ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    u.log('RIFT_SLASH_SAVED ' + asset.get_path_name())


def node(mat, cls, **props):
    result = L.create_material_expression(mat, cls)
    for key, value in props.items():
        result.set_editor_property(key, value)
    return result


def wire(source, target, pin=''):
    if isinstance(pin, int):
        pin = str(L.get_material_expression_input_names(target)[pin])
    if not L.connect_material_expressions(source, '', target, pin):
        raise RuntimeError('Material connection failed: ' + str(pin))


def material(name, code, scalars, particle=False):
    mat = owned(name) or T.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    # UE 5.8's bulk deletion mutates its iteration array and can leave outputs.
    for expression in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat, expression)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_ADDITIVE if particle else u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    inputs = {'UV': node(mat, u.MaterialExpressionTextureCoordinate),
              'Exposure': node(mat, u.MaterialExpressionEyeAdaptation)}
    if particle:
        inputs['Tint'] = node(mat, u.MaterialExpressionParticleColor)
    for key, value in scalars.items():
        inputs[key] = node(mat, u.MaterialExpressionScalarParameter, parameter_name=key, default_value=value)
    custom = node(mat, u.MaterialExpressionCustom, code=code, output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    custom.set_editor_property('inputs', pins)
    for key, value in inputs.items():
        if key == 'Tint':
            if not L.connect_material_expressions(value, 'RGBA', custom, key):
                raise RuntimeError('Particle RGBA connection failed')
        else:
            wire(value, custom, key)
    rgb = node(mat, u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(mat, u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    wire(custom, rgb)
    wire(custom, alpha)
    depth = node(mat, u.MaterialExpressionDepthFade, fade_distance_default=4.0)
    wire(alpha, depth, 0)
    L.connect_material_property(rgb, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    L.connect_material_property(depth, '', u.MaterialProperty.MP_OPACITY)
    temporal = node(mat, u.MaterialExpressionTemporalResponsivenessOutput)
    wire(node(mat, u.MaterialExpressionConstant, r=1.0), temporal, 0)
    if particle:
        L.set_material_usage(mat, u.MaterialUsage.MATUSAGE_NIAGARA_SPRITES)
    L.recompile_material(mat)
    save(mat)
    return mat


def spatial_slit(mat):
    # Slit-like silhouette only: the surface is luminous sword energy, not a
    # torn opening. Keep the thick center and tips with smooth contours in YZ.
    segments, across = 128, 8
    pos, uv, normals, faces = [], [], [], []
    for i in range(segments + 1):
        t = i / segments
        taper = max(.001, math.sin(math.pi * t)) ** .9
        center = .2 * taper * math.sin(t * math.pi * 2)
        for j in range(across + 1):
            v = j / across
            side = v * 2 - 1
            thickness = 19 * taper
            pos.append((-6 * (1 - side * side) * taper, (t - .5) * 176, center + side * thickness))
            uv.append((t, 1 - v))  # FBX/OBJ import converts V to UE's top-left convention.
            normals.append((-1, 0, 0))
    for i in range(segments):
        for j in range(across):
            a = i * (across + 1) + j + 1
            b = a + across + 1
            faces.extend(((a, b, b + 1), (a, b + 1, a + 1)))
    lines = ['# Original FPSGAME sword energy: broad middle, two pointed tips. +X flight.', 'o SM_RiftSlash']
    lines += ['v %.8f %.8f %.8f' % p for p in pos]
    lines += ['vt %.8f %.8f' % p for p in uv]
    lines += ['vn %.8f %.8f %.8f' % p for p in normals]
    lines += ['f ' + ' '.join('%d/%d/%d' % (p, p, p) for p in f) for f in faces]
    SRC.mkdir(parents=True, exist_ok=True)
    source = SRC / 'SM_RiftSlash.obj'
    source.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    import_mesh(source, 'SM_RiftSlash', mat)


def import_mesh(source, name, mat):
    owned(name)  # Preserve unowned or unsaved packages before reimporting geometry.
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal = False
    options.import_materials = False
    options.import_textures = False
    options.static_mesh_import_data.combine_meshes = True
    options.static_mesh_import_data.auto_generate_collision = False
    options.static_mesh_import_data.generate_lightmap_u_vs = False
    options.static_mesh_import_data.convert_scene = False
    options.static_mesh_import_data.normal_import_method = u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task = u.AssetImportTask()
    task.filename = str(source)
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = True
    task.options = options
    task.save = False
    T.import_asset_tasks([task])
    mesh = u.load_asset(DEST + '/' + name)
    if not isinstance(mesh, u.StaticMesh):
        raise RuntimeError('Ribbon import failed: ' + str(task.imported_object_paths))
    mesh.set_material(0, mat)
    save(mesh)


def custom_expr(mat, code, inputs, output=u.CustomMaterialOutputType.CMOT_FLOAT1):
    expression = node(mat, u.MaterialExpressionCustom, code=code, output_type=output)
    pins = []
    for key in inputs:
        pin = u.CustomInput()
        pin.set_editor_property('input_name', key)
        pins.append(pin)
    expression.set_editor_property('inputs', pins)
    for key, value in inputs.items():
        wire(value, expression, key)
    return expression


def blade_distortion():
    name = 'M_RiftBladeDistortion'
    mat = owned(name) or T.create_asset(name, DEST, u.Material, u.MaterialFactoryNew())
    for expression in list(L.get_material_expressions(mat)):
        L.delete_material_expression(mat, expression)
    mat.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    mat.set_editor_property('shading_model', u.MaterialShadingModel.MSM_UNLIT)
    mat.set_editor_property('two_sided', True)
    mat.set_editor_property('disable_depth_test', False)
    mat.set_editor_property('translucency_pass', u.MaterialTranslucencyPass.MTP_BEFORE_DOF)
    mat.set_editor_property('refraction_method', u.RefractionMode.RM_INDEX_OF_REFRACTION)
    mat.set_editor_property('refraction_depth_bias', .2)
    uv = node(mat, u.MaterialExpressionTextureCoordinate)
    time = node(mat, u.MaterialExpressionTime)
    exposure = node(mat, u.MaterialExpressionEyeAdaptation)
    phase = node(mat, u.MaterialExpressionScalarParameter, parameter_name='Phase', default_value=0.)
    fade = node(mat, u.MaterialExpressionScalarParameter, parameter_name='Opacity', default_value=1.)
    strength = node(mat, u.MaterialExpressionScalarParameter, parameter_name='DistortionStrength', default_value=.075)
    signal = custom_expr(mat, (SRC / 'rift_blade.hlsl').read_text(encoding='utf-8'),
                         {'UV': uv, 'Time': time, 'Phase': phase}, u.CustomMaterialOutputType.CMOT_FLOAT4)
    mask = custom_expr(mat, 'return S.z*Fade;', {'S': signal, 'Fade': fade})
    depth = node(mat, u.MaterialExpressionDepthFade, fade_distance_default=.65)
    wire(mask, depth, 0)
    # Full normal movement in the visible body; feather only the boundary.
    normal = custom_expr(mat, 'return normalize(float3(S.xy*smoothstep(0,.22,Mask),1));',
                         {'S': signal, 'Mask': depth}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    ior = custom_expr(mat, 'return 1+Mask*Strength;', {'Mask': depth, 'Strength': strength})
    opacity = custom_expr(mat, 'return Mask*(.31+.38*S.w);', {'Mask': depth, 'S': signal})
    emission = custom_expr(mat,
        'float hue=.35+.25*sin(Time*1.7+Phase*6.2831853); '
        'float3 crest=lerp(float3(.10,.40,1),float3(.38,.16,1),hue); '
        'return (float3(.009,.018,.075)+crest*(.04+S.w*1.8))/max(Exposure,.035);',
        {'S': signal, 'Exposure': exposure, 'Time': time, 'Phase': phase}, u.CustomMaterialOutputType.CMOT_FLOAT3)
    for expression, prop in [(normal, u.MaterialProperty.MP_NORMAL), (ior, u.MaterialProperty.MP_REFRACTION),
                              (opacity, u.MaterialProperty.MP_OPACITY), (emission, u.MaterialProperty.MP_EMISSIVE_COLOR)]:
        L.connect_material_property(expression, '', prop)
    temporal = node(mat, u.MaterialExpressionTemporalResponsivenessOutput)
    wire(node(mat, u.MaterialExpressionConstant, r=1.), temporal, 0)
    L.recompile_material(mat)
    save(mat)

    # An open spiral ribbon, 0.62 turns along the blade, no closed ring or shell.
    # Two independently moving runtime copies leave large areas of clear blade.
    segments, across = 96, 6
    pos, uv, normals, faces = [], [], [], []
    for i in range(segments + 1):
        t = i / segments
        angle = t * math.tau * .62 + .19 * math.sin(t * math.pi * 3)
        derivative = math.tau * .62 + .57 * math.pi * math.cos(t * math.pi * 3)
        for j in range(across + 1):
            v = j / across
            width = 6.8 * (.35 + .65 * max(0, math.sin(t * math.pi)) ** .65)
            radius = 6.2 + .45 * math.sin(t * math.pi * 4) + (v - .5) * width
            pos.append((9 + t * 83, radius * math.cos(angle), radius * math.sin(angle)))
            uv.append((t, 1 - v))
            n = (-radius * derivative, -83 * math.sin(angle), 83 * math.cos(angle))
            length = math.sqrt(sum(c * c for c in n))
            normals.append(tuple(c / length for c in n))
    for i in range(segments):
        for j in range(across):
            a = i * (across + 1) + j + 1
            b = a + across + 1
            faces.extend(((a, b, b + 1), (a, b + 1, a + 1)))
    lines = ['# Original FPSGAME blade refraction ribbon. X = blade axis, centimetres.', 'o SM_RiftBladeRibbon']
    lines += ['v %.8f %.8f %.8f' % p for p in pos]
    lines += ['vt %.8f %.8f' % p for p in uv]
    lines += ['vn %.8f %.8f %.8f' % p for p in normals]
    lines += ['f ' + ' '.join('%d/%d/%d' % (p, p, p) for p in f) for f in faces]
    source = SRC / 'SM_RiftBladeRibbon.obj'
    source.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    import_mesh(source, 'SM_RiftBladeRibbon', mat)


def assignments(system, stage, values):
    entries = []
    for name, (typ, expr) in values.items():
        entry = u.NiagaraExt_SetParameterEntry()
        entry.import_text('(Variable=(Name="' + name + '",Type=(ClassStructOrEnum="' + typ + '",UnderlyingType=2)))')
        entries.append(entry)
    module = str(API.call_method('AddSetParametersModule', (ref(system, 'RiftMotes', stage), entries)).get_editor_property('module_name'))
    for name, (typ, expr) in values.items():
        put(system, 'RiftMotes', stage, module, name, '(HlslExpression="' + expr + '")', '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')


def motes(mat):
    system = owned('NS_RiftSlashMotes') or T.create_asset('NS_RiftSlashMotes', DEST, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    # Only the bundled engine emitter template supplies Niagara lifecycle plumbing;
    # every shape, colour, size, placement and motion below is authored here.
    for emitter in API.call_method('GetSystemSummary', (system,)).get_editor_property('emitters'):
        API.call_method('RemoveEmitter', (ref(system, str(emitter.get_editor_property('emitter_name'))),))
    template = u.load_asset('/Niagara/DefaultAssets/Templates/Emitters/SimpleSpriteBurst')
    if not template:
        raise RuntimeError('Missing engine SimpleSpriteBurst template')
    API.call_method('AddEmitter', (system, template, 'RiftMotes'))
    topology = API.call_method('GetEmitterTopology', (ref(system, 'RiftMotes'),))
    for field in ['emitter_spawn_script', 'emitter_update_script', 'particle_spawn_script', 'particle_update_script']:
        stack = topology.get_editor_property(field)
        stage = str(stack.get_editor_property('script_name'))
        for module in stack.get_editor_property('modules'):
            name = str(module.get_editor_property('module_name'))
            if name not in ['EmitterState', 'InitializeParticle', 'ParticleState']:
                API.call_method('RemoveModule', (ref(system, 'RiftMotes', stage, name),))
    API.call_method('AddModule', (ref(system, 'RiftMotes', 'EmitterUpdateScript'), u.load_asset('/Niagara/Modules/Emitter/SpawnRate')))
    put(system, 'RiftMotes', 'EmitterUpdateScript', 'SpawnRate', 'SpawnRate', '(Value=52)')
    # Self-driven once loop. Long enough to cover the 0.67 s flight; the component
    # deactivates on impact/range and the remaining short-lived motes then fade.
    mode = u.RainAssetEditor.read_input(system, 'RiftMotes', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode')
    put(system, 'RiftMotes', 'EmitterUpdateScript', 'EmitterState', 'Life Cycle Mode',
        mode.replace('NewEnumerator0', 'NewEnumerator1').replace('"System"', '"Self"'),
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
    put(system, 'RiftMotes', 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=1.0)')
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(system, 'RiftMotes'),
            {'bLocalSpace': True, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, 'RiftMotes', renderer=0),
            {'Material': mat.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
             'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False, 'Alignment': 'Unaligned',
             'FacingMode': 'FaceCamera', 'bCastShadows': False, 'MotionVectorSetting': 'Disable',
             'CutoutTexture': None, 'bUseMaterialCutoutTexture': False})
    seed = 'frac(float(Particles.UniqueID)*.61803398875)'
    taper = 'pow(saturate(sin(' + seed + '*3.14159265)),.9)'
    side = '(frac(float(Particles.UniqueID)*.5)<.25?-1.0:1.0)'
    assignments(system, 'ParticleSpawnScript', {
        'Particles.Lifetime': (FLOAT, '.10+.045*' + seed),
        'Particles.Position': (POSITION, 'float3(-7,176*(' + seed + '-.5),15.5*' + taper + '*' + side + ')'),
        'Particles.Velocity': (VEC3, 'float3(-300,28*(' + seed + '-.5),7*' + side + ')'),
        'Particles.SpriteSize': (VEC2, 'float2(1.3,7)*(1+.4*' + seed + ')'),
        'Particles.Color': (COLOR, 'float4(.10,.52,1,.8)'),
        'Particles.SpriteRotation': (FLOAT, 'float(Particles.UniqueID)*137.508'),
    })
    assignments(system, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, 'Particles.Position+Particles.Velocity*Engine.DeltaTime'),
        'Particles.Color': (COLOR, 'float4(.10,.52,1,.8*(1-Particles.NormalizedAge)*(1-Particles.NormalizedAge))'),
    })
    system.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-190,-120,-100), max=u.Vector(20,120,80)))
    save(system)


def build(projectile_only=False):
    A.make_directory(DEST)
    blade = material('M_RiftSlash', (SRC / 'rift_slash.hlsl').read_text(encoding='utf-8'),
                     {'Age': 0., 'Opacity': 1., 'Dissolve': 0., 'Layer': 0., 'HitGlow': 0.})
    spatial_slit(blade)
    if not projectile_only:
        spark = material('M_RiftSlashMote',
                         'float2 p=(UV-.5)*2; float a=pow(saturate(1-dot(p,p)),2); '
                         'return float4(Tint.rgb*4/max(Exposure,.035),a*Tint.a);', {}, particle=True)
        motes(spark)
        blade_distortion()
    out = ROOT / 'Saved/RiftSlash' / ('authored-projectile.json' if projectile_only else 'authored.json')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'version': VERSION, 'saved': SAVED, 'source': str(SRC), 'mesh_triangles': 2048,
                               'projectile_profile': 'luminous sword energy, slit-like silhouette, 176 cm wide, 38 cm central thickness',
                               'projectile_only': projectile_only,
                               'blade_ribbon_triangles': 1152, 'blade_runtime_instances': 2,
                               'runtime_tested': False, 'rendered': False}, indent=2), encoding='utf-8')
    u.log('RIFT_SLASH_AUTHORING_COMPLETE ' + str(out))


if __name__ == '__main__':
    build()
