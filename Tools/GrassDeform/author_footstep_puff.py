"""Repair the runtime footstep puff in place; no map, PIE or preview operations.

The old heat-distortion template kept its renderer after losing its driving modules.
Author an explicit, bounded dust burst and a texture-independent soft coverage mask.
"""
import datetime
import json
import shutil
import sys
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir())
DEST = '/Game/WorldGeneration/GrassDeform'
OUT = ROOT / 'SourceAssets/GrassFootstepRepair20260926'
SYSTEM = DEST + '/NS_GrassFootstepPuff'
MATERIAL = DEST + '/M_GrassFootstepDust'
VERSION = 'puff-v2-soft-dust-20260926'
COUNT = 8
MAX_LIFETIME = .75
EMITTER = 'GrassPuff'
sys.path[:0] = [str(ROOT / 'Tools/Skills'), str(ROOT / 'Tools/Fluids')]
from build_fireball_assets import API, ref, setdata, put, assignments, emitters
from build_fireball_flames import trim, FLOAT, VEC2, VEC3, POSITION, COLOR
from author_river_pilot import node, wire, prop, custom

E, L = u.EditorAssetLibrary, u.MaterialEditingLibrary
SAVED = []


def save(asset):
    if isinstance(asset, u.Material):
        L.recompile_material(asset)
    if isinstance(asset, u.NiagaraSystem) and not u.RainAssetEditor.compile_rain(asset):
        raise RuntimeError('Footstep Niagara compilation failed')
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    SAVED.append(asset.get_path_name())
    print('FOOTSTEP_PUFF_SAVED', asset.get_path_name(), flush=True)


def own(path, cls, factory):
    asset = u.load_asset(path) if E.does_asset_exist(path) else (
        u.AssetToolsHelpers.get_asset_tools().create_asset(
            path.rsplit('/', 1)[1], DEST, cls, factory))
    if not asset:
        raise RuntimeError('Cannot load/create ' + path)
    return asset


