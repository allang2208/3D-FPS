"""Current V5 fire-ring author; installed asset names remain stable for runtime."""
import hashlib
import json
import math
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = ROOT / 'SourceAssets/FlameArmor20261016/FireRingV5'
DEST = '/Game/Skills/FlameArmor20261016/TorchV2/FireRingV4'
BODY = '/Game/Skills/FlameArmor20261016/TorchV2/NS_FlameArmorBodyV2'
sys.path.insert(0, str(ROOT / 'Tools/Fluids'))
import author_flame_armor_fireball_v3 as v3
from author_flame_armor_v2 import API, LIB, TOOLS, ref, setdata, put, assignments, setup_emitter, FLOAT, VEC3, COLOR
from author_flame_armor_v2 import POSITION, V, S, ANGLE


def clean_target(path):
    if path in {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:
        raise RuntimeError('Preserve unsaved target: ' + path)


def save(asset):
    v3.base.save(asset)


def material():
    path = DEST + '/M_FA_FireRingV4'
    clean_target(path)
    mat = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else TOOLS.create_asset(
        'M_FA_FireRingV4', DEST, u.Material, u.MaterialFactoryNew())
    LIB.delete_all_material_expressions(mat)
    for key, value in {'blend_mode': u.BlendMode.BLEND_ALPHA_COMPOSITE,
                       'shading_model': u.MaterialShadingModel.MSM_UNLIT,
                       'translucency_pass': u.MaterialTranslucencyPass.MTP_AFTER_DOF,
                       'two_sided': True, 'disable_depth_test': False,
                       'enable_responsive_aa': True, 'output_translucent_velocity': False}.items():
        mat.set_editor_property(key, value)
    LIB.set_base_material_usage(mat, u.MaterialUsage.MATUSAGE_NIAGARA_MESH_PARTICLES, True)

    def node(cls, **values):
        result = LIB.create_material_expression(mat, cls)
        for key, value in values.items():
            result.set_editor_property(key, value)
        return result

    def wire(source, target, pin, output=''):
        if not LIB.connect_material_expressions(source, output, target, pin):
            raise RuntimeError('Ring material connection: ' + pin)

    uv = node(u.MaterialExpressionTextureCoordinate)
    clock = node(u.MaterialExpressionTime)
    noise = node(u.MaterialExpressionTextureObject,
                 texture=u.load_asset('/Game/Vefects/Free_Fire/Shared/Textures/T_VFX_Noise_01'),
                 sampler_type=u.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE)
    atlas = node(u.MaterialExpressionTextureObject,
                 texture=u.load_asset('/Game/Skills/Fireball/FluidCore20260923/T_FireballCombustionFields'),
                 sampler_type=u.MaterialSamplerType.SAMPLERTYPE_MASKS)
    inputs = []
    for key in ('UV', 'Clock', 'Noise', 'Atlas'):
        pin = u.CustomInput(); pin.set_editor_property('input_name', key); inputs.append(pin)
    fields = node(u.MaterialExpressionCustom, description='FlameArmor closed fire ring',
                  code=(OUT / 'FireRing.hlsl').read_text(encoding='utf-8'), inputs=inputs,
                  output_type=u.CustomMaterialOutputType.CMOT_FLOAT4)
    for key, source in (('UV', uv), ('Clock', clock), ('Noise', noise), ('Atlas', atlas)):
        wire(source, fields, key)
    rgb = node(u.MaterialExpressionComponentMask, r=True, g=True, b=True, a=False)
    alpha = node(u.MaterialExpressionComponentMask, r=False, g=False, b=False, a=True)
    wire(fields, rgb, str(LIB.get_material_expression_input_names(rgb)[0]))
    wire(fields, alpha, str(LIB.get_material_expression_input_names(alpha)[0]))
    color = node(u.MaterialExpressionParticleColor)
    coverage = node(u.MaterialExpressionMultiply); wire(alpha, coverage, 'A'); wire(color, coverage, 'B', 'A')
    contact = node(u.MaterialExpressionDepthFade, fade_distance_default=.6)
    wire(coverage, contact, str(LIB.get_material_expression_input_names(contact)[0]))
    gain = node(u.MaterialExpressionScalarParameter, parameter_name='EmissionGain', default_value=6.2)
    energy = node(u.MaterialExpressionMultiply); wire(rgb, energy, 'A'); wire(gain, energy, 'B')
    exposure = node(u.MaterialExpressionEyeAdaptationInverse)
    wire(energy, exposure, str(LIB.get_material_expression_input_names(exposure)[0]))
    premult = node(u.MaterialExpressionMultiply); wire(exposure, premult, 'A'); wire(contact, premult, 'B')
    LIB.connect_material_property(premult, '', u.MaterialProperty.MP_EMISSIVE_COLOR)
    LIB.connect_material_property(contact, '', u.MaterialProperty.MP_OPACITY)
    errors = LIB.recompile_material(mat)
    if errors:
        raise RuntimeError(str(errors))
    save(mat)
    return mat


def mesh(mat):
    path = DEST + '/SM_FA_FireRingV4'
    clean_target(path)
    positions, normals, uv, triangles = [], [], [], []
    segments = 96

    def strip(rings, floor=False, inward=False):
        start = len(positions)
        for radius, height, height_uv in rings:
            for i in range(segments + 1):
                angle = 2 * math.pi * i / segments
                c, s = math.cos(angle), math.sin(angle)
                positions.append((radius*c, radius*s, height))
                sign = -1 if inward else 1
                normals.append((0, 0, 1) if floor else (sign*c, sign*s, 0))
                uv.append((i/segments, height_uv))
        for j in range(len(rings)-1):
            for i in range(segments):
                a = start+j*(segments+1)+i; b = a+1; c = a+segments+1; d = c+1
                faces = [(a, b, d), (a, d, c)]
                if floor or inward:
                    faces = [(x, z, y) for x, y, z in faces]
                triangles.extend(faces)

    # Two flared walls plus an actual annular floor; the center stays empty.
    strip([(38, 1.8, -1), (58, 1.8, -2)], floor=True)
    heights = (0, 6, 16, 31, 52)
    strip([(56+4*(h/52), 1.8+h, h/52) for h in heights])
    strip([(41+8*(h/52), 1.8+h, h/52) for h in heights], inward=True)
    buffers = u.GeometryScriptSimpleMeshBuffers()
    buffers.vertices = [u.Vector(*p) for p in positions]
    buffers.normals = [u.Vector(*n) for n in normals]
    buffers.uv0 = [u.Vector2D(*t) for t in uv]
    buffers.triangles = [u.IntVector(*t) for t in triangles]
    dynamic = u.DynamicMesh()
    u.GeometryScript_MeshEdits.append_buffers_to_mesh(dynamic, buffers)
    asset = u.load_asset(path) if u.EditorAssetLibrary.does_asset_exist(path) else None
    if asset:
        _, result = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dynamic, asset,
            u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False, enable_recompute_tangents=True),
            u.GeometryScriptMeshWriteLOD())
    else:
        asset, result = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dynamic, path,
            u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=False,
                enable_recompute_tangents=True, enable_collision=False))
    if not asset or result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Could not create the ring mesh: ' + str(result))
    asset.set_material(0, mat)
    save(asset)
    (OUT / 'ring-mesh-source.json').write_text(json.dumps({
        'vertices': positions, 'uv0': uv, 'normals': normals, 'triangles': triangles,
        'authored_radius_cm': 50, 'runtime_radius': 'max(62, User.Radius + 18) / 50', 'height_cm': 53.8}), encoding='utf-8')
    return asset