def dust_material():
    m = own(MATERIAL, u.Material, u.MaterialFactoryNew())
    if E.get_metadata_tag(m, 'GrassDeformVersion') == VERSION:
        return m
    m.set_editor_property('blend_mode', u.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property('shading_model', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    m.set_editor_property('two_sided', True)
    m.set_editor_property('used_with_niagara_sprites', True)
    m.set_editor_property('disable_depth_test', False)
    m.set_editor_property('allow_front_layer_translucency', False)
    m.set_editor_property('translucency_lighting_mode',
                          u.TranslucencyLightingMode.TLM_VOLUMETRIC_NON_DIRECTIONAL)
    uv = node(m, u.MaterialExpressionTextureCoordinate)
    color = node(m, u.MaterialExpressionParticleColor)
    alpha = custom(m, '''
float2 q=(UV-.5)*2;
float edge=saturate(1-dot(q,q));
float detail=.72+.28*sin(UV.x*19+sin(UV.y*13))*sin(UV.y*17);
return pow(edge,1.8)*detail*Alpha;
''', {'UV': uv, 'Alpha': (color, 'A')}, description='Footstep dust soft coverage')
    fade = node(m, u.MaterialExpressionDepthFade)
    fade.set_editor_property('fade_distance_default', 2.)
    wire(alpha, fade, 'Opacity')
    tint = custom(m, 'return Tint;', {'Tint': (color, 'RGB')}, 3)
    roughness = node(m, u.MaterialExpressionConstant)
    roughness.set_editor_property('r', 1.)
    zero = node(m, u.MaterialExpressionConstant)
    zero.set_editor_property('r', 0.)
    slab = node(m, u.MaterialExpressionSubstrateShadingModels)
    slab.set_editor_property('shading_model_override', u.MaterialShadingModel.MSM_DEFAULT_LIT)
    for output, pin, value in [('BASE_COLOR', 'BaseColor', tint),
                               ('ROUGHNESS', 'Roughness', roughness),
                               ('SPECULAR', 'Specular', zero),
                               ('METALLIC', 'Metallic', zero),
                               ('OPACITY', 'Opacity', fade)]:
        prop(m, value, output)
        wire(value, slab, pin)
    prop(m, slab, 'FRONT_MATERIAL')
    E.set_metadata_tag(m, 'GrassDeformVersion', VERSION)
    save(m)
    return m


def build():
    # Preserve live editor changes instead of overwriting dirty target packages.
    dirty = {str(p.get_path_name()) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection({SYSTEM, MATERIAL}):
        raise RuntimeError('Unsaved footstep target packages: ' + str(dirty.intersection({SYSTEM, MATERIAL})))
    OUT.mkdir(parents=True, exist_ok=True)
    source_file = ROOT / 'Content/WorldGeneration/GrassDeform/NS_GrassFootstepPuff.uasset'
    backup = OUT / 'BeforeRepair/NS_GrassFootstepPuff.uasset'
    if source_file.exists() and not backup.exists():
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, backup)
    E.make_directory(DEST)
    m = dust_material()
    s = own(SYSTEM, u.NiagaraSystem, u.NiagaraSystemFactoryNew())
    if E.get_metadata_tag(s, 'GrassDeformVersion') == VERSION:
        return s
    if EMITTER not in emitters(s):
        template = u.load_asset('/Game/NiagaraExamples/FX_Explosions/Emitters/NE_Core')
        if not template:
            raise RuntimeError('Missing footstep emitter authoring template')
        API.call_method('AddEmitter', (s, template, EMITTER))
    for name in emitters(s):
        if name != EMITTER:
            API.call_method('RemoveEmitter', (ref(s, name),))
    trim(s, EMITTER, {'EmitterUpdateScript': ['EmitterState'],
                     'ParticleSpawnScript': ['InitializeParticle'],
                     'ParticleUpdateScript': ['ParticleState']})
    for script in ['ParticleSpawnScript', 'ParticleUpdateScript']:
        E.remove_metadata_tag(s, 'Fireball.Assignments.' + EMITTER + '.' + script)
    setdata('SetEmitterData', u.NiagaraExt_EmitterData, ref(s, EMITTER), {
        'bLocalSpace': False, 'SimTarget': 'CPUSim', 'bInterpolatedSpawning': False})
    source = u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
    lifecycle = {}
    for key, old, new in [('Life Cycle Mode', 'System', 'Self'), ('Loop Behavior', 'Infinite', 'Once')]:
        value = u.RainAssetEditor.read_input(source, 'Explosion', 'EmitterUpdateScript', 'EmitterState', key)
        value = value.replace('NewEnumerator0', 'NewEnumerator1').replace('"' + old + '"', '"' + new + '"')
        put(s, EMITTER, 'EmitterUpdateScript', 'EmitterState', key, value,
            '/Script/NiagaraEditor.NiagaraExt_StackInputData_Enum')
        lifecycle[key] = value
    put(s, EMITTER, 'EmitterUpdateScript', 'EmitterState', 'Loop Duration', '(Value=0.1)')
    API.call_method('AddModule', (ref(s, EMITTER, 'EmitterUpdateScript'),
                                  u.load_asset('/Niagara/Modules/Emitter/SpawnBurst_Instantaneous')))
    put(s, EMITTER, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Count',
        '(Value=' + str(COUNT) + ')', '/Script/Niagara.NiagaraInt32')
    put(s, EMITTER, 'EmitterUpdateScript', 'SpawnBurst_Instantaneous', 'Spawn Time', '(Value=0)')
    setdata('SetRendererData', u.NiagaraExt_RendererData, ref(s, EMITTER, renderer=0), {
        'Material': m.get_path_name(), 'MaterialUserParamBinding': {'Parameter': {'Name': 'None'}},
        'SubImageSize': {'X': 1, 'Y': 1}, 'bSubImageBlend': False, 'Alignment': 'Unaligned',
        'FacingMode': 'FaceCamera', 'CutoutTexture': None, 'bUseMaterialCutoutTexture': False,
        'bCastShadows': False, 'bEnableCameraDistanceCulling': True,
        'MinCameraDistance': 0, 'MaxCameraDistance': 2500})
    seed = 'frac(float(Particles.UniqueID)*.61803399)'
    theta = '(' + seed + '*6.2831853)'
    radial = 'float3(cos(' + theta + '),sin(' + theta + '),0)'
    assignments(s, EMITTER, 'ParticleSpawnScript', {
        'Particles.PuffOrigin': (POSITION, 'Engine.Owner.Position+' + radial + '*(2+7*' + seed + ')'),
        'Particles.PuffDrift': (VEC3, radial + '*(12+10*' + seed + ')+float3(0,0,9)'),
        'Particles.Lifetime': (FLOAT, '.55+.20*' + seed),
        'Particles.Position': (POSITION, 'Engine.Owner.Position'),
        'Particles.SpriteSize': (VEC2, 'float2(4,4)'),
        'Particles.SpriteRotation': (FLOAT, seed + '*360'),
        'Particles.SpriteUVScale': (VEC2, 'float2(1,1)'),
        'Particles.SubImageIndex': (FLOAT, '0'),
        'Particles.Velocity': (VEC3, 'float3(0,0,0)'),
        'Particles.Color': (COLOR, 'float4(.30,.25,.17,0)')})
    assignments(s, EMITTER, 'ParticleUpdateScript', {
        'Particles.Position': (POSITION, 'Particles.PuffOrigin+Particles.PuffDrift*Particles.Age'),
        'Particles.Velocity': (VEC3, 'Particles.PuffDrift'),
        'Particles.SpriteSize': (VEC2, 'float2(4,4)*(1+Particles.NormalizedAge*1.5)'),
        'Particles.Color': (COLOR, 'float4(.30,.25,.17,.30*saturate(Particles.Age*30)*(1-Particles.NormalizedAge)*(1-Particles.NormalizedAge))')})
    s.set_editor_property('fixed_bounds', u.Box(min=u.Vector(-45, -45, -12), max=u.Vector(45, 45, 35)))
    E.set_metadata_tag(s, 'GrassDeformVersion', VERSION)
    save(s)
    renderer = json.loads(API.call_method('GetRendererData', (ref(s, EMITTER, renderer=0),))
                          .get_editor_property('property_values'))
    receipt = {'saved': SAVED, 'system': s.get_path_name(), 'material': m.get_path_name(),
               'burst_particles': COUNT, 'max_lifetime_seconds': MAX_LIFETIME,
               'sprite_diameter_cm': [4, 10], 'lifecycle': lifecycle,
               'saved_renderer_material': renderer.get('Material'),
               'saved_lifecycle': {key: u.RainAssetEditor.read_input(
                   s, EMITTER, 'EmitterUpdateScript', 'EmitterState', key) for key in lifecycle},
               'status': 'authored_compiled_saved', 'runtime_tested': False, 'visually_tested': False}
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    (OUT / ('receipt-' + stamp + '.json')).write_text(json.dumps(receipt, indent=2), encoding='utf8')
    print('FOOTSTEP_PUFF_COMPLETE', json.dumps(receipt), flush=True)
    return s


if __name__ == '__main__':
    build()