def assets():
    OUT.mkdir(parents=True, exist_ok=True)
    u.EditorAssetLibrary.make_directory(DEST)
    return mesh(material())


def add_ring_layers(system):
    v3.remove_body_layers(system)
    ring = u.load_asset(DEST + '/SM_FA_FireRingV4') if u.EditorAssetLibrary.does_asset_exist(DEST + '/SM_FA_FireRingV4') else assets()
    for name in ('FootTongues', 'FootFireballCores', 'FootFireballTongues', 'FootRingV4', 'FootRingEmbersV4'):
        if name in v3.base.emitters(system):
            API.call_method('RemoveEmitter', (ref(system, name),))
    name = 'FootRingV4'
    setup_emitter(system, name, u.load_asset(v3.MATERIALS['flame']), 0, True)
    API.call_method('RemoveRenderer', (ref(system, name, renderer=0),))
    renderer_class = u.load_class(None, '/Script/Niagara.NiagaraMeshRendererProperties')
    API.call_method('AddRenderer', (ref(system, name), renderer_class))
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(system, name, renderer=0), {
        'Meshes': [{'Mesh': ring.get_path_name(), 'Scale': {'X': 1, 'Y': 1, 'Z': 1}}],
        'bOverrideMaterials': False, 'FacingMode': 'Default', 'bCastShadows': False,
        'bEnableCameraDistanceCulling': False, 'SortOrderHint': 0})
    API.call_method('RemoveModule', (ref(system, name, 'EmitterUpdateScript', 'SpawnRate'),))
    API.call_method('RemoveModule', (ref(system, name, 'ParticleUpdateScript', 'ParticleState'),))
    API.call_method('AddModule', (ref(system, name, 'EmitterUpdateScript'),
                                 u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        '(HlslExpression="Engine.Emitter.TotalSpawnedParticles < 1 ? 1 : 0")',
        '/Script/NiagaraEditor.NiagaraExt_StackInputData_HlslExpression')
    put(system, name, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
    common = {'Particles.Position': (POSITION, 'float3(0,0,0)'),
              'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
              'Particles.Scale': (VEC3, 'float3(max(62,User.Radius+18)/50,max(62,User.Radius+18)/50,1)'),
              'Particles.MeshOrientation': ('/Script/CoreUObject.Quat4f', 'float4(0,0,0,1)'),
              'Particles.Color': (COLOR, 'float4(1,1,1,saturate(User.Fade))')}
    assignments(system, name, 'ParticleSpawnScript', {'Particles.Lifetime': (FLOAT, '1'), **common})
    assignments(system, name, 'ParticleUpdateScript', common)
    # Keep a few embers as accents; the ring silhouette never depends on them.
    origin = f'User.BodyOrigin+float3(cos({ANGLE}),sin({ANGLE}),0)*max(62,User.Radius+18)*.99+float3(0,0,12)'
    v3.layer(system, 'FootRingEmbersV4', 'ember', 3, False, f'.35+.25*{V}', origin,
             'Particles.Position+Particles.Velocity*Engine.DeltaTime', 'float2(.6,1.6)', 'User.Fade*.65',
             velocity=f'float3(cos({ANGLE})*3,sin({ANGLE})*3,24)+User.BodyVelocity*.10',
             axis='normalize(Particles.Velocity+float3(0,0,.1))')
    u.EditorAssetLibrary.set_metadata_tag(system, 'FlameArmor.FootRevision', 'FireRingV5')


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    clean_target(BODY)
    source = ROOT / 'Content/Skills/FlameArmor20261016/TorchV2/NS_FlameArmorBodyV2.uasset'
    previous = OUT / 'Before' / source.name
    previous.parent.mkdir(parents=True, exist_ok=True)
    if not previous.exists():
        shutil.copy2(source, previous)
    for leaf in ('M_FA_FireRingV4', 'SM_FA_FireRingV4'):
        old_asset = ROOT / 'Content/Skills/FlameArmor20261016/TorchV2/FireRingV4' / (leaf+'.uasset')
        old_copy = OUT / 'Before' / old_asset.name
        if old_asset.exists() and not old_copy.exists():
            shutil.copy2(old_asset, old_copy)
    v3.base.RECORDS.clear()
    assets()
    system = u.load_asset(BODY)
    add_ring_layers(system)
    save(system)
    receipt = {'revision': 'FireRingV5', 'saved_assets': list(v3.base.RECORDS),
               'before': str(previous), 'before_sha256': hashlib.sha256(previous.read_bytes()).hexdigest(),
               'ring_triangles': 1728, 'persistent_ring_particles': 1, 'ring_embers_per_second': 3,
               'native_cpp_changed': False, 'weapon_or_arrow_changed': False,
               'runtime_test_or_render': False}
    (OUT / 'delivery.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    print('FLAME_ARMOR_RING_V5_SAVED', receipt['saved_assets'])


if __name__ == '__main__':
    run()
